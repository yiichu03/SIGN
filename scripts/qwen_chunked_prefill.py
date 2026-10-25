"""Memory-bounded Qwen3.5 prefill, keeping all eight contexts and their caches.

The installed Transformers generic chunked-prefill path slices 3D positions as
2D tensors and does not handle image tokens crossing chunks. Embed images once,
slice positions on their last axis, and use the model's existing hybrid cache.
Only token prefill is chunked; every forward still has the full batch dimension.
"""

from types import MethodType


def install_chunked_prefill(model, chunk_size=2048):
    import torch

    original = model._prefill

    def prefill(self, input_ids, generation_config, model_kwargs, is_first_iteration=True):
        if input_ids.shape[-1] <= chunk_size:
            return original(input_ids, generation_config, model_kwargs, is_first_iteration)
        assert is_first_iteration
        cache = model_kwargs['past_key_values']
        assert cache.get_seq_length() == 0
        assert model_kwargs.get('pixel_values_videos') is None
        positions = model_kwargs['position_ids']
        assert positions.shape[-1] == input_ids.shape[-1]
        mask = model_kwargs['attention_mask']
        embedding = self.get_input_embeddings()
        pixels = model_kwargs.get('pixel_values')
        image_mask = image_indices = image_embeds = None
        if pixels is not None:
            features = self.model.get_image_features(
                pixels, model_kwargs['image_grid_thw'], return_dict=True)
            image_embeds = torch.cat(features.pooler_output, dim=0).to(embedding.weight.device, embedding.weight.dtype)
            # A hidden-dimension-expanded masked_scatter creates a huge int64
            # prefix-sum temporary for long batches. Select token rows instead.
            image_mask = input_ids.eq(self.config.image_token_id)
            assert int(image_mask.sum()) == image_embeds.shape[0]
            image_indices = torch.zeros_like(input_ids)
            image_indices[image_mask] = torch.arange(image_embeds.shape[0], device=input_ids.device)
            del features
        for start in range(0, input_ids.shape[-1], chunk_size):
            end = min(input_ids.shape[-1], start + chunk_size)
            # Materialize only this token block's embeddings (not B x full L x D).
            embeds = embedding(input_ids[:, start:end])
            if image_mask is not None:
                local_mask = image_mask[:, start:end]
                embeds[local_mask] = image_embeds[image_indices[:, start:end][local_mask]]
            outputs = self(
                inputs_embeds=embeds,
                attention_mask=mask[:, :end], position_ids=positions[..., start:end],
                past_key_values=cache, use_cache=True, logits_to_keep=1, return_dict=True,
            )
            cache = outputs.past_key_values
        assert cache.get_seq_length() == input_ids.shape[-1]
        return outputs

    model._prefill = MethodType(prefill, model)
    return original


def validate_chunked_prefill(model, processor, image_path):
    """Check numerical agreement with stock prefill on shared token prefixes.

BF16 GEMM shapes can change near-tied greedy choices, so compare teacher-forced
logits, rather than requiring divergent autoregressive continuations to match.
"""
    import torch

    chats = [[{'role': 'user', 'content': [
        {'type': 'image', 'path': str(image_path)},
        {'type': 'text', 'text': f'请以 CASE_{i} 开头，用一句中文描述图片中彩色轨迹的形状。' + ' ' * i},
    ]}] for i in range(8)]
    inputs = processor.apply_chat_template(
        chats, add_generation_prompt=True, enable_thinking=False,
        tokenize=True, return_dict=True, return_tensors='pt', padding=True).to(model.device)
    # Separate cache/mask correctness from BF16 rounding using FP32 text layers.
    # Vision features remain in the original dtype and are identical in both paths.
    dtypes = {name: parameter.dtype for name, parameter in model.named_parameters()}
    torch.cuda.empty_cache()
    old_tf32 = torch.backends.cuda.matmul.allow_tf32
    torch.backends.cuda.matmul.allow_tf32 = False
    try:
        model.model.language_model.float()
        model.lm_head.float()
        with torch.inference_mode():
            reference = model.generate(**inputs, max_new_tokens=1, do_sample=False,
                                       output_logits=True, return_dict_in_generate=True)
            fp32_expected = reference.logits[0].float().cpu()
            del reference
            original = install_chunked_prefill(model, chunk_size=256)
            try:
                chunked = model.generate(**inputs, max_new_tokens=1, do_sample=False,
                                         output_logits=True, return_dict_in_generate=True)
                fp32_actual = chunked.logits[0].float().cpu()
                del chunked
            finally:
                model._prefill = original
        difference32 = fp32_actual-fp32_expected
        fp32_check = dict(max_logit_error=difference32.abs().max().item(),
                          rms_logit_error=difference32.square().mean().sqrt().item(),
                          argmax_matches=int((fp32_actual.argmax(-1)==fp32_expected.argmax(-1)).sum()))
        print(f'FP32 cache/mask correctness check: {fp32_check}', flush=True)
        if not (torch.isfinite(difference32).all() and fp32_check['max_logit_error'] < .005
                and fp32_check['rms_logit_error'] < .001):
            raise RuntimeError(f'FP32 chunked prefill check failed: {fp32_check}')
    finally:
        for name, parameter in model.named_parameters():
            if parameter.dtype != dtypes[name]:
                parameter.data = parameter.data.to(dtypes[name])
        torch.backends.cuda.matmul.allow_tf32 = old_tf32
        torch.cuda.empty_cache()
    checks = []
    for extra in (0, 12):
        if extra:
            # Identical forced continuation for both implementations in each row.
            addition = processor.tokenizer('轨迹从起点开始向左移动，然后转向。', return_tensors='pt')['input_ids'].to(model.device)
            addition = addition[:, :extra].expand(8, -1)
            inputs['input_ids'] = torch.cat((inputs['input_ids'], addition), dim=-1)
            inputs['attention_mask'] = torch.cat((inputs['attention_mask'], torch.ones_like(addition)), dim=-1)
            if 'mm_token_type_ids' in inputs:
                inputs['mm_token_type_ids'] = torch.cat((inputs['mm_token_type_ids'], torch.zeros_like(addition)), dim=-1)
        with torch.inference_mode():
            reference = model.generate(**inputs, max_new_tokens=1, do_sample=False,
                                       output_logits=True, return_dict_in_generate=True)
            expected = reference.logits[0].float().cpu()
            del reference
            original = install_chunked_prefill(model, chunk_size=256)
            chunked = model.generate(**inputs, max_new_tokens=1, do_sample=False,
                                     output_logits=True, return_dict_in_generate=True)
            actual = chunked.logits[0].float().cpu()
            del chunked
        model._prefill = original
        difference = actual-expected
        rms = difference.square().mean().sqrt().item()
        relative_rms = rms / max(expected.square().mean().sqrt().item(), 1.)
        maximum = difference.abs().max().item()
        total_variation = .5*(actual.softmax(-1)-expected.softmax(-1)).abs().sum(-1)
        check = dict(added_prefix_tokens=extra, rms_logit_error=rms,
                     relative_rms_logit_error=relative_rms, max_logit_error=maximum,
                     max_probability_total_variation=total_variation.max().item(),
                     argmax_matches=int((actual.argmax(-1)==expected.argmax(-1)).sum()))
        checks.append(check)
        print(f'Prefill numerical check: {check}', flush=True)
        # FP32 above checks implementation correctness. For BF16 the meaningful
        # criterion is probability-distribution deviation; raw logits can shift.
        if not (torch.isfinite(difference).all() and total_variation.max().item() < .03):
            raise RuntimeError(f'Chunked prefill numerical validation failed: {checks}')
    del inputs
    torch.cuda.empty_cache()
    return {'independent_contexts': 8, 'validation_chunk_size': 256,
            'numerical_validation_passed': True, 'fp32_check': fp32_check, 'checks': checks}

#!/usr/bin/env python3
"""Two saved long requests: stock single inference and first-token prefill check."""
import hashlib
import json
import os
import time
from pathlib import Path

from qwen_prompt_search import MODEL, dump, parse

ROOT = Path(__file__).resolve().parents[1] / 'results/qwen_diagnostic/group8_p12'


def main():
    import torch
    from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration
    from qwen_chunked_prefill import install_chunked_prefill

    target = ROOT / 'single_control'
    target.mkdir(exist_ok=True)
    processor = AutoProcessor.from_pretrained(MODEL, local_files_only=True)
    processor.tokenizer.padding_side = 'left'
    model = Qwen3_5ForConditionalGeneration.from_pretrained(
        MODEL, dtype='auto', device_map='auto', local_files_only=True).eval()
    checks = []
    for case in ('group_02/episode_005', 'group_03/episode_007'):
        source = ROOT / case / 'qwen_p12'
        request = (source / 'request.txt').read_text()
        batch = json.loads((source / 'result.json').read_text())
        folder = target / case.replace('/', '_')
        folder.mkdir(exist_ok=True)
        (folder / 'request.txt').write_text(request)
        chat = [{'role': 'user', 'content': [{'type': 'text', 'text': request}]}]
        inputs = processor.apply_chat_template(
            chat, add_generation_prompt=True, enable_thinking=False,
            tokenize=True, return_dict=True, return_tensors='pt').to(model.device)
        torch.cuda.synchronize()
        start = time.perf_counter()
        with torch.inference_mode():
            stock = model.generate(**inputs, max_new_tokens=512, do_sample=False,
                                   output_logits=True, return_dict_in_generate=True)
        torch.cuda.synchronize()
        seconds = time.perf_counter() - start
        expected = stock.logits[0].float().cpu()
        raw = processor.decode(stock.sequences[0, inputs['input_ids'].shape[-1]:],
                               skip_special_tokens=True, clean_up_tokenization_spaces=False)
        (folder / 'response.txt').write_text(raw)
        parsed, error = parse(raw)
        del stock
        torch.cuda.empty_cache()
        original = install_chunked_prefill(model, chunk_size=2048)
        try:
            with torch.inference_mode():
                chunked = model.generate(**inputs, max_new_tokens=1, do_sample=False,
                                         output_logits=True, return_dict_in_generate=True)
            actual = chunked.logits[0].float().cpu()
            del chunked
        finally:
            model._prefill = original
        check = dict(case=case, stock_parsed=parsed, stock_parse_error=error,
                     batch_parsed=batch['parsed'], stock_generation_seconds=seconds,
                     input_tokens=int(inputs['input_ids'].shape[-1]),
                     request_sha256=hashlib.sha256(request.encode()).hexdigest(),
                     first_token_probability_total_variation=float(
                         .5 * (actual.softmax(-1) - expected.softmax(-1)).abs().sum()),
                     first_token_argmax_matches=bool(actual.argmax(-1) == expected.argmax(-1)),
                     first_token_logit_rms_error=float((actual - expected).square().mean().sqrt()),
                     pbs_job_id=os.environ.get('PBS_JOBID'),
                     limit='Two selected disagreement cases; single unpadded long contexts. '
                           'First-token agreement does not certify all padded batch states or later outputs.')
        dump(folder / 'result.json', check)
        checks.append(check)
        dump(target / 'results.json', checks)
        print(case, parsed, 'prefill_TV', check['first_token_probability_total_variation'], flush=True)
        del inputs
        torch.cuda.empty_cache()


if __name__ == '__main__':
    main()

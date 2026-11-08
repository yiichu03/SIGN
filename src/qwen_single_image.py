"""Independent single-image scores; batching never exposes another sample's image."""
import json
import math
import os
import re
import time
from pathlib import Path
from numbers import Real
from qwen_topdown import strict_json


def validate_metadata(item):
    """Require measured area and actions; never derive m² from percentages."""
    value = dict(item)
    count, area = value.get('action_count'), value.get('new_area_m2')
    if type(count) is not int or count <= 0:
        raise ValueError('action_count must be a positive integer')
    if isinstance(area, bool) or not isinstance(area, Real) or not math.isfinite(area) or area < 0:
        raise ValueError('new_area_m2 must be supplied as finite, nonnegative measured m²')
    ratio = float(area) / count
    supplied = value.get('new_area_m2_per_action', ratio)
    if (isinstance(supplied, bool) or not isinstance(supplied, Real)
            or not math.isfinite(supplied) or not math.isclose(supplied, ratio, rel_tol=1e-6, abs_tol=1e-9)):
        raise ValueError('new_area_m2_per_action disagrees with area / action_count')
    value.update(new_area_m2=float(area), new_area_m2_per_action=ratio)
    if 'total_covered_area_m2' in value or 'prior_seen_area_m2' in value:
        total, prior = value.get('total_covered_area_m2'), value.get('prior_seen_area_m2')
        for field, number in [('total_covered_area_m2', total), ('prior_seen_area_m2', prior)]:
            if isinstance(number, bool) or not isinstance(number, Real) or not math.isfinite(number) or number < 0:
                raise ValueError(field + ' must be finite nonnegative measured m²')
        if not math.isclose(total, prior + area, rel_tol=1e-6, abs_tol=1e-9):
            raise ValueError('Total covered area must equal prior seen area + new area')
        value.update(total_covered_area_m2=float(total), prior_seen_area_m2=float(prior))
    return value


def load_manifest(path):
    """Two groups of eight; grouping is bookkeeping, not model context."""
    path = Path(path).resolve()
    spec = strict_json(path.read_text())
    groups = spec['groups']
    if len(groups) != 2 or len({g['id'] for g in groups}) != 2:
        raise ValueError('Expected two uniquely named groups')
    rows = []
    for group in groups:
        if len(group['items']) != 8 or len({r['id'] for r in group['items']}) != 8:
            raise ValueError('Each group requires eight unique image IDs')
        for item in group['items']:
            row = validate_metadata(item)
            if not isinstance(row['id'], str) or not row['id']:
                raise ValueError('Image ID must be a nonempty string')
            image = (path.parent / row['image']).resolve()
            if not image.is_file():
                raise FileNotFoundError(image)
            row.update(group_id=group['id'], image=str(image))
            rows.append(row)
    return spec, rows


def probabilities_from_logits(logits):
    """Temperature=1 softmax restricted to A/B/C, then ordinal expectation."""
    if len(logits) != 3 or any(isinstance(x, bool) or not isinstance(x, Real) or not math.isfinite(x) for x in logits):
        raise ValueError('Expected three finite candidate logits')
    weights = [math.exp(float(x) - max(logits)) for x in logits]
    p = [x / sum(weights) for x in weights]
    return dict(p_low=p[0], p_medium=p[1], p_high=p[2], q=0.5 * p[1] + p[2])


def choice_softmax(logits):
    """Actual candidate-token probabilities, also supporting binary decisions."""
    if len(logits) < 2 or any(isinstance(x, bool) or not isinstance(x, Real)
            or not math.isfinite(x) for x in logits):
        raise ValueError('Expected at least two finite candidate logits')
    weights=[math.exp(float(x)-max(logits)) for x in logits]
    return [v/sum(weights) for v in weights]


def response_positions(masks):
    """Last prompt token predicts the first answer token. Require left padding."""
    positions = []
    for row in masks:
        if not row or any(x not in (0, 1) for x in row) or row[-1] != 1 or row != sorted(row):
            raise ValueError('Expected a nonempty left-padded attention mask')
        positions.append(len(row) - 1)
    return positions


def conversations(images, prompt, metadata=None):
    if not 1 <= len(images) <= 8 or not prompt.strip():
        raise ValueError('Expected 1-8 independent image requests and a nonempty prompt')
    if metadata is not None and len(metadata) != len(images):
        raise ValueError('Metadata must correspond one-to-one with images')
    rows = []
    for i, image in enumerate(images):
        content = [{'type':'text','text':prompt}, {'type':'image','image':str(Path(image).resolve())}]
        if metadata is not None:
            item = validate_metadata(metadata[i])
            if 'image' in item and Path(item['image']).resolve() != Path(image).resolve():
                raise ValueError('Metadata image does not match its batch row')
            stats = {k:item[k] for k in ('action_count','new_area_m2','new_area_m2_per_action')}
            for key in ('prior_seen_area_m2', 'total_covered_area_m2'):
                if key in item:
                    stats[key] = item[key]
            content.append({'type':'text','text':'Current image statistics (m² and m²/action): '+json.dumps(stats)})
        rows.append([{'role':'user','content':content}])
    return rows


def multi_image_conversations(requests, prompt):
    """One labelled multi-image episode per row, never a joint batch dialogue."""
    if not 1 <= len(requests) <= 8 or not prompt.strip():
        raise ValueError('Expected 1-8 independent requests and a prompt')
    messages=[]
    for request in requests:
        images=request.get('images',[])
        if not 1 <= len(images) <= 8:
            raise ValueError('Expected 1-8 images in each independent request')
        roles=[x.get('role','') for x in images]
        if len(set(roles))!=len(roles) or any(not re.fullmatch(r'[A-Z][A-Z0-9_]*',x) for x in roles):
            raise ValueError('Image roles must be unique explicit labels')
        context=request.get('context','')
        if not isinstance(context,str) or len(context)>16000:
            raise ValueError('Invalid request context')
        content=[dict(type='text',text=prompt)]
        for item in images:
            content.extend([dict(type='text',text='IMAGE ROLE: '+item['role']),
                dict(type='image',image=str(Path(item['image']).resolve()))])
        if context:
            content.append(dict(type='text',text=context))
        messages.append([dict(role='user',content=content)])
    return messages


def parse_score(raw, truncated=False):
    if truncated:
        raise ValueError('Truncated answer')
    value = strict_json(raw)
    if not isinstance(value, dict) or set(value) != {'score'}:
        raise ValueError('Expected exactly {"score": number or null}')
    score = value['score']
    if score is not None and (type(score) not in (int,float) or not math.isfinite(score) or not 0 <= score <= 1):
        raise ValueError('Score must be in [0,1], or null for unknown')
    return value


class SingleImageJudge:
    def __init__(self, model_dir, prompt, max_image_pixels=262144, max_new_tokens=64, seed=100, dtype='auto'):
        start=time.perf_counter()
        import torch
        import transformers
        from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration
        if not os.environ.get('PBS_JOBID') or not torch.cuda.is_available():
            raise RuntimeError('Use a PBS GPU job')
        torch.set_num_threads(1);torch.manual_seed(seed)
        self.torch=torch;self.prompt=prompt;self.max_pixels=max_image_pixels;self.max_new_tokens=max_new_tokens
        self.processor=AutoProcessor.from_pretrained(model_dir,local_files_only=True)
        self.processor.tokenizer.padding_side='left'
        self.model=Qwen3_5ForConditionalGeneration.from_pretrained(model_dir,dtype=dtype,device_map='cuda:0',local_files_only=True).eval()
        torch.cuda.synchronize()
        self.load_seconds=time.perf_counter()-start
        self.environment={'torch':torch.__version__,'transformers':transformers.__version__,
           'gpu':torch.cuda.get_device_name(),'model_dir':str(model_dir),'model_load_seconds':self.load_seconds,
           'dtype':str(self.model.dtype)}

    def _prepare(self, images, metadata=None):
        grouped=bool(images and isinstance(images[0],dict))
        if grouped:
            if metadata is not None:
                raise ValueError('Multi-image context belongs to its independent request')
            messages=multi_image_conversations(images,self.prompt)
            counts=[len(r['images']) for r in images]
        else:
            messages=conversations(images,self.prompt,metadata)
            counts=[1]*len(images)
        inputs=self.processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,
            return_dict=True,return_tensors='pt',processor_kwargs={'text_kwargs':{'padding':True},
            'images_kwargs':{'size':{'shortest_edge':65536,'longest_edge':self.max_pixels}}}).to(self.model.device)
        if inputs['image_grid_thw'].shape[0]!=sum(counts) or inputs['input_ids'].shape[0]!=len(images):
            raise RuntimeError('Multi-image count/batch row mismatch')
        return inputs, messages

    def class_probabilities(self, images, metadata, labels=('A','B','C')):
        """Read three real next-answer logits; ABC remains the default interface."""
        labels = tuple(labels)
        if len(labels) != 3 or len(set(labels)) != 3 or any(not isinstance(x,str) or not x for x in labels):
            raise ValueError('Expected three distinct nonempty candidate labels')
        results,audit=self.choice_probabilities(images,metadata,labels)
        for result in results:
            if result['valid']:
                result.update(probabilities_from_logits(result['logits']))
            else:
                result.update(p_low=None,p_medium=None,p_high=None,q=None)
        return results,audit

    def choice_probabilities(self, images, metadata=None, labels=('left','right','keep')):
        """Same loader/processor/readout for real two- or three-word choices."""
        labels=tuple(labels)
        if len(labels) not in (2,3) or len(set(labels))!=len(labels) or any(not isinstance(x,str) or not x for x in labels):
            raise ValueError('Expected two or three distinct candidate labels')
        torch = self.torch
        start = time.perf_counter()
        inputs, messages = self._prepare(images, metadata)
        masks = inputs['attention_mask'].cpu().tolist()
        positions = response_positions(masks)
        tokenizer = self.processor.tokenizer
        token_ids = [tokenizer.encode(c, add_special_tokens=False) for c in labels]
        if any(len(ids) != 1 for ids in token_ids) or len({ids[0] for ids in token_ids}) != len(labels):
            raise ValueError('Candidate labels must be distinct single tokens')
        token_ids = [ids[0] for ids in token_ids]
        if tokenizer.batch_decode([[i] for i in token_ids]) != list(labels):
            raise ValueError('Candidate token IDs do not decode to the requested labels')
        rendered = [self.processor.apply_chat_template(m, tokenize=False, add_generation_prompt=True,
                    enable_thinking=False) for m in messages]
        # Verify the exact assistant boundary: appending each label adds one token,
        # without changing/merging the trailing prompt tokens.
        for text in rendered:
            prefix = tokenizer.encode(text, add_special_tokens=False)
            for label, token_id in zip(labels, token_ids):
                if tokenizer.encode(text+label, add_special_tokens=False) != prefix+[token_id]:
                    raise ValueError('Candidate is not one token at the actual answer boundary')
        with torch.inference_mode():
            logits = self.model(**inputs, logits_to_keep=1, use_cache=False, return_dict=True).logits[:, -1, :].float()
        selected = logits[:, token_ids].cpu().tolist()
        mass = (torch.logsumexp(logits[:, token_ids], dim=-1)-torch.logsumexp(logits, dim=-1)).exp().cpu().tolist()
        top_values, top_ids = logits.topk(5, dim=-1)
        results = []
        for values, candidate_mass in zip(selected, mass):
            try:
                result = dict(probabilities=choice_softmax(values),labels=list(labels),valid=True,error=None)
            except ValueError as exc:
                result = dict(probabilities=None,labels=list(labels),valid=False,error=str(exc))
            result['logits'] = [v if math.isfinite(v) else str(v) for v in values]
            result['candidate_mass'] = candidate_mass if math.isfinite(candidate_mass) else None
            results.append(result)
        audit = {'token_ids':dict(zip(labels,token_ids)), 'decoded_labels':tokenizer.batch_decode([[i] for i in token_ids]),
            'response_positions':positions, 'padding_side':tokenizer.padding_side,
            'input_token_ids':inputs['input_ids'].cpu().tolist(), 'attention_mask':masks,
            'image_grid_thw':inputs['image_grid_thw'].cpu().tolist(), 'rendered_chats':rendered,
            'images_per_row':[len(x['images']) if isinstance(x,dict) else 1 for x in images],
            'top_token_ids':top_ids.cpu().tolist(),
            'top_logits':[[v if math.isfinite(v) else str(v) for v in row] for row in top_values.cpu().tolist()],
            'temperature':1.0, 'seconds':time.perf_counter()-start}
        return results, audit

    def verify_choices(self, requests, labels, tolerance=1e-4):
        """Multi-image order, variable-length padding, row isolation and logits."""
        results,audit=self.choice_probabilities(requests,labels=labels)
        offset=0;batch_delta=0.0
        for i,row in enumerate(requests):
            singles,other=self.choice_probabilities([row],labels=labels)
            active=[t for t,m in zip(audit['input_token_ids'][i],audit['attention_mask'][i]) if m]
            assert active==other['input_token_ids'][0],'Multi-image batch/solo token mismatch'
            count=audit['images_per_row'][i]
            assert audit['image_grid_thw'][offset:offset+count]==other['image_grid_thw'],'Image order/grid mismatch'
            offset+=count
            assert results[i]['valid'] and singles[0]['valid']
            batch_delta=max(batch_delta,max(abs(a-b) for a,b in zip(results[i]['probabilities'],singles[0]['probabilities'])))
        swapped,_=self.choice_probabilities(requests[::-1],labels=labels)
        permutation=max(abs(a-b) for original,other in zip(results,swapped[::-1]) for a,b in zip(original['probabilities'],other['probabilities']))
        inputs,_=self._prepare(requests)
        with self.torch.inference_mode():
            generated=self.model.generate(**inputs,max_new_tokens=1,do_sample=False,return_dict_in_generate=True,
                output_logits=True,pad_token_id=self.processor.tokenizer.pad_token_id)
        ids=list(audit['token_ids'].values())
        raw=generated.logits[0][:,ids].float().cpu().tolist()
        generation=max(abs(a-b) for result,values in zip(results,raw) for a,b in zip(result['probabilities'],choice_softmax(values)))
        return dict(passed=max(batch_delta,permutation,generation)<=tolerance,token_ids=audit['token_ids'],
            images_per_row=audit['images_per_row'],padding_counts=[len(m)-sum(m) for m in audit['attention_mask']],
            response_positions=audit['response_positions'],single_batch_max_delta=batch_delta,
            batch_permutation_max_delta=permutation,forward_generation_max_delta=generation,tolerance=tolerance,
            first_generated_tokens=self.processor.tokenizer.batch_decode(generated.sequences[:,inputs['input_ids'].shape[-1]:].cpu()),
            input_audit=audit)

    def verify_readout(self, images, metadata, tolerance=1e-4, labels=('A','B','C')):
        """Small GPU check: batch vs singles, then raw first-generation logits."""
        results, audit = self.class_probabilities(images, metadata, labels=labels)
        max_delta = 0.0
        single_results = []
        for i in range(len(images)):
            single, single_audit = self.class_probabilities(images[i:i+1], None if metadata is None else metadata[i:i+1], labels=labels)
            active = [t for t,m in zip(audit['input_token_ids'][i],audit['attention_mask'][i]) if m]
            if active != single_audit['input_token_ids'][0] or audit['image_grid_thw'][i] != single_audit['image_grid_thw'][0]:
                raise RuntimeError('Single/batch input mismatch')
            if not results[i]['valid'] or not single[0]['valid']:
                raise RuntimeError('Invalid probability in GPU verification')
            single_results.append(single[0])
            max_delta = max(max_delta, max(abs(results[i][k]-single[0][k]) for k in ('p_low','p_medium','p_high','q')))
        permuted, _ = self.class_probabilities(images[::-1],None if metadata is None else metadata[::-1], labels=labels)
        permutation_delta = max(abs(a[k]-b[k]) for a,b in zip(results,permuted[::-1])
            for k in ('p_low','p_medium','p_high','q'))
        inputs, _ = self._prepare(images, metadata)
        with self.torch.inference_mode():
            generated = self.model.generate(**inputs, max_new_tokens=1, do_sample=False,
                return_dict_in_generate=True, output_logits=True, pad_token_id=self.processor.tokenizer.pad_token_id)
        ids = list(audit['token_ids'].values())
        raw = generated.logits[0][:, ids].float().cpu().tolist()
        generation_delta = max(abs(result[k]-probabilities_from_logits(values)[k])
            for result,values in zip(results,raw) for k in ('p_low','p_medium','p_high','q'))
        return {'passed':max(max_delta,generation_delta,permutation_delta)<=tolerance,
            'token_ids':audit['token_ids'],'decoded_labels':audit['decoded_labels'],
            'padding_counts':[len(m)-sum(m) for m in audit['attention_mask']],
            'response_positions':audit['response_positions'],'single_batch_max_probability_delta':max_delta,
            'permutation_max_probability_delta':permutation_delta,'batch_results':results,'single_results':single_results,
            'forward_generation_max_probability_delta':generation_delta,'tolerance':tolerance,
            'first_generated_token_ids':generated.sequences[:,inputs['input_ids'].shape[-1]].cpu().tolist(),
            'first_generated_tokens':self.processor.tokenizer.batch_decode(generated.sequences[:,inputs['input_ids'].shape[-1]:].cpu())}

    def score(self, images):
        """Time local PNG read+processor+H2D+generation+decode+strict parsing."""
        torch=self.torch;torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
        inputs, _ = self._prepare(images)
        torch.cuda.synchronize();prepared=time.perf_counter()
        with torch.inference_mode():
            generated=self.model.generate(**inputs,max_new_tokens=self.max_new_tokens,do_sample=False,
                pad_token_id=self.processor.tokenizer.pad_token_id)
        torch.cuda.synchronize();generated_at=time.perf_counter()
        ids=generated[:,inputs['input_ids'].shape[-1]:].cpu().tolist()
        eos=self.model.generation_config.eos_token_id;eos=eos if isinstance(eos,list) else [eos]
        answers=[]
        for image,row in zip(images,ids):
            stop=next((i+1 for i,t in enumerate(row) if t in eos),len(row));row=row[:stop]
            truncated=len(row)>=self.max_new_tokens and row[-1] not in eos
            raw=self.processor.decode(row,skip_special_tokens=True,clean_up_tokenization_spaces=False)
            try:parsed=parse_score(raw,truncated);error=None
            except (ValueError,KeyError,TypeError) as exc:parsed=None;error=str(exc)
            answers.append({'image':str(image),'raw':raw,'token_ids':row,'output_tokens':len(row),'parsed':parsed,'parse_error':error,'truncated':truncated})
        ended=time.perf_counter()
        return {'batch_size':len(images),'total_seconds':ended-start,'preprocess_h2d_seconds':prepared-start,
            'generation_seconds':generated_at-prepared,'decode_parse_seconds':ended-generated_at,
            'peak_gpu_gib':torch.cuda.max_memory_allocated()/1024**3,
            'input_tokens':inputs['attention_mask'].sum(dim=1).cpu().tolist(),
            'input_token_ids':inputs['input_ids'].cpu().tolist(),'image_grid_thw':inputs['image_grid_thw'].cpu().tolist(),
            'answers':answers}

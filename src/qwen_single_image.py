"""Independent single-image scores; batching never exposes another sample's image."""
import json
import math
import os
import time
from pathlib import Path
from qwen_topdown import strict_json


def conversations(images, prompt):
    if not 1 <= len(images) <= 8 or not prompt.strip():
        raise ValueError('Expected 1-8 independent image requests and a nonempty prompt')
    return [[{'role':'user','content':[{'type':'text','text':prompt},
             {'type':'image','image':str(Path(image).resolve())}]}] for image in images]


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
    def __init__(self, model_dir, prompt, max_image_pixels=262144, max_new_tokens=64, seed=100):
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
        self.model=Qwen3_5ForConditionalGeneration.from_pretrained(model_dir,dtype='auto',device_map='cuda:0',local_files_only=True).eval()
        torch.cuda.synchronize()
        self.load_seconds=time.perf_counter()-start
        self.environment={'torch':torch.__version__,'transformers':transformers.__version__,
           'gpu':torch.cuda.get_device_name(),'model_dir':str(model_dir),'model_load_seconds':self.load_seconds}

    def score(self, images):
        """Time local PNG read+processor+H2D+generation+decode+strict parsing."""
        torch=self.torch;torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
        messages=conversations(images,self.prompt)
        inputs=self.processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,
            return_dict=True,return_tensors='pt',processor_kwargs={'text_kwargs':{'padding':True},
            'images_kwargs':{'size':{'shortest_edge':65536,'longest_edge':self.max_pixels}}}).to(self.model.device)
        if inputs['image_grid_thw'].shape[0]!=len(images) or inputs['input_ids'].shape[0]!=len(images):
            raise RuntimeError('Expected one image in each independent batch row')
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

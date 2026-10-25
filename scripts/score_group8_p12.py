#!/usr/bin/env python3
"""Unchanged p12, independent JSON-only requests, same-task batches of eight."""
import hashlib
import json
import os
import time
from datetime import datetime,timezone
from pathlib import Path
from qwen_prompt_search import CONTEXT,HEADER,FORMAT,MODEL,parse,dump

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE/'results/qwen_diagnostic/group8_p12'

def main():
    import torch
    import transformers
    from transformers import AutoProcessor,Qwen3_5ForConditionalGeneration
    from qwen_chunked_prefill import install_chunked_prefill
    torch.manual_seed(100)
    assert (ROOT/'collection_complete.json').exists()
    spec_path=BASE/'results/qwen_diagnostic/prompt_iteration/prompts/p12.json'
    spec=json.loads(spec_path.read_text())
    meta=dict(status='loading',started_at=datetime.now(timezone.utc).isoformat(),job=os.environ.get('PBS_JOBID'),prompt_sha256=hashlib.sha256(spec_path.read_bytes()).hexdigest(),mode='json_only',batch_size=8,model=str(MODEL),torch=torch.__version__,transformers=transformers.__version__)
    dump(ROOT/'qwen_run.json',meta)
    processor=AutoProcessor.from_pretrained(MODEL,local_files_only=True);processor.tokenizer.padding_side='left'
    model=Qwen3_5ForConditionalGeneration.from_pretrained(MODEL,dtype='auto',device_map='auto',local_files_only=True).eval()
    install_chunked_prefill(model,chunk_size=2048)
    meta.update(status='running',gpu=torch.cuda.get_device_name())
    dump(ROOT/'qwen_run.json',meta)
    eos=model.generation_config.eos_token_id;eos=set(eos if isinstance(eos,list) else [eos])
    try:
        for g in json.loads((ROOT/'manifest.json').read_text())['groups']:
            group=ROOT/g['group'];assert (group/'collection_verified.json').exists()
            folders=sorted(group.glob('episode_*'));assert len(folders)==8
            if all((f/'qwen_p12/result.json').exists() for f in folders):continue
            conversations=[]
            for f in folders:
                d=json.loads((f/'waypoints.json').read_text())
                request=HEADER['json_only']+'\n'+spec.get('context',CONTEXT)+'\n'+spec['body'].strip()+'\n\n'+spec.get('output_format',FORMAT)+'\nWAYPOINT_JSON:\n'+json.dumps(d,ensure_ascii=False,separators=(',',':'))
                target=f/'qwen_p12';target.mkdir(exist_ok=True);(target/'request.txt').write_text(request)
                conversations.append([{'role':'user','content':[{'type':'text','text':request}]}])
            torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
            inputs=processor.apply_chat_template(conversations,add_generation_prompt=True,enable_thinking=False,tokenize=True,return_dict=True,return_tensors='pt',padding=True).to(model.device)
            torch.cuda.synchronize();prepared=time.perf_counter()
            with torch.inference_mode():generated=model.generate(**inputs,max_new_tokens=512,do_sample=False)
            torch.cuda.synchronize();end=time.perf_counter()
            for i,f in enumerate(folders):
                ids=generated[i,inputs['input_ids'].shape[-1]:].tolist();stop=next((j+1 for j,x in enumerate(ids) if x in eos),len(ids));ids=ids[:stop]
                raw=processor.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
                (f/'qwen_p12/response.txt').write_text(raw)
                parsed,error=parse(raw)
                n=len(json.loads((f/'waypoints.json').read_text())['waypoints'])
                dump(f/'qwen_p12/result.json',dict(parsed=parsed,parse_error=error,redundancy_score={'NONE':0,'SOME':1,'CLEAR':2}.get(parsed['label']) if parsed else None,interval_bounds_valid=parsed is not None and all(0<=a<=b<=n for a,b in parsed['intervals']),batch_seconds=end-start,amortized_seconds=(end-start)/8,preprocessing_seconds=prepared-start,generation_seconds=end-prepared,input_tokens=int(inputs['attention_mask'][i].sum()),output_tokens=len(ids),hit_output_limit=len(ids)>=512 and ids[-1] not in eos,request_sha256=hashlib.sha256((f/'qwen_p12/request.txt').read_bytes()).hexdigest(),batch_id=g['group'],members=[p.name for p in folders],pbs_job_id=meta['job']))
            dump(group/'qwen_batch.json',dict(seconds=end-start,amortized_seconds=(end-start)/8,peak_gib=torch.cuda.max_memory_allocated()/1024**3,padded_input_tokens=inputs['input_ids'].shape[-1],batch_size=8))
            del inputs,generated
            print('Completed batch',g['group'],round(end-start,2),'seconds',flush=True)
        meta['status']='complete'
    except Exception as e:
        meta.update(status='failed',error=repr(e));raise
    finally:
        meta['finished_at']=datetime.now(timezone.utc).isoformat();dump(ROOT/'qwen_run.json',meta)

if __name__=='__main__':main()

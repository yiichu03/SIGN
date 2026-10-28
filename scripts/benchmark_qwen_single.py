#!/usr/bin/env python3
"""Latency benchmark, arbitrary prompt; not a judge quality evaluation."""
import argparse,sys,json,hashlib,time,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from qwen_single_image import SingleImageJudge
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model-dir',required=True);p.add_argument('--prompt',required=True);p.add_argument('--images',nargs=8,required=True);p.add_argument('--out',required=True);p.add_argument('--repeats',type=int,default=3)
a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False);prompt=Path(a.prompt).read_text()
meta={'images':{str(i):hashlib.sha256(Path(i).read_bytes()).hexdigest() for i in a.images},'prompt':prompt,
      'purpose':'One independent score per image; no group or relative scoring; latency only','repeats':a.repeats,
      'pixels':262144,'max_new_tokens':64,'seed':100,'enable_thinking':False,'do_sample':False}
(out/'inputs.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
judge=SingleImageJudge(a.model_dir,prompt);meta.update(judge.environment)
results=[]
def call(label,images):
 result=judge.score(images);result['label']=label;results.append(result)
 (out/(str(len(results)).zfill(2)+'_'+label+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(label,round(result['total_seconds'],4),'s',sum(x['parse_error'] is None for x in result['answers']),'valid',flush=True)
 return result
cold=call('first_single',a.images[:1]);call('warmup_batch8',a.images)
for repeat in range(a.repeats):
 call('single_'+str(repeat),a.images[:1])
 call('batch8_'+str(repeat),a.images)
start=time.perf_counter();serial=[call('serial_'+str(i),[image]) for i,image in enumerate(a.images)];serial_seconds=time.perf_counter()-start
start=time.perf_counter();halves=[call('batch4_'+str(i),a.images[i:i+4]) for i in (0,4)];batch4_seconds=time.perf_counter()-start
single=[r['total_seconds'] for r in results if r['label'].startswith('single_')]
batched=[r['total_seconds'] for r in results if r['label'].startswith('batch8_')]
summary=dict(meta,first_call_seconds=cold['total_seconds'],load_plus_first_call_seconds=judge.load_seconds+cold['total_seconds'],
    single_median_seconds=statistics.median(single),batch8_median_seconds=statistics.median(batched),batch8_min_seconds=min(batched),batch8_max_seconds=max(batched),
    serial8_seconds=serial_seconds,batch4_twice_seconds=batch4_seconds,serial8_inference_sum_seconds=sum(x['total_seconds'] for x in serial),
    batch4_inference_sum_seconds=sum(x['total_seconds'] for x in halves),peak_gpu_gib=max(r['peak_gpu_gib'] for r in results),
    valid_answers=sum(x['parse_error'] is None for r in results for x in r['answers']),answers=sum(len(r['answers']) for r in results),
    batch8_output_tokens=[[x['output_tokens'] for x in r['answers']] for r in results if r['label'].startswith('batch8_')],
    semantics='Warm timings exclude model load and trajectory-to-image rendering, include local PNG decode/processor/H2D/generate/decode/parse; batch rows have independent attention and one image each. Serial and batch4 wall times include audit JSON writes; inference sums exclude those writes.')
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

#!/usr/bin/env python3
"""English prompt experiments on the frozen 60-case development collection."""
import argparse
import csv
import hashlib
import json
import os
import re
import statistics
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'results/qwen_diagnostic/graded60'
ROOT=BASE/'results/qwen_diagnostic/prompt_iteration'
MODEL=BASE.parent/'models/Qwen3.5-9B'
MODES=('image_only','json_only','image_json')
LABELS=('NONE','SOME','CLEAR','UNCERTAIN')
HUMAN={'无或可忽略':'NONE','有':'SOME','明显有':'CLEAR','不确定/边界':'UNCERTAIN','未标注':None}
HEADER={
'image_only': 'You are given ONE complete ImageNav trajectory as a white-background top-down plot. No waypoint JSON is provided.',
'json_only': 'You are given ONE complete ImageNav trajectory as waypoint JSON. No plot is provided.',
'image_json': 'You are given ONE complete ImageNav trajectory as a white-background top-down plot AND its matching waypoint JSON.',
}
CONTEXT='''The agent is navigating an initially unfamiliar environment to find a visual goal. You do not have its camera observations, goal image, occupancy map, visibility history or shortest path. Judge observable search behavior, not task success or optimality. END is the termination point, not proof that the goal was reached. Increasing step numbers or changing trajectory colors do not by themselves imply spatial or exploratory progress. Do not invent obstacles, rooms, goal locations or measured information gain.
Plot: the continuous color bar encodes step order; labels mark sparse steps; arrows show headings; START and END mark the first recorded pose and final pose. A line crossing or overlapping projection alone does not establish repeated searching. The white background contains no walls. Read the color bar rather than assuming a particular color is early or late.
JSON: each waypoint is the pose AFTER the indexed action. map_row/map_col are integer pixels, not meters; equal pixels do not prove identical continuous poses. heading_rad is periodic modulo 2*pi. action is [angular_velocity, linear_velocity], NORMALIZED commands, not physical velocities; negative linear commands do not by themselves prove backward movement. Infer executed motion from poses, not command signs. Multiple low-level steps may be one observation turn. Treat unavailable fields as unavailable, not as negative evidence.
'''
FORMAT='''Return only one JSON object with these keys:
{"label":"NONE|SOME|CLEAR|UNCERTAIN","intervals":[[start_step,end_step]],"repeated_path":"YES|NO|UNCERTAIN","behavior":"brief behavior type","evidence":"observable temporal evidence supporting the label","alternative":"plausible normal explanation considered, or why it is insufficient","stuck_or_recovery":"separate description with approximate steps, or none/uncertain"}
Use one allowed label, not the literal list. NONE means no material redundancy or only negligible overhead; SOME means material localized redundancy; CLEAR means sustained or recurring substantial redundancy; UNCERTAIN means the available evidence cannot resolve a plausible normal explanation versus material redundancy. Intervals should identify at most three strongest approximate candidate intervals; use [] when none can be identified. Keep evidence and alternative together under 90 English words. Do not include a hidden reasoning transcript, markdown fences, or extra text.
'''

def dump(p,d):
 p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');t.replace(p)

def freeze():
 out=ROOT/'human_reference.json'
 if out.exists():return
 rows=json.loads((DATA/'analysis_review2/case_comparison.json').read_text())
 for r in rows:
  p=DATA/r['case']/'review2.md';s=p.read_text();tail=s[s.index('## 人工复核'):]
  # The existing classification is a documented interpretation of free-text notes.
  if r['comment'] and r['comment'] not in tail:raise ValueError('Human note changed: '+r['case'])
  r['reference_label']=HUMAN[r['human']]
  r['raw_human_section']=tail
  r['review2_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
  r['stuck_related']='卡' in r['comment']
 dump(out,[{k:r[k] for k in ('case','human','comment','reference_label','raw_human_section','review2_sha256','stuck_related')} for r in rows])
 dump(ROOT/'protocol.json',dict(cases=60,prompt_limit=20,wave_size=5,modes=MODES,model=str(MODEL),batch_size=1,do_sample=False,enable_thinking=False,max_new_tokens=512,inputs='Original trajectory2.png and full corrected waypoint JSON; no goal/RGB/human labels in model inputs',selection='Development agreement only; all 60 repeatedly used for tuning; not held-out accuracy. 54 clear labels are primary, 5 boundary cases reported separately, 1 unlabeled excluded.',ranking='Compare balanced accuracy with abstentions counted as errors, positive recall, negative specificity, coverage, four-level agreement and reason quality. No label-frequency matching.'))

def request(case,mode,body,context=CONTEXT,output_format=FORMAT,footer=""):
 text=HEADER[mode]+'\n'+context+'\n'+body.strip()+'\n\n'+output_format
 if mode!='image_only':
  payload=json.loads((case/'waypoints_corrected.json').read_text())
  text+='\nWAYPOINT_JSON:\n'+json.dumps(payload,ensure_ascii=False,separators=(',',':'))
 if footer:text+='\n\nFINAL TASK REMINDER:\n'+footer
 return text

def parse(raw,kind='json'):
 try:
  if kind=='lines':
   fields={}
   for line in raw.splitlines():
    if ':' in line:
     k,v=line.split(':',1);fields[k.strip().lower()]=v.strip()
   obj=dict(label=fields['redundant_search'],intervals=json.loads(fields['steps']),repeated_path=fields['repeated_path'],behavior='See evidence',evidence=fields['evidence'],alternative=fields['alternative'],stuck_or_recovery=fields['stuck_or_recovery'])
  else:
   obj=json.JSONDecoder().raw_decode(raw[raw.index('{'):])[0]
   if kind=='binary_json':
    pair=(obj.get('redundant_search'),obj.get('severity'))
    mapping={('YES','LOCALIZED'):'SOME',('YES','SUBSTANTIAL'):'CLEAR',('NO','NEGLIGIBLE'):'NONE',('UNCERTAIN','UNRESOLVED'):'UNCERTAIN'}
    if pair not in mapping:raise ValueError('inconsistent binary/severity fields')
    obj['label']=mapping[pair]
  if obj.get('label') not in LABELS:raise ValueError('invalid label')
  if obj.get('repeated_path') not in ('YES','NO','UNCERTAIN'):raise ValueError('invalid repeated_path')
  intervals=obj.get('intervals')
  if not isinstance(intervals,list) or any(not isinstance(v,list) or len(v)!=2 or not all(isinstance(n,int) and not isinstance(n,bool) for n in v) for v in intervals):raise ValueError('invalid intervals')
  for k in ('behavior','evidence','alternative','stuck_or_recovery'):
   if not isinstance(obj.get(k),str):raise ValueError('missing text field '+k)
  return obj,None
 except (ValueError,KeyError,TypeError) as e:return None,str(e)

def run(prompt_id):
 import torch
 import transformers
 from transformers import AutoProcessor,Qwen3_5ForConditionalGeneration
 torch.manual_seed(100)
 spec=json.loads((ROOT/'prompts'/f'{prompt_id}.json').read_text());body=spec['body']
 out=ROOT/prompt_id;out.mkdir(exist_ok=True)
 meta=dict(spec_sha256=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),prompt_id=prompt_id,prompt_sha256=hashlib.sha256(body.encode()).hexdigest(),job_id=os.environ.get('PBS_JOBID'),status='loading',started_at=datetime.now(timezone.utc).isoformat())
 dump(out/'run.json',meta)
 processor=AutoProcessor.from_pretrained(MODEL,local_files_only=True)
 processor.tokenizer.padding_side='left'
 model=Qwen3_5ForConditionalGeneration.from_pretrained(MODEL,dtype='auto',device_map='auto',local_files_only=True).eval()
 meta.update(status='running',gpu=torch.cuda.get_device_name(),torch=torch.__version__,transformers=transformers.__version__,attention_backend=model.config.get_text_config()._attn_implementation)
 dump(out/'run.json',meta)
 refs=json.loads((ROOT/'human_reference.json').read_text())
 cases=sorted([DATA/r['case'] for r in refs],key=lambda p:-len(json.loads((p/'waypoints_corrected.json').read_text())['waypoints']))
 try:
  for mode in MODES:
   for i,case in enumerate(cases):
    folder=out/case.relative_to(DATA)/mode;folder.mkdir(parents=True,exist_ok=True)
    if (folder/'result.json').exists():continue
    text=request(case,mode,body,spec.get('context',CONTEXT),spec.get('output_format',FORMAT),spec.get('footer',''))
    (folder/'request.txt').write_text(text)
    content=[]
    if mode!='json_only':content.append({'type':'image','path':str(case/'trajectory2.png')})
    content.append({'type':'text','text':text})
    torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
    inputs=processor.apply_chat_template([{'role':'user','content':content}],add_generation_prompt=True,enable_thinking=False,tokenize=True,return_dict=True,return_tensors='pt').to(model.device)
    torch.cuda.synchronize();prepared=time.perf_counter()
    with torch.inference_mode():generated=model.generate(**inputs,max_new_tokens=512,do_sample=False)
    torch.cuda.synchronize();end=time.perf_counter()
    ids=generated[0,inputs['input_ids'].shape[-1]:];raw=processor.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
    (folder/'response.txt').write_text(raw)
    obj,error=parse(raw,spec.get('output_kind','json'))
    length=len(json.loads((case/'waypoints_corrected.json').read_text())['waypoints'])
    interval_valid=obj is not None and all(0<=a<=b<=length for a,b in obj['intervals'])
    dump(folder/'result.json',dict(prompt_id=prompt_id,case=str(case.relative_to(DATA)),mode=mode,parsed=obj,parse_error=error,interval_bounds_valid=interval_valid,excess_intervals=obj is not None and len(obj['intervals'])>3,seconds=end-start,preprocessing_seconds=prepared-start,generation_seconds=end-prepared,input_tokens=inputs['input_ids'].shape[-1],output_tokens=len(ids),hit_output_limit=len(ids)>=512,peak_gib=torch.cuda.max_memory_allocated()/1024**3,image=str(case/'trajectory2.png') if mode!='json_only' else None,prompt_sha256=meta['prompt_sha256'],request_sha256=hashlib.sha256(text.encode()).hexdigest(),job_id=meta['job_id']))
    del inputs,generated,ids
    print(f'{prompt_id} {mode} {i+1}/60 {end-start:.2f}s {obj["label"] if obj else "PARSE_ERROR"}',flush=True)
  meta['status']='complete'
 except Exception as e:
  meta.update(status='failed',error=repr(e));raise
 finally:
  meta['finished_at']=datetime.now(timezone.utc).isoformat();dump(out/'run.json',meta)
  analyze([prompt_id])

def _analyze(ids):
 refs=json.loads((ROOT/'human_reference.json').read_text());ref={r['case']:r for r in refs}
 for pid in ids:
  out=ROOT/pid;rows=[];summary=[]
  for mode in MODES:
   results=[json.loads(p.read_text()) for p in sorted(out.glob('val_*/episode_*/'+mode+'/result.json'))]
   counts=Counter();conf=Counter();correct=fp=fn=tp=tn=abstain=exact=0
   records=[]
   for r in results:
    h=ref[r['case']];p=r['parsed'];lab=p['label'] if p else 'INVALID';truth=h['reference_label'];counts[lab]+=1
    row=dict(case=r['case'],mode=mode,human=truth,prediction=lab,human_comment=h['comment'],seconds=r['seconds'],evidence=p['evidence'] if p else r['parse_error'],alternative=p['alternative'] if p else '',behavior=p['behavior'] if p else '',stuck_or_recovery=p['stuck_or_recovery'] if p else '',excluded_stuck_reference=h['stuck_related'],intervals=p['intervals'] if p else [],interval_bounds_valid=r['interval_bounds_valid'],hit_output_limit=r['hit_output_limit'])
    rows.append(row);records.append(row)
    if truth in ('NONE','SOME','CLEAR') and not h['stuck_related']:
     positive=truth!='NONE';predpos=lab in ('SOME','CLEAR');predneg=lab=='NONE'
     conf[(truth,lab)]+=1;exact+=lab==truth
     tp+=positive and predpos;tn+=not positive and predneg
     fp+=not positive and predpos;fn+=positive and predneg
     abstain+=lab in ('UNCERTAIN','INVALID')
   n=sum(conf.values());neg=sum(v for (h,p),v in conf.items() if h=='NONE');pos=n-neg
   s=dict(prompt_id=pid,mode=mode,completed=len(results),counts=dict(counts),clear_reference_n=n,tp=tp,tn=tn,fp=fp,fn=fn,abstentions_on_clear=abstain,positive_recall=tp/pos if pos else None,negative_specificity=tn/neg if neg else None,balanced_accuracy=(tp/pos+tn/neg)/2 if pos and neg else None,binary_agreement=(tp+tn)/n if n else None,four_level_agreement=exact/n if n else None,coverage=(n-abstain)/n if n else None,mean_seconds=statistics.mean(r['seconds'] for r in results) if results else None,output_limited=sum(r['hit_output_limit'] for r in results),invalid_intervals=sum(not r['interval_bounds_valid'] for r in results),uncertain_on_boundary=sum(r['human']=='UNCERTAIN' and r['prediction']=='UNCERTAIN' for r in records),confusion=[dict(human=h,predicted=p,n=v) for (h,p),v in sorted(conf.items())])
   summary.append(s)
  dump(out/'summary.json',summary)
  with (out/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
   writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['case']);writer.writeheader();writer.writerows(rows)
  # Group the three modalities together per case. Original reports are untouched.
  for case in ref:
   folder=out/case;folder.mkdir(parents=True,exist_ok=True)
   rel=os.path.relpath(DATA/case,folder)
   report=f'# {pid} — {case}\n\n![模型输入轨迹]({rel}/trajectory2.png)\n\n![人工审核 GIF]({rel}/trajectory.gif)\n\n人工参考：{ref[case]["human"]}；{ref[case]["comment"]}\n\n'
   for mode in MODES:
    report+=f'## {mode}\n\n[实际输入]({mode}/request.txt) · [原始输出]({mode}/response.txt)\n\n'
    p=folder/mode/'response.txt'
    report+=('```text\n'+p.read_text()+'\n```\n\n') if p.exists() else '待运行。\n\n'
   report+='## 人工复核\n\n- 判断是否合理：\n- 依据是否真实：\n- 区间与备注：\n'
   target=folder/'review.md'
   if target.exists() and '## 人工复核' in target.read_text():report=report.split('## 人工复核')[0]+target.read_text()[target.read_text().index('## 人工复核'):]
   target.write_text(report)
  index=f'# {pid}：{json.loads((ROOT/"prompts"/(pid+".json")).read_text())["name"]}\n\n[Prompt 定义](../prompts/{pid}.json) · [统计](summary.json) · [逐条对照](comparison.csv)\n\n'
  index+='\n'.join(f'- [{case}]({case}/review.md)' for case in ref)+'\n';(out/'index.md').write_text(index)
 allrows=[]
 for p in sorted(ROOT.glob('p[0-9][0-9]/summary.json')):allrows.extend(json.loads(p.read_text()))
 dump(ROOT/'leaderboard.json',allrows)
 with (ROOT/'leaderboard.csv').open('w',encoding='utf-8-sig',newline='') as f:
  cols=['prompt_id','mode','completed','balanced_accuracy','binary_agreement','four_level_agreement','tp','tn','fp','fn','abstentions_on_clear','coverage','positive_recall','negative_specificity','uncertain_on_boundary','mean_seconds','output_limited','invalid_intervals']
  writer=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');writer.writeheader();writer.writerows(allrows)
 for s in allrows:print({k:s[k] for k in ('prompt_id','mode','completed','tp','tn','fp','fn','abstentions_on_clear','balanced_accuracy')})

def analyze(ids):
 import fcntl
 with (ROOT/'.analysis.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  _analyze(ids)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=('freeze','run','analyze'));p.add_argument('ids',nargs='*');a=p.parse_args()
 if a.command=='freeze':freeze()
 elif a.command=='run':run(a.ids[0])
 else:analyze(a.ids)

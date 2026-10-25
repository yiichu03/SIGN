#!/usr/bin/env python3
"""Compact progress, stratified metrics and error review for prompt iteration."""
import argparse,json,re
from pathlib import Path
from collections import Counter
from qwen_prompt_search import ROOT,DATA


def main():
 p=argparse.ArgumentParser();p.add_argument('ids',nargs='*');p.add_argument('--errors',action='store_true');a=p.parse_args()
 ref={r['case']:r for r in json.loads((ROOT/'human_reference.json').read_text())}
 ids=a.ids or [p.stem for p in sorted((ROOT/'prompts').glob('p*.json'))]
 for pid in ids:
  report={};per_mode={}
  for mode in ('image_only','json_only','image_json'):
   rows=[]
   for f in sorted((ROOT/pid).glob('val_*/episode_*/'+mode+'/result.json')):
    d=json.loads(f.read_text());truth=ref[d['case']]['reference_label'];obj=d['parsed'];lab=obj['label'] if obj else 'INVALID'
    raw=(f.parent/'response.txt').read_text()
    match=re.search(r'(?:^|[\{,\n])\s*"?label"?\s*:\s*"(NONE|SOME|CLEAR|UNCERTAIN)"',raw)
    decision=lab if obj else (match.group(1) if match else 'INVALID')
    rows.append(dict(decision_label=decision,case=d['case'],human=truth,label=lab,seconds=d['seconds'],parsed=obj,stuck=ref[d['case']]['stuck_related'],steps=len(json.loads((DATA/d['case']/'waypoints_corrected.json').read_text())['waypoints'])))
   per_mode[mode]=rows
   def stats(rs):
    clear=[x for x in rs if x['human'] in ('NONE','SOME','CLEAR') and not x['stuck']]
    pos=[x for x in clear if x['human']!='NONE'];neg=[x for x in clear if x['human']=='NONE']
    tp=sum(x['label'] in ('SOME','CLEAR') for x in pos);tn=sum(x['label']=='NONE' for x in neg)
    fp=sum(x['label'] in ('SOME','CLEAR') for x in neg);fn=sum(x['label']=='NONE' for x in pos)
    return dict(n=len(rs),labels=dict(Counter(x['label'] for x in rs)),tp=tp,tn=tn,fp=fp,fn=fn,abstain=sum(x['label'] in ('UNCERTAIN','INVALID') for x in clear),BA=round((tp/len(pos)+tn/len(neg))/2,4) if pos and neg else None)
   report[mode]=dict(all=stats(rows),decision_only=stats([dict(x,label=x['decision_label']) for x in rows]),invalid_responses=sum(x['parsed'] is None for x in rows),without_stuck=stats([x for x in rows if not x['stuck']]),by_difficulty={s:stats([x for x in rows if x['case'].startswith(s)]) for s in ('val_easy','val_medium','val_hard')},by_length={k:stats([x for x in rows if (x['steps']<=100 if k=='le100' else x['steps']>100)]) for k in ('le100','gt100')})
   print(pid,mode,report[mode]['all'],'decision_only_BA',report[mode]['decision_only']['BA'])
   if a.errors:
    for x in rows:
     if x['human'] in ('NONE','SOME','CLEAR') and ((x['human']=='NONE')!=(x['label']=='NONE') or x['label'] in ('UNCERTAIN','INVALID')):
      print(' ',x['case'],x['human'],'->',x['label'],json.dumps(x['parsed'],ensure_ascii=False))
  if (ROOT/pid).exists():(ROOT/pid/'diagnostics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()

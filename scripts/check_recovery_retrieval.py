#!/usr/bin/env python3
"""Fixed-threshold appearance QA; GT is read only by this offline report."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.recovery_memory import VisualMatcher


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists()
    events=[json.loads(l) for l in (a.source/'native/recovery/events.jsonl').read_text().splitlines()]
    matcher=VisualMatcher();gallery=[];rows=[]
    # No outcomes are used to select cases or thresholds; all available actual scan RGBs.
    for e in events:
        key=e['episode'];name=Path(key[0]).stem+'_'+key[1]+'.npz'
        with np.load(a.source/'audit_traces'/name,allow_pickle=False) as trace:poses=trace['poses'].copy()
        for side in ['left','forward','right']:
            step=e['view_steps'][side];view=matcher.view(np.asarray(Image.open(e['view_files'][side]['path']).convert('RGB')))
            for old in gallery:
                if old['episode']!=key or step-old['step']<16:continue
                result=matcher.match(view,old['view'])
                pa,pb=poses[step],poses[old['step']]
                distance=float(np.linalg.norm(pa[:3]-pb[:3]))
                cosine=float(np.clip(abs(np.dot(pa[3:],pb[3:])),0,1));angle=float(np.rad2deg(2*np.arccos(cosine)))
                label='positive' if distance<=.25 and angle<=15 else 'negative' if distance>.75 or angle>=45 else 'unknown'
                rows.append(dict(episode=key,query_event=e['id'],query_side=side,query_step=step,
                    stored_event=old['event'],stored_side=old['side'],stored_step=old['step'],match=result,
                    offline_only_position_distance_m=distance,offline_only_angle_deg=angle,offline_only_label=label))
            gallery.append(dict(episode=key,step=step,event=e['id'],side=side,view=view))
    tp=sum(r['match']['valid'] and r['offline_only_label']=='positive' for r in rows)
    fp=sum(r['match']['valid'] and r['offline_only_label']=='negative' for r in rows)
    fn=sum(not r['match']['valid'] and r['offline_only_label']=='positive' for r in rows)
    summary=dict(events=len(events),pairs=len(rows),true_positive=tp,false_positive=fp,false_negative=fn,
        precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
        accepted_unknown=sum(r['match']['valid'] and r['offline_only_label']=='unknown' for r in rows),
        no_threshold_tuning=True,scope='Saved scan RGBs from existing full run; not representative normal-navigation keyframes, not a human location truth.',
        limitation='Insufficient positives or zero accepted matches does not validate reliable memory recall. New runtime uses no GT.',rows=rows)
    a.output.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='rows'},indent=2))

if __name__=='__main__':main()

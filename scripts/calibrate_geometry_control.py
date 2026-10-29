"""Freeze geometry128's scale from the already completed, valid Qwen128 short run."""
import argparse,csv,hashlib,json,math
from pathlib import Path

def calibrate(source):
    raw=source.read_bytes();rows=[json.loads(line) for line in raw.splitlines()]
    ids=[s['segment_id'] for s in rows]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate calibration segments')
    selected=[s for s in rows if s['valid_geometry']]
    if not selected:raise ValueError('No valid calibration segments')
    for s in selected:
        q=s['result'];area=s['metadata']['new_area_m2'];L=s['action_count']
        if (not q['valid'] or type(L) is not int or L<=0 or not math.isfinite(q['q']) or not 0<=q['q']<=1
                or not math.isfinite(area) or area<0 or L!=s['end']-s['start']
                or abs(q['q']-.5*q['p_medium']-q['p_high'])>1e-12):raise ValueError('Invalid calibration row')
    total_Lq=sum(s['action_count']*s['result']['q'] for s in selected)
    total_area=sum(s['metadata']['new_area_m2'] for s in selected)
    if total_area<=0:raise ValueError('Zero total calibration area')
    alpha=.03*total_Lq/total_area
    return dict(beta=.03,rollout_steps=256,source_sha256=hashlib.sha256(raw).hexdigest(),source=str(source),
        total_segments=len(rows),valid_segments=len(selected),sum_length_times_q=total_Lq,sum_new_area_m2=total_area,
        alpha=alpha,qwen_bonus_sum=.03*total_Lq/256,geometry_bonus_sum=alpha*total_area/256,
        rule='Valid segments only from completed40960-step Qwen128 short run. Frozen before new experiments; no fitting on new training or validation data.'),selected

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result,rows=calibrate(a.source);a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'calibration.json').write_text(json.dumps(result,indent=2)+'\n')
    with (a.output/'segments.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['id','actions','q','new_area_m2','length_times_q'])
        for s in rows:w.writerow([s['segment_id'],s['action_count'],s['result']['q'],s['metadata']['new_area_m2'],s['action_count']*s['result']['q']])
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()

"""Read the immutable original training tails; never reads continuation runs."""
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from tensorboard.backend.event_processing.event_file_loader import RawEventFileLoader
from tensorboard.compat.proto import event_pb2

ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent
PREVIOUS=ROOT/'logs/training_readout_20261031/snapshot_005043'
previous=json.loads((PREVIOUS/'readout.json').read_text())
checkpoints=json.loads((ROOT/'logs/training_continuation_20261103/checkpoint_audit.json').read_text())
jobs=json.loads((ROOT/'logs/training_continuation_20261103/previous_jobs.json').read_text())
TZ=timezone(timedelta(hours=8));now=datetime.now(TZ)
OUT=HERE/now.strftime('readout_%Y%m%dT%H%M%S');OUT.mkdir()
NAMES={'coverage256':'coverage256','coverage32':'coverage32','qwen128_beta01':'qwen01',
       'A_qwen128_beta003':'A','B_qwen256_beta003':'B','C_geometry128':'C'}
KEYS=['metrics/success','metrics/spl','reward','metrics/collisions.count','learner/value_loss','learner/action_loss']
report=dict(recorded_at=now.isoformat(timespec='seconds'),event_date='2026-10-31',runs={},
    semantics='Original pre-interruption training only. Latest values are native overlapping50-update episode-window metrics. Last1M averages are means of those correlated window points, not full-train-set or validation evaluations. Checkpoint steps are separate from final event steps.')

def complete_end(raw):
    offset=0
    while offset+12<=len(raw):
        length=struct.unpack_from('<Q',raw,offset)[0]
        if offset+16+length>len(raw):break
        assert length<10000000
        offset+=16+length
    return offset

for name,checkpoint_key in NAMES.items():
    records=[r for r in previous['snapshots'] if r['source'].startswith(previous['runs'][name]['directory']+'/tb/')]
    streams={};inputs=[]
    for record in records:
        source=Path(record['source']);size=source.stat().st_size
        with source.open('rb') as f:
            prefix=f.read(record['bytes']);assert hashlib.sha256(prefix).hexdigest()==record['sha256']
            offset=complete_end(prefix);f.seek(offset);tail=f.read()
        end=complete_end(tail)
        target=OUT/(name+'.tfevents_tail');target.write_bytes(tail[:end])
        inputs.append(dict(source=str(source),source_size=size,verified_prefix_bytes=record['bytes'],
            verified_prefix_sha256=record['sha256'],tail_offset=offset,tail_bytes=end,
            tail_sha256=hashlib.sha256(tail[:end]).hexdigest(),ignored_incomplete_final_bytes=len(tail)-end))
        for raw in RawEventFileLoader(str(target)).Load():
            event=event_pb2.Event.FromString(raw)
            for value in event.summary.value:
                if not value.HasField('simple_value'):raise RuntimeError('Unexpected non-scalar encoding')
                streams.setdefault(value.tag,[]).append((int(event.step),float(event.wall_time),float(value.simple_value)))
    streams={k:np.asarray(v,dtype=np.float64) for k,v in streams.items()}
    nonfinite={k:int((~np.isfinite(v[:,2])).sum()) for k,v in streams.items() if not np.isfinite(v[:,2]).all()}
    final_step=int(streams['metrics/success'][-1,0]);event_time=float(streams['metrics/success'][-1,1])
    assert int(streams['metrics/spl'][-1,0])==final_step
    # The verified old prefix ends earlier than the full final1M interval.
    assert previous['runs'][name]['latest_step']<final_step-1000000
    last1m={};previous_half={};last_half={}
    for tag,values in streams.items():
        for target,lo,hi in [(last1m,final_step-1000000,final_step),
                             (previous_half,final_step-1000000,final_step-500000),
                             (last_half,final_step-500000,final_step)]:
            selected=values[(values[:,0]>lo)&(values[:,0]<=hi)]
            if len(selected):target[tag]=dict(mean=float(selected[:,2].mean()),points=len(selected))
    checkpoint=checkpoints[checkpoint_key];job=previous['runs'][name]['job_id']+'.stdct-mgmt-02'
    x=dict(job_id=job,interrupted_at=jobs[job]['obittime'],exit_status=jobs[job]['Exit_status'],
        final_event_step=final_step,last_event_at=datetime.fromtimestamp(event_time,TZ).isoformat(timespec='seconds'),
        checkpoint_step=checkpoint['extra_state']['step'],uncheckpointed_steps=final_step-checkpoint['extra_state']['step'],
        latest={tag:dict(step=int(a[-1,0]),value=float(a[-1,2])) for tag,a in streams.items()},
        last1m=last1m,last1m_first_half=previous_half,last1m_second_half=last_half,
        nonfinite_in_final_tail=nonfinite,earlier_history_finite_in_verified_previous_snapshot=previous['runs'][name]['all_scalars_finite'],inputs=inputs)
    if name.startswith('coverage'):
        area=last1m['learner/coverage_new_area_m2']['mean'];x['last1m_area_per_all_actions']=area/2048
    else:
        prefix='geometry' if name.startswith('C_') else 'qwen'
        x['last1m_area_per_valid_action']=last1m['learner/'+prefix+'_new_area_m2']['mean']/last1m['learner/'+prefix+'_valid_actions']['mean']
        x['last1m_valid_segment_fraction']=last1m['learner/'+prefix+'_valid_segments']['mean']/last1m['learner/'+prefix+'_segments']['mean']
    with (OUT/(name+'_selected.csv')).open('w') as f:
        writer=csv.writer(f);writer.writerow(['tag','step','wall_time','value'])
        for tag,a in streams.items():
            if tag in KEYS or any(k in tag for k in ['bonus_sum','new_area_m2','valid_fraction','q_mean']):
                for step,wall,value in a:writer.writerow([tag,int(step),wall,value])
    report['runs'][name]=x
    print(name,final_step,'latestSR/SPL',streams['metrics/success'][-1,2],streams['metrics/spl'][-1,2],
          'last1M',last1m['metrics/success']['mean'],last1m['metrics/spl']['mean'],flush=True)
(OUT/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print('OUTPUT',OUT,flush=True)

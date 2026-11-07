"""Matched original-training budgets, reconstructed from verified fixed CSVs."""
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent
PREFIX=ROOT/'logs/training_readout_20261031/snapshot_005043'
TAIL=ROOT/'logs/training_stop_20261031/readout_20261103T014602'
prefix_report=json.loads((PREFIX/'readout.json').read_text())
tail_report=json.loads((TAIL/'report.json').read_text())
published=json.loads((ROOT/'SIGN-qwen-ablation-publication/docs/experiments/qwen128-reward/ablations/training_20261031/inputs.json').read_text())
published_shas={v['source']:v['source_sha256'] for v in published.values()}
now=datetime.now(timezone(timedelta(hours=8)))
OUT=HERE/now.strftime('snapshot_%H%M%S');OUT.mkdir()
NAMES=['baseline','coverage256','coverage32','qwen128_beta01','A_qwen128_beta003','B_qwen256_beta003','C_geometry128']
LABELS=['Frozen baseline','Coverage256','Coverage32','Qwen128 beta0.1','A: Qwen128 beta0.03','B: Qwen256 beta0.03','C: Geometry128']
TAGS=['metrics/success','metrics/spl','reward','metrics/collisions.count','learner/coverage_new_area_m2']
COLORS=['#111111','#e67e22','#7c8c16','#9467bd','#d62728','#1f77b4','#2ca02c']
streams={};inputs=[];ends={}
for name in NAMES:
    data={tag:{} for tag in TAGS}
    paths=[PREFIX/name/'selected_scalars.csv']
    if name!='baseline':paths.append(TAIL/(name+'_selected.csv'))
    for p in paths:
        raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        if str(p) in published_shas:assert digest==published_shas[str(p)]
        inputs.append(dict(path=str(p),sha256=digest,bytes=len(raw),verified_published_prefix=str(p) in published_shas))
        with p.open() as f:
            for row in csv.DictReader(f):
                tag=row['tag']
                if tag not in data:continue
                step=int(row['step']);value=float(row['value']);assert np.isfinite(value)
                if step in data[tag]:assert data[tag][step]==value
                data[tag][step]=value
    arrays={tag:np.asarray(sorted(rows.items()),dtype=np.float64) for tag,rows in data.items() if rows}
    ends[name]=int(arrays['metrics/success'][-1,0]);streams[name]=arrays
    expected=prefix_report['runs'][name]['latest_step'] if name=='baseline' else tail_report['runs'][name]['final_event_step']
    assert ends[name]==expected
    print(name,ends[name],flush=True)

groups={'legacy':['baseline','coverage256','coverage32'],'qwen_vs_coverage':NAMES}
report=dict(recorded_at=now.isoformat(timespec='seconds'),original_runs_only=True,
    semantics='Original50-update episode-window training logs; means at exactly matched environment-step rows. No continuation metrics, new simulations or validation. Correlated logging points are not independent samples.',
    source_ends=ends,inputs=inputs,groups={})
for label,names in groups.items():
    end=min(ends[n] for n in names)
    group=dict(common_end=end,names=names,windows={})
    for width in [1000000,5000000]:
        window=dict(lower_exclusive=end-width,upper_inclusive=end,runs={});expected_steps=None
        for name in names:
            metrics={}
            for tag,arr in streams[name].items():
                selected=arr[(arr[:,0]>end-width)&(arr[:,0]<=end)]
                if not len(selected):continue
                metrics[tag]=dict(mean=float(selected[:,1].mean()),points=len(selected))
                if tag in ['metrics/success','metrics/spl']:
                    if expected_steps is None:expected_steps=selected[:,0]
                    else:assert np.array_equal(selected[:,0],expected_steps),(name,tag)
            metrics['latest_at_common_end']={tag:float(a[a[:,0]==end,1][0]) for tag,a in streams[name].items()}
            if name in ['coverage256','coverage32']:
                metrics['new_m2_per_all_actions']=metrics['learner/coverage_new_area_m2']['mean']/2048
            window['runs'][name]=metrics
        group['windows'][str(width)]=window
    report['groups'][label]=group
    print(label,json.dumps(group,indent=2),flush=True)

with (OUT/'matched_means.csv').open('w') as f:
    writer=csv.writer(f);writer.writerow(['group','lower_exclusive','upper_inclusive','method','tag','mean','points'])
    for label,g in report['groups'].items():
        for w in g['windows'].values():
            for name,metrics in w['runs'].items():
                for tag,m in metrics.items():
                    if isinstance(m,dict) and 'mean' in m:writer.writerow([label,w['lower_exclusive'],w['upper_inclusive'],name,tag,m['mean'],m['points']])

fig,axes=plt.subplots(2,2,figsize=(15,9),constrained_layout=True)
for col,(label,names) in enumerate(groups.items()):
    end=report['groups'][label]['common_end']
    for row,tag in enumerate(['metrics/success','metrics/spl']):
        ax=axes[row,col]
        for name in names:
            a=streams[name][tag];a=a[a[:,0]<=end];smooth=101
            y=np.convolve(a[:,1],np.ones(smooth)/smooth,mode='valid')*100
            x=a[(smooth-1)//2:len(a)-(smooth-1)//2,0]/1e6
            stride=max(1,len(x)//3000);i=NAMES.index(name)
            ax.plot(x[::stride],y[::stride],label=LABELS[i],color=COLORS[i],linewidth=1.3)
        ax.axvspan((end-5000000)/1e6,end/1e6,color='gray',alpha=.10)
        ax.set_ylabel('Training SR (%)' if row==0 else 'Training SPL (%)');ax.grid(alpha=.2)
        if row==0:ax.set_title(f'{label}: common end {end/1e6:.3f}M');ax.legend(fontsize=7)
        if row==1:ax.set_xlabel('Environment steps (millions)')
fig.suptitle('Matched original-training budgets | one seed | 101-update display smoothing | shaded last5M')
fig.savefig(OUT/'matched_training.png',dpi=160);fig.savefig(OUT/'matched_training.pdf');plt.close(fig)
for item in inputs:assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
(OUT/'comparison.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print('OUTPUT',OUT,flush=True)

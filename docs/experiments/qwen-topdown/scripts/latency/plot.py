from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;d=json.loads((HERE/'comparison.json').read_text());names=list(d['models']);r=list(d['models'].values());x=np.arange(len(names));width=.35
fig,axes=plt.subplots(1,2,figsize=(12,4.8),constrained_layout=True)
a=axes[0]
for offset,key,label,color in [(-width/2,'serial8_seconds','Eight requests, serial','#d95f02'),(width/2,'eight_independent_batch_seconds','Eight independent requests, batch8','#2166ac')]:
 bars=a.bar(x+offset,[v[key] for v in r],width,label=label,color=color)
 
 for rect in bars:a.text(rect.get_x()+rect.get_width()/2,rect.get_height()+.04,'%.2f s'%rect.get_height(),ha='center',va='bottom',fontsize=9)
a.set_xticks(x);a.set_xticklabels([n.replace('Qwen3.5-','') for n in names]);a.set_ylabel('Seconds until all eight responses are returned');a.legend(fontsize=8);a.grid(axis='y',alpha=.2);a.set_title('Same A40, resident model, one image per request')
a=axes[1];labels=['baseline','coverage256','coverage32'];base=[d['training']['runs'][n]['seconds_per_update_mean'] for n in labels];xx=np.arange(3)
for offset,vals,label,color in [(-.25,base,'Current training','#777777'),(0,[v+d['models']['Qwen3.5-9B']['eight_independent_batch_seconds'] for v in base],'+ Qwen9B','#2166ac'),(.25,[v+d['models']['Qwen3.5-2B']['eight_independent_batch_seconds'] for v in base],'+ Qwen2B','#1b9e77')]:
 bars=a.bar(xx+offset,vals,.25,label=label,color=color);
 for rect in bars:a.text(rect.get_x()+rect.get_width()/2,rect.get_height()+.04,'%.2f'%rect.get_height(),ha='center',va='bottom',fontsize=8)
a.set_xticks(xx);a.set_xticklabels(labels);a.set_ylabel('Estimated seconds per PPO update (8 x 256)');a.set_title('Additive estimate; rendering / IPC / contention excluded');a.legend(fontsize=8);a.grid(axis='y',alpha=.2)
fig.suptitle('Single-image score latency benchmark | short fixed prompt | greedy output, thinking disabled')
fig.savefig(HERE/'latency_comparison.png',dpi=160);fig.savefig(HERE/'latency_comparison.pdf')

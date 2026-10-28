from pathlib import Path
import json,csv
HERE=Path(__file__).resolve().parent
plan=json.loads((HERE/'plan.json').read_text());training=json.loads((HERE/'training_timing.json').read_text())
rows=[];report={'kind':'Single-image independent scoring latency; not scoring accuracy','training':training,'models':{},'assumptions':['Resident model, one batch containing eight independent single-image requests.','Synchronous add-on estimate T_new=T_train+T_batch8; excludes live topdown rendering/IPC and unmeasured GPU contention.','Bench uses unoptimized reference kernels in existing environment; all model sizes share hardware and stack.','Median of three warm batch8 trials; serial8 and two batch4 measured once; generation length may vary.']}
for size in plan['models']:
 name='Qwen3.5-'+size;summary=json.loads((HERE/name/'summary.json').read_text());batch=summary['batch8_median_seconds']
 trials=[json.loads(p.read_text()) for p in (HERE/name).glob('*_batch8_*.json')]
 assert len(trials)==3 and all(r['batch_size']==8 for r in trials)
 record={'single_seconds':summary['single_median_seconds'],'eight_independent_batch_seconds':batch,'serial8_seconds':summary['serial8_seconds'],'two_batch4_seconds':summary['batch4_twice_seconds'],'model_load_seconds':summary['model_load_seconds'],'first_call_seconds':summary['first_call_seconds'],'load_plus_first_call_seconds':summary['load_plus_first_call_seconds'],'peak_gpu_gib':summary['peak_gpu_gib'],'valid_answers':summary['valid_answers'],'answers':summary['answers'],'batch8_preprocess_seconds':[t['preprocess_h2d_seconds'] for t in trials],'batch8_generate_seconds':[t['generation_seconds'] for t in trials],'output_tokens':summary['batch8_output_tokens'],'estimated_training':{n:{'original_seconds':v['seconds_per_update_mean'],'with_qwen_seconds':v['seconds_per_update_mean']+batch,'overhead_percent':batch/v['seconds_per_update_mean']*100} for n,v in training['runs'].items()},'hypothetical_200s_round_with_qwen_seconds':200+batch}
 report['models'][name]=record
 rows.append({'model':name,**{k:record[k] for k in ['single_seconds','eight_independent_batch_seconds','serial8_seconds','two_batch4_seconds','model_load_seconds','peak_gpu_gib','valid_answers','answers']}})
(HERE/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
with (HERE/'comparison.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
print(json.dumps(report,indent=2))

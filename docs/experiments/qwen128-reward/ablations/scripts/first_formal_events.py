"""Read early formal event files and verify fresh initialization and effective cases."""
import json,math,sys
from pathlib import Path
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;RUN=ROOT/'SIGN-qwen-ablation/results/qwen_ablation_20261029'
sub=json.loads((HERE/'formal_submission.json').read_text());report={}
for case in ['A','B','C']:
 out=RUN/case/'train';data=dict(job_id=sub['cases'][case]['training']['job_id'],submitted=True)
 if (out/'qwen/initial_parameter_hashes.json').exists():
  initial=json.loads((out/'qwen/initial_parameter_hashes.json').read_text())
  short=json.loads((RUN/case/'short_40960/qwen/initial_parameter_hashes.json').read_text())
  assert initial==short;data.update(fresh_initial_parameters_equal_to_short=True)
 if (out/'qwen/effective_config.yaml').exists():
  (HERE/case/'formal_effective_config.yaml').write_bytes((out/'qwen/effective_config.yaml').read_bytes())
 if (out/'tb').exists():
  ea=EventAccumulator(str(out/'tb'),size_guidance={'scalars':0});ea.Reload()
  values={tag:ea.Scalars(tag)[-1] for tag in ea.Tags()['scalars'] if ea.Scalars(tag)}
  if values:
   assert all(math.isfinite(e.value) for e in values.values())
   data.update(steps=max(e.step for e in values.values()),scalar_series=len(values),all_scalars_finite=True,last_values={k:v.value for k,v in values.items()})
 if case=='C':data['qwen_worker_absent']=not (out/'qwen/worker.log').exists()
 elif (out/'qwen/worker_boot.json').exists():
  boot=json.loads((out/'qwen/worker_boot.json').read_text());assert boot['environment']['dtype']=='torch.float32';data['worker_boot']=boot
 report[case]=data
(HERE/'first_formal_events.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:{x:y for x,y in v.items() if x not in ['last_values','worker_boot']} for k,v in report.items()},indent=2))

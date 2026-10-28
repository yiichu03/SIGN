from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import re,json,statistics
ROOT=Path('/scratch/e1538633/liuyi');OUT=Path(__file__).resolve().parent
paths={'baseline':ROOT/'logs/gibson_frozen_encoder_20261026/train_personal.pbs.log','coverage256':ROOT/'logs/gibson_rollout_coverage_20261027/train_personal.pbs.log','coverage32':ROOT/'logs/gibson_coverage_settle32_20261028/train_personal.pbs.log'}
results={}
for name,p in paths.items():
 text=p.read_text();rows=[]
 for stamp,update in re.findall(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+) update: (\d+)',text):rows.append((datetime.strptime(stamp,'%Y-%m-%d %H:%M:%S,%f').timestamp(),int(update)))
 rows=rows[-51:];rates=[(t1-t0)/(n1-n0) for (t0,n0),(t1,n1) in zip(rows,rows[1:]) if n1>n0]
 results[name]={'source':str(p),'latest_update':rows[-1][1],'last_intervals':len(rates),'updates_covered':rows[-1][1]-rows[0][1], 'seconds_per_update_mean':sum((b[0]-a[0]) for a,b in zip(rows,rows[1:]))/(rows[-1][1]-rows[0][1]),'seconds_per_update_median':statistics.median(rates),'seconds_per_logged_block_median':statistics.median([b[0]-a[0] for a,b in zip(rows,rows[1:])]),'logged_update_stride':rows[-1][1]-rows[-2][1],'rollout_envs':8,'rollout_steps_per_env':256,'environment_steps_per_update':2048,'latest_log_timestamp':datetime.fromtimestamp(rows[-1][0]).astimezone(ZoneInfo('Asia/Singapore')).isoformat()}
record={'recorded_at':datetime.now(ZoneInfo('Asia/Singapore')).isoformat(timespec='seconds'),'runs':results}
(OUT/'training_timing.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

"""Remove only the temporary user holds installed for this priority evaluation."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent
plan=json.loads((HERE/'priority_submission.json').read_text());records={}
for job in plan['held_training_jobs']:
    error=None
    for attempt in range(3):
        try:
            raw=subprocess.check_output(['qstat','-fx','-F','json',job],text=True,timeout=15)
            state=json.loads(raw)['Jobs'][job]
            if state['job_state']=='F':records[job]={'finished_already':True};break
            if 'u' in state.get('Hold_Types',''):
                subprocess.run(['qrls','-h','u',job],check=True,timeout=15)
            records[job]={'temporary_user_hold_released':True};break
        except Exception as exc:
            error=repr(exc)
            if attempt<2:time.sleep(5)
    if job not in records:records[job]={'error':error}
(HERE/'released_training_holds.json').write_text(json.dumps({
    'at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
    'jobs':records},indent=2)+'\n')
assert all('error' not in item for item in records.values()),records

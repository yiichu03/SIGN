"""Submit the bounded full diagnostic batch once the control comparison passes."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    receipt = HERE/'full_submission.json'
    assert not receipt.exists(), 'Existing submission receipt; do not duplicate jobs'
    submission = json.loads((HERE/'smoke_submission.json').read_text())
    smoke = submission.get('latest_job_id', submission['job_id'])
    state = json.loads(subprocess.check_output(['qstat','-fx','-F','json',smoke],text=True))['Jobs'][smoke]
    assert state['job_state'] == 'F' and state['Exit_status'] == 0
    assert json.loads((HERE/'smoke_passed.json').read_text())['passive_control_matches_diagnostic']
    from guard import guard
    guard()
    records = {'submitted_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
               'smoke_job':smoke,'project':'CFP04-SF-109','route':'auto',
               'resource_per_case':'1A40/12CPU64GB/4h','cases':{}}
    receipt.write_text(json.dumps(records,indent=2)+'\n')
    for case in ['baseline','coverage256','coverage32']:
        dependency = 'afterany:'+records['cases']['baseline']['job_id'] if case == 'coverage32' else 'afterok:'+smoke
        command = ['qsub','-N','sign-diag-'+{'baseline':'base','coverage256':'256','coverage32':'32'}[case],
                   '-q','auto','-P','CFP04-SF-109','-l','walltime=04:00:00',
                   '-l','select=1:ncpus=12:mem=64gb:ngpus=1:gpu_model=A40',
                   '-o',str(HERE/('full_'+case+'.pbs.log')),'-v','DIAG_CASE='+case,
                   '-W','depend='+dependency,str(HERE/'full.pbs')]
        result = subprocess.run(command,text=True,capture_output=True)
        records['cases'][case] = dict(command=command,returncode=result.returncode,
                                      stdout=result.stdout.strip(),stderr=result.stderr.strip())
        receipt.write_text(json.dumps(records,indent=2)+'\n')
        result.check_returncode()
        job = result.stdout.strip()
        assert re.fullmatch(r'\d+\.[A-Za-z0-9_.-]+',job)
        records['cases'][case]['job_id'] = job
        receipt.write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records,indent=2))


if __name__ == '__main__':
    main()

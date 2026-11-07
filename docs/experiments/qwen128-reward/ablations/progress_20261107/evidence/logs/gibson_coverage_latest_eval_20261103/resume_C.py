"""Resume C after both priority eval jobs terminate, using the approved rollback."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from guard import guard

HERE=Path(__file__).resolve().parent
guard()
m=json.loads((HERE/'C_resume_manifest.json').read_text())
status=json.loads(subprocess.check_output(['qstat','-fx','-F','json',m['paused_job']],text=True))['Jobs'][m['paused_job']]
assert status['job_state']=='F'
assert hashlib.sha256(Path(m['checkpoint']).read_bytes()).hexdigest()==m['checkpoint_sha256']
assert not Path(m['output']).exists(),'Existing C recovery output'
command=json.loads((HERE/'C_resume_command.json').read_text())['command']
assert command[0]==sys.executable
with (HERE/'C_resume.log').open('x') as log:
    subprocess.run(command,cwd=m['cwd'],stdout=log,stderr=subprocess.STDOUT,check=True)
guard()

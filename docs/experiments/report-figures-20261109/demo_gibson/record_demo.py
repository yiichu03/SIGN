"""One fresh Public SIGN rollout; recording callback cannot alter policy inputs."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
PAIR=HERE.parent/'coverage_comparison'
sys.path.insert(0,str(PAIR))
from record_pair import record, sha, write_json, pixel_sha
import numpy as np
import torch
import habitat_sim
from PIL import Image


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=HERE)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    assert os.environ.get('PYTHONHASHSEED')=='0' and torch.cuda.is_available()
    frames=[];frame_rows=[]
    def capture(step,rgb,row):
        assert step==len(frames) and rgb.shape==(128,128,3)
        frames.append(rgb)
        frame_rows.append({'step':step,'rgb_pixel_sha256':pixel_sha(rgb),
                           'stop_called':row['stop_called'],'episode_over':row['episode_over']})
    task=PAIR/'episodes/Cantwell_1703.json.gz'
    summary=record(task,'public',out/'recording',frame_callback=capture)
    assert len(frames)==summary['steps']+1
    np.savez_compressed(out/'rgb_all_steps.npz',rgb=np.stack(frames),step=np.arange(len(frames)))
    with (out/'rgb_manifest.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(frame_rows[0]),lineterminator='\n');w.writeheader();w.writerows(frame_rows)
    for label,step in [('start',0),('midpoint',summary['steps']//2),('terminal',summary['steps'])]:
        Image.fromarray(frames[step]).save(out/f'{label}.png')
    shutil.copyfile(out/'recording/goal.png',out/'goal.png')
    shutil.copyfile(out/'recording/steps.csv',out/'steps.csv')
    prior=json.loads((PAIR/'Cantwell_1703/public/summary.json').read_text())
    fields=['episode','start_pose','initial_rgb_pixel_sha256','goal_pixel_sha256','checkpoint_sha256','safety_sha256','seed','max_steps']
    assert all(summary[k]==prior[k] for k in fields)
    with (PAIR/'Cantwell_1703/public/steps.csv').open() as f:old=list(csv.DictReader(f))
    with (out/'steps.csv').open() as f:new=list(csv.DictReader(f))
    columns=['step','x','y','z','qx','qy','qz','qw','action_0','action_1','success','spl','stop_called']
    trajectory_equal=len(old)==len(new) and all(all(a[k]==b[k] for k in columns) for a,b in zip(old,new))
    lab=Path(sys.prefix).parent/'habitat-lab-sign'
    summary.update(environment={'python':platform.python_version(),'habitat_sim':habitat_sim.__version__,
                    'torch':torch.__version__,'torch_cuda':torch.version.cuda,
                    'gpu':torch.cuda.get_device_name(0),
                    'habitat_lab_commit':subprocess.check_output(['git','-C',str(lab),'rev-parse','HEAD'],text=True).strip()},
                   source_parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                   source_files_sha256={'record_pair.py':sha(PAIR/'record_pair.py'),'record_demo.py':sha(__file__)},
                   actual_rgb_observations=len(frames),terminal_captured_before_reset=True,
                   intermediate_png_step=summary['steps']//2,
                   prior_pair_comparison={'matched_input_fields':fields,'recorded_pose_action_rows_identical':trajectory_equal,
                                          'prior_steps':prior['steps'],'prior_success':prior['success'],'prior_spl':prior['spl']},
                   rgb_archive_sha256=sha(out/'rgb_all_steps.npz'))
    write_json(out/'summary.json',summary)
    print('RECORDED',summary['steps'],summary['success'],summary['spl'],'prior_trajectory_equal',trajectory_equal,flush=True)

if __name__=='__main__':main()

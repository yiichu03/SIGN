"""Check identical native action trajectories before allowing a full replay."""
import json
from pathlib import Path
import hashlib
import subprocess
import numpy as np

HERE = Path(__file__).resolve().parent


def records(folder):
    rows = [json.loads(line) for p in folder.glob('*.jsonl') for line in p.read_text().splitlines()]
    result = {(r['scene_id'],r['episode_id']):r for r in rows}
    assert len(result) == len(rows)
    return result


def main():
    base = HERE/'smoke/baseline'
    a = records(base/'control/episodes')
    b = records(base/'diagnostic/episodes')
    assert set(a) == set(b) and len(a) >= 28
    keys = ['steps','success','spl','view_match','navigation_reward','collisions',
            'goal_sha256','start_position','pose_trace_sha256','new_area_m2']
    for key in a:
        assert all(a[key][field] == b[key][field] for field in keys), key
    diag = records(base/'diagnostic/diagnostics')
    assert set(diag) == set(a)
    video_frames = 0
    for row in diag.values():
        folder = base/'diagnostic'
        with np.load(folder/row['trace'], allow_pickle=False) as data:
            assert len(data['metrics']) == row['steps']+1
            pose = np.c_[data['position_xyz'][1:],data['rotation_xyzw'][1:]].astype(np.float32)
            assert hashlib.sha256(pose.tobytes()).hexdigest() == row['pose_trace_sha256']
        assert row['captured_images'] and row['video']
        ffprobe = '/scratch/e1538633/liuyi/envs/sign-baseline/bin/ffprobe'
        count = int(subprocess.check_output([ffprobe,'-v','error','-count_frames',
            '-select_streams','v:0','-show_entries','stream=nb_read_frames',
            '-of','default=nw=1:nk=1',str(folder/row['video'])],text=True).strip())
        assert count == row['steps']+1
        video_frames += count
    result = dict(passive_control_matches_diagnostic=True, episodes=len(a),
                  exact_fields=keys, old_reference_pose_matches=sum(r['reference_pose_hash_equal'] for r in diag.values()),
                  trace_pose_hashes_verified=True, full_video_frames_verified=video_frames)
    (HERE/'smoke_passed.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

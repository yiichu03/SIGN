"""Check paired identity and numerical consistency of the recorded artifacts."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
checks=[]
for case in sorted(HERE.glob('*_*')):
    if not (case/'pair_verification.json').exists():continue
    pair=json.loads((case/'pair_verification.json').read_text());assert pair['passed']
    for method in ['public','coverage']:
        d=case/method;s=json.loads((d/'summary.json').read_text())
        with (d/'steps.csv').open() as f:rows=list(csv.DictReader(f))
        assert len(rows)==s['steps']+1
        assert [int(r['step']) for r in rows]==list(range(len(rows)))
        xyz=np.array([[float(r[k]) for k in ['x','y','z']] for r in rows])
        length=np.linalg.norm(np.diff(xyz,axis=0),axis=1).sum()
        assert np.isclose(length,s['path_length_m'],rtol=1e-6)
        delta=np.array([float(r['delta_new_area_m2']) for r in rows]);assert (delta>=0).all()
        assert np.allclose(delta.cumsum(),[float(r['cumulative_new_area_m2']) for r in rows])
        m=np.load(d/'map.npz')
        assert np.isclose((np.count_nonzero(m['seen'])-np.count_nonzero(m['initial_seen']))*.01,s['new_area_m2'])
        shortest=s['episode']['info']['geodesic_distance']
        assert np.isclose(s['spl'],s['success']*shortest/max(shortest,length),rtol=2e-5)
        assert (d/f"rgb_{s['steps']:03d}.png").exists()
        assert hashlib.sha256(np.asarray(Image.open(d/'goal.png')).tobytes()).hexdigest()==s['goal_pixel_sha256']
        checks.append(dict(case=case.name,method=method,steps=s['steps'],success=s['success'],spl=s['spl'],
                           path_length_m=s['path_length_m'],new_area_m2=s['new_area_m2']))
    assert np.array_equal(np.asarray(Image.open(case/'public/goal.png')),np.asarray(Image.open(case/'coverage/goal.png')))
    assert np.array_equal(np.asarray(Image.open(case/'public/rgb_000.png')),np.asarray(Image.open(case/'coverage/rgb_000.png')))
(HERE/'validation.json').write_text(json.dumps({'passed':True,'checks':'paired source/start/goal identity, step sequence, 3D path length, cumulative coverage, mask area, SPL, terminal frame','results':checks},indent=2)+'\n')
print(json.dumps(checks,indent=2))

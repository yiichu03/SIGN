"""Offline visualization only. Original training-grid masks remain untouched."""
import json
from pathlib import Path
import numpy as np
import habitat_sim
from habitat.utils.visualizations import maps,fog_of_war
from scipy.ndimage import distance_transform_edt
root=Path('/scratch/e1538633/liuyi');out=Path(__file__).resolve().parent;records=[]
for group in sorted(out.glob('group_*')):
 for path in sorted(group.glob('C*/trajectory.json')):
  t=json.loads(path.read_text());pf=habitat_sim.PathFinder();assert pf.load_nav_mesh(str(root/'SIGN'/t['scene_id'].replace('.glb','.navmesh')))
  mpp=.025;grid=maps.get_topdown_map(pf,t['poses'][0]['position_xyz'][1],draw_border=False,meters_per_pixel=mpp)
  valid=grid==1;dist,nearest=distance_transform_edt(~valid,return_indices=True);seen=np.zeros_like(grid);coords=[];corrections=[]
  assert t['grid_changed_steps']==0
  for i,p in enumerate(t['poses']):
   xyz=p['position_xyz'];rc=maps.to_grid(xyz[2],xyz[0],grid.shape,pathfinder=pf);coords.append(list(rc));dd=float(dist[rc]);assert dd<=2.01,(path,i,dd)
   corrected=np.array([nearest[0][rc],nearest[1][rc]],dtype=np.int64)
   if dd:corrections.append({'step':i,'distance_px':dd,'raw_rc':list(rc),'fog_origin_rc':corrected.tolist()})
   seen=fog_of_war.reveal_fog_of_war(grid,seen,corrected,p['heading_rad'],fov=90,max_line_len=3/mpp)
   if i==0:initial=seen.copy()
  np.savez_compressed(path.parent/'display_map_data.npz',grid=grid,valid_union=valid,initial_seen=initial,seen=seen,coords=np.asarray(coords),mpp=mpp)
  records.append({'group':group.name,'case':path.parent.name,'corrected_steps':len(corrections),'max_adjustment_m':max([c['distance_px']*mpp for c in corrections]+[0]),'corrections':corrections,'initial_area_m2':float(initial.sum()*mpp*mpp)})
(out/'display_reconstruction.json').write_text(json.dumps({'method':'2.5cm fixed-floor raster; fog origins only snapped to nearest valid pixel within 2 pixels (5cm); drawn path retains raw mapped positions; independent visualization, not training reward','records':records},indent=2))

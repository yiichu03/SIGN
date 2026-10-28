from pathlib import Path
import csv,json,math,hashlib
import numpy as np
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;SOURCE=HERE
lookup={(r['group'],r['candidate']):r for r in csv.DictReader((SOURCE/'coverage.csv').open())}
spec={'coverage_definition':'Newly seen navigable XZ grid cells excluding initial view; saved 0.025m display reconstruction, 3m range/90deg FOV, fog-origin boundary correction <=5cm; not RGB surface area or native training 0.1m statistic','groups':[]}
for group_id in ['group_01','group_02']:
 group={'id':group_id,'items':[]}
 for index in range(1,9):
  case='C%02d'%index;folder=SOURCE/group_id/case
  trajectory=json.loads((folder/'trajectory.json').read_text());maps=np.load(folder/'display_map_data.npz')
  valid=maps['valid_union'].astype(bool);initial=maps['initial_seen'].astype(bool);seen=maps['seen'].astype(bool);mpp=float(maps['mpp'])
  cells=int(np.count_nonzero(valid&seen&~initial));area=cells*mpp*mpp
  actions=len(trajectory['poses'])-1
  assert actions==trajectory['window_steps']==int(lookup[(group_id,case)]['steps'])
  assert math.isclose(area,float(lookup[(group_id,case)]['new_m2']),abs_tol=1e-9)
  image=folder/'topdown_static.png';assert image.is_file()
  group['items'].append({'id':case,'image':str(image),'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
    'scene':Path(trajectory['scene_id']).stem,'episode_id':trajectory['episode_id'],'action_count':actions,'new_area_m2':area,'new_area_m2_per_action':area/actions,
    'area_source':{'mask':str(folder/'display_map_data.npz'),'mask_sha256':hashlib.sha256((folder/'display_map_data.npz').read_bytes()).hexdigest(),'new_valid_cells':cells,'meters_per_pixel':mpp,'trajectory':str(folder/'trajectory.json'),'trajectory_sha256':hashlib.sha256((folder/'trajectory.json').read_bytes()).hexdigest()}})
 spec['groups'].append(group)
(HERE/'manifest.json').write_text(json.dumps(spec,indent=2)+'\n');print('16 images: action counts and mask-based m2 verified against trajectory and CSV')

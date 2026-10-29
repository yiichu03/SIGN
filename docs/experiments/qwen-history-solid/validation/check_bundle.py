from pathlib import Path
import csv,gzip,hashlib,json,math,re,zipfile
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
archive=HERE/'qwen2b_history_review.zip';out=HERE/'unpacked_final';out.mkdir(exist_ok=False)
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for name in z.namelist():assert not Path(name).is_absolute() and '..' not in Path(name).parts
 z.extractall(out)
manifest=json.loads((out/'bundle_manifest.json').read_text())
for name,record in manifest['files'].items():
 p=out/name;assert p.stat().st_size==record['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256'],name
spec=json.loads((out/'windows.json').read_text());results=json.loads((out/'scores/results.json').read_text());lookup={(r['segment_id'],r['variant']):r for r in results};geometry=[];yellow=[]
for s in spec['segments']:
 t=json.loads(gzip.decompress((out/'sources'/s['trajectory_id']/'trajectory.json.gz').read_bytes()))
 assert s['action_count']==s['end']-s['start'] and s['history_action_count']==s['start']
 assert sum(bool(p.get('collision',False)) for p in t['poses'][s['start']+1:s['end']+1])==s['collision_actions']
 with np.load(out/s['masks']) as m:
  grid,coords,valid=m['grid'],m['coords'],m['valid'].astype(bool)
  for kind,prior,final in [('history',m['prior_seen'],m['final_seen']),('legacy',m['legacy_initial_seen'],m['legacy_seen'])]:
   stats=s[kind+'_stats'];new=int(np.count_nonzero(final.astype(bool)&~prior.astype(bool)&valid));before=int(np.count_nonzero(prior.astype(bool)&valid));total=int(np.count_nonzero(final.astype(bool)&valid))
   assert new+before==total
   assert math.isclose(stats['new_area_m2'],new*.025**2,abs_tol=1e-10)
   assert math.isclose(stats['total_covered_area_m2'],total*.025**2,abs_tol=1e-10)
 # Original Matplotlib fixed view transform; verify both current markers on all variants.
 W,H=1400,1120;left,right,bottom,top=.125*W,.9*W,.12*H,.88*H
 x0,x1,y1,y0=s['bounds'];scale=min((right-left)/(x1-x0),(top-bottom)/(y1-y0))
 axw,axh=(x1-x0)*scale,(y1-y0)*scale;axleft=left+((right-left)-axw)/2;axbottom=bottom+((top-bottom)-axh)/2
 def pixel(rc):return np.array([axleft+(rc[1]-x0)*scale,H-(axbottom+(y1-rc[0])*scale)])
 def marker_distance(a,color,target):
  mask=np.all(a==np.array(color),axis=2);yy,xx=np.where(mask);inside=(xx>=axleft)&(xx<=axleft+axw)&(yy>=H-(axbottom+axh))&(yy<=H-axbottom)
  assert inside.any(),(s['id'],color)
  return float(np.min(np.linalg.norm(np.stack([xx[inside],yy[inside]],axis=1)-target,axis=1)))
 for variant in ['legacy','history']+(['history_no_yellow'] if s['start'] else []):
  r=lookup[(s['id'],variant)];a=np.asarray(Image.open(out/r['image']).convert('RGB'));assert a.shape==(H,W,3)
  dstart=marker_distance(a,[20,146,83],pixel(coords[s['start']]))
  dend=marker_distance(a,[34,44,65],pixel(coords[s['end']]))
  assert dstart<9 and dend<9,(r['id'],dstart,dend)
  geometry.append(dict(id=r['id'],current_start_marker_error_px=dstart,end_marker_error_px=dend,canvas=[W,H],scale_px_per_cell=scale))
 if s['start']:
  full,hidden=lookup[(s['id'],'history')],lookup[(s['id'],'history_no_yellow')]
  assert full['metadata']==hidden['metadata'] and full['prompt_version']==hidden['prompt_version']
  a=np.asarray(Image.open(out/full['image']).convert('RGB'));b=np.asarray(Image.open(out/hidden['image']).convert('RGB'));yy,xx=np.where(np.any(a!=b,axis=2))
  assert not len(xx) or (xx.min()>=math.floor(axleft)-2 and xx.max()<=math.ceil(axleft+axw)+2)
  assert not len(xx) or (yy.min()>=math.floor(H-(axbottom+axh))-2 and yy.max()<=math.ceil(H-axbottom)+2)
  yellow.append(dict(segment_id=s['id'],only_map_pixels_changed=True,changed_pixels=len(xx)))
with (out/'human_review.csv').open() as f:
 rows=list(csv.DictReader(f));assert len(rows)==44
 for r in rows:
  for k,v in r.items():
   if k.startswith('human_') or k in ['reviewer','reviewed_at','notes']:assert v=='',(k,v)
page=(out/'index.html').read_text()
for target in re.findall(r'(?:src|href)="([^"]+)"',page):assert not re.match('https?://',target) and (out/target).exists(),target
assert len(geometry)==100 and len(yellow)==12
report=dict(passed=True,zip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),zip_bytes=archive.stat().st_size,manifest_files=len(manifest['files']),images=100,unique_segments=44,human_labels_all_blank=True,all_html_local_links_exist=True,coverage_stats_recomputed=True,geometry=geometry,yellow_only_pixel_checks=yellow)
(HERE/'bundle_check.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',len(geometry),'images; markers/current window; total/prior/new areas; yellow-only maps; all blank human labels')

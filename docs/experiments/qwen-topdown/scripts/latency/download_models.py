import os,json,time,hashlib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
os.environ['HF_HUB_DISABLE_XET']='1'
from huggingface_hub import HfApi,snapshot_download
ROOT=Path('/scratch/e1538633/liuyi');OUT=Path(__file__).resolve().parent

def download(size):
 repo='Qwen/Qwen3.5-'+size;folder=ROOT/'models'/('Qwen3.5-'+size);api=HfApi()
 info=api.model_info(repo,files_metadata=True);revision=info.sha;start=time.time()
 selected=[f for f in info.siblings if f.rfilename.endswith(('.json','.safetensors','.jinja','.txt')) and '/' not in f.rfilename]
 assert selected
 path=snapshot_download(repo,revision=revision,local_dir=folder,allow_patterns=[f.rfilename for f in selected],max_workers=4)
 files={}
 for f in selected:
  p=folder/f.rfilename;assert p.is_file()
  h=hashlib.sha256()
  with p.open('rb') as fd:
   for chunk in iter(lambda:fd.read(8*1024*1024),b''):h.update(chunk)
  sha=h.hexdigest();lfs=getattr(f,'lfs',None)
  expected=getattr(lfs,'sha256',None) if lfs else None
  if expected:assert sha==expected,(repo,f.rfilename)
  files[f.rfilename]={'bytes':p.stat().st_size,'sha256':sha,'official_lfs_sha256':expected}
 record={'repo':repo,'revision':revision,'directory':str(path),'seconds':time.time()-start,'files':files,'recorded_at':datetime.now(ZoneInfo('Asia/Singapore')).isoformat(timespec='seconds')}
 (OUT/('download_'+size+'.json')).write_text(json.dumps(record,indent=2)+'\n');print('VERIFIED',repo,revision,sum(f['bytes'] for f in files.values()),flush=True)
with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(download,['4B','2B','0.8B']))

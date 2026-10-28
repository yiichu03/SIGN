#!/usr/bin/env python3
"""Score two groups of independent images from real next-token A/B/C logits."""
import argparse,csv,hashlib,json,sys,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from qwen_single_image import SingleImageJudge,load_manifest

def dump(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True);p.add_argument('--prompt',required=True);p.add_argument('--out',required=True)
    p.add_argument('--model-dir',default=str(Path(__file__).resolve().parents[2]/'models/Qwen3.5-9B'))
    p.add_argument('--batch-size',type=int,choices=range(1,9),default=8)
    p.add_argument('--dtype',choices=['float32','bfloat16','auto'],default='float32',
                   help='FP32 default stabilizes probability readout across batch shapes; old generation default is unchanged')
    p.add_argument('--verify',action='store_true',help='Compare padded batch/singles and first-generation raw logits')
    a=p.parse_args();spec,rows=load_manifest(a.manifest);prompt_path=Path(a.prompt);prompt=prompt_path.read_text()
    if not prompt.strip():raise ValueError('Empty prompt')
    version=hashlib.sha256(prompt.encode()).hexdigest();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
    dump(out/'manifest.json',spec);shutil.copyfile(prompt_path,out/'prompt.txt')
    (out/'images').mkdir()
    for index,row in enumerate(rows):
        sha=hashlib.sha256(Path(row['image']).read_bytes()).hexdigest()
        if row.get('image_sha256',sha)!=sha:raise ValueError('Image hash mismatch: '+row['image'])
        image=out/'images'/('%02d.png'%index);shutil.copyfile(row['image'],image)
        if hashlib.sha256(image.read_bytes()).hexdigest()!=sha:raise ValueError('Changed image during copy')
        row.update(image_sha256=sha,source_image=row['image'],image=str(image))
    run={'status':'loading','prompt_version':version,'prompt_source':str(prompt_path.resolve()),
         'manifest_source':str(Path(a.manifest).resolve()),'manifest_sha256':hashlib.sha256(Path(a.manifest).read_bytes()).hexdigest(),
         'model_config_sha256':hashlib.sha256((Path(a.model_dir)/'config.json').read_bytes()).hexdigest(),
         'code_sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in
             [Path(__file__).resolve(),Path(__file__).resolve().parents[1]/'src/qwen_single_image.py']},
         'method':'softmax([logit_A,logit_B,logit_C]), temperature=1; q=0.5*p_medium+p_high',
         'mapping':{'A':'LOW','B':'MEDIUM','C':'HIGH'},'rows':rows,'batch_size':a.batch_size,
         'seed':100,'max_image_pixels':262144,'enable_thinking':False}
    dump(out/'run.json',run)
    try:
        judge=SingleImageJudge(a.model_dir,prompt,dtype=a.dtype);run.update(judge.environment)
        if a.verify:
            probe=[rows[0],rows[10],rows[-1]]
            verification=judge.verify_readout([r['image'] for r in probe],probe)
            if not any(verification['padding_counts']):raise RuntimeError('Probe did not exercise padding')
            dump(out/'verification.json',verification)
            if not verification['passed']:raise RuntimeError('GPU probability checks failed; inspect verification.json')
        scored=[]
        for start in range(0,len(rows),a.batch_size):
            batch=rows[start:start+a.batch_size]
            results,audit=judge.class_probabilities([r['image'] for r in batch],batch)
            dump(out/('batch_%02d.json'%(start//a.batch_size)),{'items':batch,'results':results,'audit':audit})
            for row,result in zip(batch,results):
                scored.append({**row,**result,'prompt_version':version})
        dump(out/'scores.json',{'prompt_version':version,'method':run['method'],'results':scored})
        fields=['group_id','id','action_count','new_area_m2','new_area_m2_per_action',
                'p_low','p_medium','p_high','q','candidate_mass','valid','error','prompt_version']
        with (out/'scores.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(scored)
        run.update(status='complete',valid=sum(r['valid'] for r in scored),total=len(scored))
    except Exception as exc:
        run.update(status='failed',error=repr(exc));raise
    finally:dump(out/'run.json',run)
    print(json.dumps({k:run[k] for k in ('status','valid','total','prompt_version')},ensure_ascii=False))

if __name__=='__main__':main()

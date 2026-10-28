from pathlib import Path
import json,csv,shutil,hashlib,zipfile,html,math
HERE=Path(__file__).resolve().parent;SOURCE=HERE/'scores_2b';OUT=HERE/'review'
run=json.loads((SOURCE/'run.json').read_text());verification=json.loads((SOURCE/'verification.json').read_text())
assert run['status']=='complete' and run['valid']==run['total']==16 and verification['passed']
rows=json.loads((SOURCE/'scores.json').read_text())['results'];assert len({(r['scene'],r['episode_id']) for r in rows})==16 and len({r['scene'] for r in rows})==8
OUT.mkdir(exist_ok=False);(OUT/'images').mkdir();cards=[]
for row in rows:
 assert row['valid'] and abs(sum(row[k] for k in ['p_low','p_medium','p_high'])-1)<1e-12
 assert abs(row['q']-.5*row['p_medium']-row['p_high'])<1e-12
 source=Path(row['image']);name=f"{row['group_id']}_{row['id']}_{row['scene']}_ep{row['episode_id']}.png";target=OUT/'images'/name;shutil.copyfile(source,target)
 assert hashlib.sha256(target.read_bytes()).hexdigest()==row['image_sha256'];row['image']='images/'+name
 cards.append(f'''<article><h2>{html.escape(row['scene'])} / task {row['episode_id']} — q={row['q']:.4f}</h2><p>LOW {row['p_low']:.4f} · MEDIUM {row['p_medium']:.4f} · HIGH {row['p_high']:.4f}</p><p>Actions {row['action_count']} · New area {row['new_area_m2']:.4f} m² · Efficiency {row['new_area_m2_per_action']:.4f} m²/action</p><a href="{row['image']}"><img src="{row['image']}" alt="{row['scene']}"></a></article>''')
with (OUT/'scores.csv').open('w',newline='') as f:
 fields=['group_id','id','scene','episode_id','action_count','new_area_m2','new_area_m2_per_action','p_low','p_medium','p_high','q','valid','prompt_version']
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
(OUT/'scores.json').write_text(json.dumps({'model':'Qwen3.5-2B','dtype':run['dtype'],'prompt_version':run['prompt_version'],'results':rows},ensure_ascii=False,indent=2)+'\n')
for file in ['prompt.txt','verification.json','batch_00.json','batch_01.json']:shutil.copyfile(SOURCE/file,OUT/file)
shutil.copyfile(HERE/'plan.json',OUT/'trajectory_selection.json');shutil.copyfile(HERE/'display_reconstruction.json',OUT/'map_audit.json')
(OUT/'index.html').write_text('''<!doctype html><html lang="zh"><meta charset="utf-8"><title>Gibson diverse scenes — Qwen2B</title><style>body{font:16px system-ui;margin:24px;background:#f5f6f8;color:#172033}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:20px}article{background:white;padding:16px;border-radius:12px}img{width:100%}h2{font-size:19px}</style><h1>Gibson：8场景×2不同任务，Qwen3.5-2B单图独立评分</h1><p>A/B/C logits → 三候选softmax(T=1)；q=0.5×P(MEDIUM)+P(HIGH)。FP32。<a href="scores.csv">CSV</a> · <a href="scores.json">JSON</a> · <a href="prompt.txt">Prompt</a></p><p>沿用之前相同prompt；不是组内排名。固定公开SIGN权重随机采样，每任务最多256步，提前终止保留实际长度。新增面积按0.025m二维导航视域mask计算，扣初始视野，fog原点边界投影≤5cm。尚未经人工准确性验证。</p><main>'''+''.join(cards)+'</main></html>')
archive=HERE/'qwen2b_gibson_diverse_review.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for f in OUT.rglob('*'):
  if f.is_file():z.write(f,f.relative_to(OUT))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None and len([n for n in z.namelist() if n.endswith('.png')])==16
(HERE/'complete.json').write_text(json.dumps({'valid':16,'scenes':8,'tasks':16,'zip':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'prompt_version':run['prompt_version'],'verification':verification},indent=2)+'\n')
print(archive,archive.stat().st_size,flush=True)

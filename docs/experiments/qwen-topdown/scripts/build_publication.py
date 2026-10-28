"""Build/check an immutable Qwen evidence snapshot; no inference or Git mutations."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse,csv,gzip,hashlib,io,json,re,subprocess,sys
ROOT=Path('/scratch/e1538633/liuyi');TREE=ROOT/'SIGN-qwen-topdown-judge'
CODE='4cc7257d640ddb2216fd6b20b1fc929f465287e4'
REL=Path('docs/experiments/qwen-topdown');OUT=TREE/REL
PILOT=ROOT/'logs/gibson_topdown_pilot_20261028';ABC=ROOT/'logs/qwen_token_probabilities_20261028'
DIVERSE=ROOT/'logs/qwen_gibson_diverse_20261028';SPEED=ROOT/'logs/qwen_single_latency_20261028';IO=ROOT/'logs/qwen_topdown_engineering_20261028'
FILES={}
def sha(data):return hashlib.sha256(data).hexdigest()
def write(name,data,source=None,generated=False):
    p=OUT/name
    if p.exists() and p.read_bytes()!=data:
        if name=='workspace/WORKLOG.md':assert data.startswith(p.read_bytes()),'Published log prefix changed'
        else:assert generated or name=='scripts/build_publication.py' or name in ('workspace/AGENTS.md','workspace/STATUS.md','workspace/RUNBOOK.md'),'Immutable evidence changed: '+name
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    FILES[name]={'bytes':len(data),'sha256':sha(data),'generated':generated}
    if source:FILES[name].update(source=str(source.relative_to(ROOT)),source_sha256=sha(source.read_bytes()))
def copy(source,name,compress=False):
    raw=source.read_bytes();data=raw
    if compress:
        buffer=io.BytesIO()
        with gzip.GzipFile(fileobj=buffer,mode='wb',filename='',mtime=0) as f:f.write(raw)
        data=buffer.getvalue();assert gzip.decompress(data)==raw
    write(name,data,source)
    if compress:FILES[name]['compression']='gzip'
def json_file(name,value):write(name,(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode(),generated=True)
def text_file(name,value):write(name,value.encode(),generated=True)
def selected(folder,prefix,names):
    for name in names:
        if (folder/name).is_file():copy(folder/name,prefix+'/'+name)
def run_files(folder,prefix):
    run=json.loads((folder/'run.json').read_text());assert run['status']=='complete' and run['valid']==run['total']==16
    for p in folder.iterdir():
        if p.is_file() and p.suffix in ('.json','.csv','.txt','.md'):copy(p,prefix+'/'+p.name)
    return json.loads((folder/'scores.json').read_text())['results']
def portable_manifest(source,name,images):
    spec=json.loads(source.read_text())
    for group in spec['groups']:
        for item in group['items']:
            key=(group['id'],item['id']);item['image']='../'+images[key]
    json_file(name,spec)
def check():
    m=json.loads((OUT/'publication_manifest.json').read_text())
    actual={str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()}
    assert actual==set(m['files'])|{'publication_manifest.json'}, actual^set(m['files'])
    for name,item in m['files'].items():
        p=OUT/name;data=p.read_bytes();assert len(data)==item['bytes'] and sha(data)==item['sha256'],name
        assert len(data)<12*1024*1024 and p.suffix.lower() not in ('.pth','.pt','.glb','.navmesh','.zip','.mp4'),name
        if item.get('compression'):assert sha(gzip.decompress(data))==item['source_sha256']
        if p.suffix in ('.md','.json','.py','.txt','.csv','.pbs','.log','.yaml'):
            s=data.decode('utf-8')
            assert not re.search(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}|hf_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}',s),name
            if p.suffix=='.md':
                for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',s):
                    if re.match(r'https?://|#',target):continue
                    assert not target.startswith('/') and (p.parent/target.split('#')[0]).resolve().exists(),(name,target)
                for target in re.findall(r'<img[^>]+src="([^"]+)"',s):assert (p.parent/target).exists(),(name,target)
    assert sha((TREE/'README.md').read_bytes())==m['root_readme_sha256']
    assert not subprocess.check_output(['git','diff',CODE,'--','src','scripts','tests','exp_config','run_sim.py'],cwd=TREE)
    previous=subprocess.run(['git','show',CODE+':'+str(REL/'workspace/WORKLOG.md')],cwd=TREE,capture_output=True)
    if previous.returncode==0:assert (OUT/'workspace/WORKLOG.md').read_bytes().startswith(previous.stdout)
    sys.path.insert(0,str(TREE/'src'))
    from qwen_single_image import load_manifest
    for manifest in ['pilot.json','diverse.json']:
        _,rows=load_manifest(OUT/'manifests'/manifest);assert len(rows)==16
        for r in rows:assert sha(Path(r['image']).read_bytes())==r['image_sha256']
    assert len(list((OUT/'images/pilot').glob('group_*/C*.png')))==16
    assert len(list((OUT/'images/diverse').glob('group_*/C*.png')))==16
    print('CHECKED',len(m['files']),'files',sum(x['bytes'] for x in m['files'].values()),'bytes')
def build():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=TREE,text=True).strip()==CODE
    assert subprocess.check_output(['git','remote','get-url','--push','origin'],cwd=TREE,text=True).strip()=='git@github.com:yiichu03/SIGN.git'
    images={};image_index=[]
    for cohort,source in [('pilot',PILOT),('diverse',DIVERSE)]:
        mapping={}
        for folder in sorted(source.glob('group_*/C*')):
            if not (folder/'trajectory.json').exists():continue
            group,case=folder.parent.name,folder.name;name=f'images/{cohort}/{group}/{case}.png'
            copy(folder/'topdown_static.png',name);mapping[(group,case)]=name
            t=json.loads((folder/'trajectory.json').read_text());image_index.append({'cohort':cohort,'group_id':group,'id':case,'image':name,'sha256':FILES[name]['sha256'],'scene':Path(t['scene_id']).stem,'episode_id':t['episode_id']})
            for file in ['trajectory.json','display_map_data.npz','map_data.npz','task.json.gz']:
                source_file=folder/file
                if not source_file.exists():source_file=folder.parent/file
                target_file=file+'.gz' if file.endswith('.json') else file
                copy(source_file,f'evidence/trajectories/{cohort}/{group}/{case}/'+target_file,compress=file.endswith('.json'))
        assert len(mapping)==16;images[cohort]=mapping
        for group in ['group_01','group_02']:copy(source/group/'overview_static.png',f'images/{cohort}/{group}/overview.png')
        selected(source,f'evidence/collection/{cohort}',['plan.json','collection_complete.json','coverage.csv','display_reconstruction.json','render_manifest.json','map_audit.json','complete.json','scheduler_final.txt','submission.json'])
    json_file('images/index.json',image_index)
    portable_manifest(ABC/'manifest.json','manifests/pilot.json',images['pilot'])
    portable_manifest(DIVERSE/'manifest.json','manifests/diverse.json',images['diverse'])
    copy(ABC/'manifest.json','evidence/inputs/pilot_manifest.json');copy(DIVERSE/'manifest.json','evidence/inputs/diverse_manifest.json')
    nine=run_files(ABC/'run_1503691','evidence/probability/pilot_9b')
    two=run_files(ABC/'run_2b_1503819','evidence/probability/pilot_2b')
    different=run_files(DIVERSE/'scores_2b','evidence/probability/diverse_2b')
    a={(r['group_id'],r['id']):r for r in nine};b={(r['group_id'],r['id']):r for r in two}
    assert set(a)==set(b)
    for key in a:
        for field in ['image_sha256','action_count','new_area_m2','new_area_m2_per_action','prompt_version']:assert a[key][field]==b[key][field]
    for row in nine+two+different:
        assert row['valid'] and abs(sum(row[k] for k in ['p_low','p_medium','p_high'])-1)<1e-12
        assert abs(row['q']-.5*row['p_medium']-row['p_high'])<1e-12
        assert abs(row['new_area_m2']/row['action_count']-row['new_area_m2_per_action'])<1e-12
    copy(ABC/'run_1503691/prompt.txt','prompts/coverage_abc_v1.txt')
    assert len({r['prompt_version'] for r in nine+two+different})==1
    selected(ABC,'evidence/validation',['tokenizer_probe.json','unit_tests_final.log','unit_tests_fp32.log','scheduler_final.txt','scheduler_2b_1503819.txt','submission.json','retry_submission.json','submission_2b_1503819.json'])
    copy(ABC/'run_1503665/run.json','evidence/failure_bf16/run.json')
    copy(ABC/'score_1503665.pbs.log','evidence/failure_bf16/pbs.log.gz',compress=True)
    for size in ['9B','4B','2B','0.8B']:
        folder=SPEED/('Qwen3.5-'+size)
        for p in folder.glob('*.json'):copy(p,f'evidence/latency/{folder.name}/'+p.name)
        copy(SPEED/(folder.name+'.log'),f'evidence/latency/{folder.name}.log.gz',compress=True)
    selected(SPEED,'evidence/latency',['comparison.json','comparison.csv','training_timing.json','plan.json','gpu.csv','runtime.json','completion.json','scheduler_final.txt','unit_tests.log','latency_comparison.png','latency_comparison.pdf','download_4B.json','download_2B.json','download_0.8B.json'])
    copy(SPEED/'prompt.txt','prompts/latency_json.txt')
    for case in ['gpu_smoke_01','gpu_smoke_02']:
        for p in (IO/case).glob('*'):
            if p.is_file() and p.suffix in ('.json','.txt'):copy(p,f'evidence/legacy_multimage_io/{case}/'+p.name)
    for group in ['group_02','group_02_v2']:
        for file in ['request.json','provenance.json','seal.json']:copy(IO/group/file,f'evidence/legacy_multimage_io/{group}/'+file)
    selected(IO,'evidence/legacy_multimage_io',['smoke_prompt.txt','smoke_prompt_v2.txt','smoke_config.json','source_manifest.json','source_manifest_v2.json'])
    for cohort,folder,names in [
        ('pilot_collection',PILOT,['collect.py','rebuild_display.py','render.py','collect_autox.pbs']),
        ('probability',ABC,['prepare_manifest.py','tokenizer_probe.py','check_results.py','score.pbs','score_2b_review.pbs']),
        ('diverse_collection',DIVERSE,['prepare.py','collect.py','rebuild_display.py','render.py','prepare_manifest.py','check_inputs.py','package.py','run.pbs']),
        ('latency',SPEED,['download_models.py','training_timing.py','run_all.py','benchmark.pbs','summarize.py','plot.py'])]:
        selected(folder,'scripts/'+cohort,names)
    copy(Path(__file__),'scripts/build_publication.py')
    for file in ['AGENTS.md','STATUS.md','RUNBOOK.md','WORKLOG.md']:copy(ROOT/file,'workspace/'+file)
    comparison=[]
    lines=['# Gibson同图：9B与2B独立概率评分\n','两组各8条同任务重复轨迹。每张图独立评价，batch行间不共享图片或对话；相同prompt、metadata、图片SHA，FP32，T=1。q=0.5×P(MEDIUM)+P(HIGH)。不是相对排名。\n','[原始9B CSV](../evidence/probability/pilot_9b/scores.csv) · [原始2B CSV](../evidence/probability/pilot_2b/scores.csv) · [Prompt](../prompts/coverage_abc_v1.txt)\n','| 图片（点击放大） | 场景/任务 | 动作 | 新增m²/动作 | 9B LOW/MED/HIGH | 9B q | 2B LOW/MED/HIGH | 2B q |','|---|---|---:|---:|---|---:|---|---:|']
    index={(x['cohort'],x['group_id'],x['id']):x for x in image_index}
    for key,r in a.items():
        s=b[key];img=images['pilot'][key];entry=index[('pilot',*key)]
        comparison.append({'group_id':key[0],'id':key[1],'scene':entry['scene'],'episode_id':entry['episode_id'],'image':img,'action_count':r['action_count'],'new_area_m2':r['new_area_m2'],'efficiency':r['new_area_m2_per_action'],'q_9b':r['q'],'q_2b':s['q']})
        thumb=f'<a href="../{img}"><img src="../{img}" width="230"></a>'
        lines.append(f"| {thumb} | {entry['scene']} / {entry['episode_id']} / {key[1]} | {r['action_count']} | {r['new_area_m2_per_action']:.4f} | {r['p_low']:.4f}/{r['p_medium']:.4f}/{r['p_high']:.4f} | {r['q']:.4f} | {s['p_low']:.4f}/{s['p_medium']:.4f}/{s['p_high']:.4f} | {s['q']:.4f} |")
    text_file('reports/pilot_9b_2b.md','\n'.join(lines)+'\n');json_file('reports/pilot_comparison.json',comparison)
    buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=comparison[0],lineterminator="\n");writer.writeheader();writer.writerows(comparison);text_file('reports/pilot_comparison.csv',buffer.getvalue())
    lines=['# Gibson跨场景：2B独立概率评分\n','8个此前未展示的场景×2个不同任务，共16条。任务在采集前固定；官方库存标为单层，端点高度差<0.05m。先选5–8m和8–15m距离区间；后者无候选时选另一较长任务。没有按成功或Qwen分数筛图。公开SIGN权重原生随机动作采样，每条最多256步，提前终止保留实际步数。\n','[完整CSV](../evidence/probability/diverse_2b/scores.csv) · [JSON与原logits](../evidence/probability/diverse_2b/scores.json) · [选择计划](../evidence/collection/diverse/plan.json) · [Prompt](../prompts/coverage_abc_v1.txt)\n','| 图片（点击放大） | 场景/任务 | 动作 | 新增m² | m²/动作 | LOW | MEDIUM | HIGH | q |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in different:
        img=images['diverse'][(r['group_id'],r['id'])];thumb=f'<a href="../{img}"><img src="../{img}" width="230"></a>'
        lines.append(f"| {thumb} | {r['scene']} / {r['episode_id']} | {r['action_count']} | {r['new_area_m2']:.4f} | {r['new_area_m2_per_action']:.4f} | {r['p_low']:.4f} | {r['p_medium']:.4f} | {r['p_high']:.4f} | {r['q']:.4f} |")
    text_file('reports/diverse_2b.md','\n'.join(lines)+'\n')
    latency=json.loads((SPEED/'comparison.json').read_text())
    lines=['# 速度记录：生成式JSON与真实logits分开\n','以下旧测速使用单图JSON数字回答，短prompt，BF16/auto，模型常驻。同一A40上测1图、8独立请求batch8与串行；不是把8张图放进一个会话。每模型52次输出包含重复测速，不是52个独立质量样本。\n','| 模型 | 单图秒 | 独立batch8整批秒 | 串行8图秒 | 峰值GiB | 严格JSON通过 |','|---|---:|---:|---:|---:|---:|']
    for name,r in latency['models'].items():lines.append(f"| {name} | {r['single_seconds']:.3f} | {r['eight_independent_batch_seconds']:.3f} | {r['serial8_seconds']:.3f} | {r['peak_gpu_gib']:.2f} | {r['valid_answers']}/{r['answers']} |")
    lines+=['\n![旧JSON链路测速](../evidence/latency/latency_comparison.png)','\n当前ABC概率评分使用FP32前向，不生成JSON数字。它的实际批次秒数如下（包含预处理/读出审计，不能与旧BF16生成式耗时混为同一工作负载）：\n','| 评分批次 | 每批8图秒 |','|---|---|']
    for label,folder in [('9B pilot',ABC/'run_1503691'),('2B pilot',ABC/'run_2b_1503819'),('2B diverse',DIVERSE/'scores_2b')]:
        times=[json.loads(p.read_text())['audit']['seconds'] for p in sorted(folder.glob('batch_*.json'))];lines.append('| '+label+' | '+' / '.join(f'{x:.3f}' for x in times)+' |')
    lines+=['\n[完整测速JSON](../evidence/latency/comparison.json) · [任意测速prompt](../prompts/latency_json.txt) · [实测训练每轮时间](../evidence/latency/training_timing.json)\n','旧训练最近500轮均值约3.99/6.58/8.85秒（冻结基线/coverage256/coverage32）；每轮8×256环境动作。同步相加仅为成本估计，未测在线绘图、IPC及同GPU争用，不能把旧测速估计当成新FP32评分的端到端训练实测。']
    text_file('reports/latency.md','\n'.join(lines)+'\n')
    readme='''# Qwen 单图top-down评分（Gibson）

当前代码：`phase2/qwen-topdown-judge @ 4cc7257`。每张图独立评价，一次可将8个独立会话组成batch；无同任务分组要求。本包保存2026-10-28已完成的离线实验，尚未接入PPO或改动trainer、采样、coverage reward。

## 看图片和分数

- **[9B / 2B 同图对照：16张](reports/pilot_9b_2b.md)**：Edgemere、Denmark各8条同任务重复轨迹。
- **[2B 跨场景 / 不同任务：16张](reports/diverse_2b.md)**：8个新场景各2个不同任务。
- [速度记录与原始输出](reports/latency.md)：保留4模型生成式JSON测速，明确区分当前真实logits评分。
- [图片来源与SHA索引](images/index.json)：32张不同top-down图去重存储，另保留4张overview。

## 当前评分方法与验证

[A/B/C评分prompt](prompts/coverage_abc_v1.txt)对应A=LOW、B=MEDIUM、C=HIGH。读取真实assistant回答位置的下一token原logits；当前tokenizer为A32/B33/C34，T=1对三候选softmax，`q=0.5*p_medium+p_high`。这些是三候选条件概率，不是校准的成功率；每图还记录全词表中ABC总概率candidate_mass。

同一模型只加载一次，独立batch预处理复用现有实现。新概率CLI默认FP32；原JSON生成与benchmark默认auto保持。最初BF16单张/batch概率最大差0.02936，检查阻止了产出；[失败run](evidence/failure_bf16/run.json)与[原错误日志](evidence/failure_bf16/pbs.log.gz)保留，没有提高阈值掩盖错误。FP32通过left padding/实际回答位置、单图与batch、排列不变性、forward与生成首步raw logits对照；生成只用于位置核验，正式分数不从JSON数字反推。

| 作业 | 模型 / 图片 | 结果 | batch/solo最大概率差 | 排列 / forward-generation差 |
|---|---|---|---:|---|
| 1503691 | 9B pilot16 | 16/16有效 | 1.74e-5 | 0 / 0 |
| 1503819 | 2B同图16 | 16/16有效 | 1.42e-5 | 0 / 0 |
| 1503973 | 2B跨场景16 | 16/16有效 | 2.23e-5 | 0 / 0 |

25项单测通过。[9B验证](evidence/probability/pilot_9b/verification.json)、[2B同图验证](evidence/probability/pilot_2b/verification.json)、[2B跨场景验证](evidence/probability/diverse_2b/verification.json)。用户给出“我感觉评分还挺不错的”的整体反馈；尚无冻结的逐图人工标签或独立准确率评估，离线评分也不证明训练收益。当前等待用户决定后续方向。

## 面积、动作与图片口径

manifest逐图提供action_count、new_area_m2，并计算/验证new_area_m2_per_action。面积由保存的mask新增有效格数×每像素米数平方重算，与轨迹动作数及CSV核对，**没有从覆盖率百分比推算平方米**。扣初始视野，统计3m/90°的二维可通行区视域并集。图片使用0.025m显示重建、固定初始高度切片和最多5cm的fog原点边界投影；这是导航网格代理，不是RGB表面积，也不同于训练reward的0.1m口径。原0.1m与显示mask、逐步XYZ/朝向/动作在[evidence/trajectories](evidence/trajectories)保留。

轨迹来自公开SIGN导航/安全权重的原生随机动作，不是Qwen控制。最多256动作或真实提前结束。没有中途时间/朝向标注，图片交叉不自动代表无效重复搜索。公开模型权重、场景、环境、第一人称RGB序列不在此包内。

## 复用入口

核心：[src/qwen_single_image.py](../../../src/qwen_single_image.py)；CLI：[scripts/score_qwen_single.py](../../../scripts/score_qwen_single.py)；可编辑prompt：[scripts/prompts/qwen_single_coverage_abc.txt](../../../scripts/prompts/qwen_single_coverage_abc.txt)；测试：[tests/test_qwen_single_image.py](../../../tests/test_qwen_single_image.py)。

在已配置qwen35的PBS GPU作业内，从仓库根执行（模型路径按本机填写，out必须全新）：

```bash
python scripts/score_qwen_single.py \\
  --manifest docs/experiments/qwen-topdown/manifests/diverse.json \\
  --prompt docs/experiments/qwen-topdown/prompts/coverage_abc_v1.txt \\
  --model-dir /path/to/Qwen3.5-2B \\
  --out results/my_qwen_scores --batch-size 8 --verify
```

[pilot manifest](manifests/pilot.json)与[diverse manifest](manifests/diverse.json)使用仓库内相对图片路径，可直接复用；只改prompt即可换评分角度，保持A/B/C映射。每次保存prompt内容SHA、图片副本、metadata、输入token/mask/grid、原logits与结果。原始审计JSON中的服务器绝对路径是当时输入的原文，保留以便追溯；仓库内图片位置以可移植manifest和图片索引为准。

[scripts](scripts)保存服务器端采集、导图、面积核对和PBS脚本快照，部分脚本依赖原服务器目录；不是新的Qwen调用框架。[旧八图同会话连通性证据](evidence/legacy_multimage_io)仅用于历史回溯，不属于当前单图评分协议。

## 文档维护与证据

[AGENTS](workspace/AGENTS.md)、[STATUS](workspace/STATUS.md)、[RUNBOOK](workspace/RUNBOOK.md)、[WORKLOG](workspace/WORKLOG.md)是服务器根四文档的自动生成快照，根文件仍是维护源；不要手工维护两份。已有覆盖奖励研究材料留在原位。[publication_manifest.json](publication_manifest.json)记录每个文件的SHA、大小与来源；构建脚本只生成/校验，不自动训练、评分或推送。
'''
    text_file('README.md',readme)
    root_readme=(TREE/'README.md').read_text();navigation='\n## Qwen independent top-down scoring\n\n[Experiment overview, images, probabilities and reproduction](docs/experiments/qwen-topdown/README.md) · [9B/2B same-image comparison](docs/experiments/qwen-topdown/reports/pilot_9b_2b.md) · [2B diverse Gibson scenes/tasks](docs/experiments/qwen-topdown/reports/diverse_2b.md)\n'
    if '## Qwen independent top-down scoring' not in root_readme:(TREE/'README.md').write_text(root_readme+navigation)
    manifest={'generated_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),'code_commit':CODE,'branch':'phase2/qwen-topdown-judge','target':'yiichu03/SIGN','unique_topdown_images':32,'probability_outputs':48,'root_readme_sha256':sha((TREE/'README.md').read_bytes()),'files':FILES}
    (OUT/'publication_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    check()
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');args=parser.parse_args()
    check() if args.check_only else build()

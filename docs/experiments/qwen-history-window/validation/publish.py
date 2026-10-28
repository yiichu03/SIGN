"""Publish verified evidence plus generated workspace snapshots; no inference or push."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,re,shutil,subprocess
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;TREE=ROOT/'SIGN-qwen-history-window';OUT=TREE/'docs/experiments/qwen-history-window';CODE='0bb9a90daac3c9199c4f19245c7c93e7f85079fc'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 m=json.loads((OUT/'publication_manifest.json').read_text())
 actual={str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()}
 assert actual==set(m['files'])|{'publication_manifest.json'}
 for name,r in m['files'].items():
  p=OUT/name;assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes'],name
  assert p.suffix.lower() not in ['.pth','.pt','.safetensors','.glb','.navmesh','.zip'] and p.stat().st_size<15*1024**2,name
  if p.suffix in ['.md','.txt','.json','.py','.html','.csv','.pbs','.log','.diff']:
   s=p.read_text();assert not re.search(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|hf_[A-Za-z0-9]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}',s),name
   if p.suffix=='.md':
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',s):
     if re.match(r'https?://|#',target):continue
     assert not target.startswith('/') and (p.parent/target.split('#')[0]).resolve().exists(),(name,target)
 for file,r in json.loads((OUT/'bundle_manifest.json').read_text())['files'].items():assert sha(OUT/file)==r['sha256'],file
 assert not subprocess.check_output(['git','diff',CODE,'--','src','scripts','tests','exp_config','run_sim.py'],cwd=TREE)
 assert sha(TREE/'README.md')==m['root_readme_sha256']
 print('Publication check PASSED',len(m['files']),'files',sum(r['bytes'] for r in m['files'].values()),'bytes')
def build():
 assert json.loads((HERE/'browser_check.json').read_text())['passed']
 assert json.loads((HERE/'bundle_check.json').read_text())['passed']
 assert subprocess.check_output(['git','remote','get-url','--push','origin'],cwd=TREE,text=True).strip()=='git@github.com:yiichu03/SIGN.git'
 assert subprocess.check_output(['git','branch','--show-current'],cwd=TREE,text=True).strip()=='phase2/qwen-history-window'
 shutil.copytree(HERE/'review',OUT)
 validation=OUT/'validation';validation.mkdir()
 for name in ['bundle_check.json','bundle_check.log','browser_check.json','browser_check.log','browser_blind.png','browser_scores.png','check_bundle.py','browser_check.py','scheduler_completed.txt','submission.json','revision.json','run.pbs.log','unit_tests.log','input_guard.json','check_inputs.py','run.pbs','publish.py']:
  if (HERE/name).exists():shutil.copyfile(HERE/name,validation/name)
 workspace=OUT/'workspace';workspace.mkdir()
 for name in ['AGENTS.md','STATUS.md','RUNBOOK.md','WORKLOG.md']:shutil.copyfile(ROOT/name,workspace/name)
 a=json.loads((OUT/'analysis.json').read_text());qc=json.loads((HERE/'bundle_check.json').read_text());scores=json.loads((OUT/'scores/run.json').read_text())
 text='''# Qwen2B历史窗口：交付与验证

最终作业1505092（CFP/autox/A40），运行代码0bb9a90；首跑1505083完成后，像素检查发现起终点同格时绿点被X遮挡，改为同点外绿圈后仅用2B补跑。原始轨迹/覆盖口径/prompt/动作与窗口定义不变。

- [完整报告：128／256、整体历史与黄线对照](REPORT.md)
- [离线审阅页](index.html)：下载ZIP解压后在本地打开；默认隐藏模型分数，可切换显示。
- [评分CSV](scores.csv) · [结果JSON](results.json) · [空白人审CSV](human_review.csv) · [窗口清单](window_list.csv)
- [原始窗口与输入映射](windows.json) · [prompt最小差异](prompts/history.diff) · [复现说明](README.md)
- [实际浏览器验证](validation/browser_check.json) · [像素/面积/哈希验证](validation/bundle_check.json)

64次请求去重44片段：完整128步12段有真实历史；完整256步5段全部无前置历史；短段27个单列。100张实际输入，32张严格复用发布2B旧分数、68张新FP32概率读出。旧分数只有图片SHA/promptSHA/实际metadata一致且同模型配置/FP32/版本时复用。

本数据不能检验256步历史能力；无历史段的分数变化也不代表模型理解历史。报告只描述输入敏感性，不用平均q判优，没有人工真值、准确率或PPO收益结论。重复搜索、必要返回、有效扩展、碰撞受阻仅列待人审线索，标签保持空白。

根四文档的生成快照在workspace，服务器根文件继续作为维护源。原实验/失败/补跑的操作沿革见workspace/WORKLOG.md；原始评分审计在scores，复用的原批次输入/耗时在sources/*_2b_batch_*.json。绘图源均保持原2.5cm/3m/90°，不与导航训练0.1m口径混用。
'''
 text+=f"\nZIP实际路径：{HERE/'qwen2b_history_review.zip'}；{qc['zip_bytes']} bytes，SHA256 {qc['zip_sha256']}。ZIP通过CRC、全部文件SHA和实际Chromium file://断网浏览，100图片解码、默认隐藏/开关、筛选与空白人审检查通过。\n"
 (OUT/'VALIDATION.md').write_text(text)
 rootreadme=TREE/'README.md';s=rootreadme.read_text();s+='\n## Qwen history-window offline evaluation\n\n[Results, controls and validation](docs/experiments/qwen-history-window/VALIDATION.md) · [128/256 report](docs/experiments/qwen-history-window/REPORT.md) · [Blank human review table](docs/experiments/qwen-history-window/human_review.csv)\n';rootreadme.write_text(s)
 files={str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.rglob('*')) if p.is_file()}
 manifest={'generated_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),'target':'yiichu03/SIGN','branch':'phase2/qwen-history-window','runtime_commit':CODE,'job_id':'1505092.stdct-mgmt-02','zip_path':str(HERE/'qwen2b_history_review.zip'),'zip_sha256':qc['zip_sha256'],'root_readme_sha256':sha(rootreadme),'files':files}
 (OUT/'publication_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');check()
if __name__=='__main__':
 import sys
 check() if '--check-only' in sys.argv else build()

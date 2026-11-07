"""Self-contained report ZIP plus complete diagnostic evidence; no weights/scenes."""
from datetime import datetime, timedelta, timezone
import csv
from html.parser import HTMLParser
import hashlib
import json
import posixpath
from pathlib import Path
import shutil
import tempfile
import subprocess
from urllib.parse import unquote, urlparse
import zipfile

HERE = Path(__file__).resolve().parent

def sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()

REPORT = HERE/'analysis'


class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[]

    def handle_starttag(self, tag, attrs):
        for key,value in attrs:
            if key in ['href','src'] and value:
                parsed=urlparse(value)
                if not parsed.scheme and parsed.path:
                    self.links.append(unquote(parsed.path))


def archive(target, files):
    assert not target.exists(), target
    temporary=target.with_suffix('.partial.zip')
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as z:
        for file,name in files:
            assert file.suffix.lower() not in ['.pth','.pt','.glb','.lmdb','.h5'], file
            mode=zipfile.ZIP_STORED if file.suffix.lower() in ['.mp4','.npz','.png','.jpg','.pdf'] else zipfile.ZIP_DEFLATED
            z.write(file,name,compress_type=mode)
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
    temporary.replace(target)
    return dict(path=str(target),bytes=target.stat().st_size,
                sha256=sha256_file(target),files=len(files))


def main():
    assert (REPORT/'report_ready.json').exists()
    from guard import guard
    guard()
    checked={}
    fields=['steps','success','spl','view_match','navigation_reward','collisions',
            'goal_sha256','start_position','pose_trace_sha256','new_area_m2','new_m2_per_step']
    for case in ['baseline','coverage256','coverage32']:
        reference=json.loads((HERE/(case+'_reference.json')).read_text())
        rows=[json.loads(line) for file in (HERE/'full'/case/'diagnostic'/'episodes').glob('*.jsonl')
              for line in file.read_text().splitlines()]
        keys=[Path(row['scene_id']).stem+':'+row['episode_id'] for row in rows]
        assert len(rows)==len(set(keys))==4200 and set(keys)==set(reference)
        for key,row in zip(keys,rows):
            for field in fields:
                assert row[field]==reference[key][field], (case,key,field,row[field],reference[key][field])
        checked[case]=dict(episodes=len(rows),all_reference_fields_exact=True)
    (REPORT/'reference_audit.json').write_text(json.dumps(dict(
        checked_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        original_sources_and_recording_inputs_unchanged=True,
        compared_fields=fields,cases=checked),indent=2)+'\n')
    episodes=json.loads((REPORT/'episodes.json').read_text())
    paired={}
    models=['baseline','coverage256','coverage32']
    for row in episodes:
        key=(row['scene_id'],row['episode_id'])
        assert row['case'] not in paired.setdefault(key,{})
        paired[key][row['case']]=row
    paired_rows=[]
    for (scene,episode),items in sorted(paired.items()):
        assert set(items)==set(models)
        row=dict(scene_id=scene,episode_id=episode,
                 success_pattern=''.join('S' if items[c]['success'] else 'F' for c in models))
        for model in models:
            for field in ['success','steps','minimum_distance','observed_stage','trace','video']:
                row[model+'_'+field]=items[model][field]
        paired_rows.append(row)
    assert len(paired_rows)==4200
    for filename,rows in [('paired_tasks.csv',paired_rows),
                          ('common_failures.csv',[r for r in paired_rows if r['success_pattern']=='FFF'])]:
        with (REPORT/filename).open('w') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(paired_rows[0]))
            writer.writeheader();writer.writerows(rows)
    (REPORT/'overlap_audit.json').write_text(json.dumps(dict(
        model_episode_failures=sum(not r['success'] for r in episodes),
        distinct_tasks_failed_any=sum(r['success_pattern']!='SSS' for r in paired_rows),
        distinct_tasks_failed_all=sum(r['success_pattern']=='FFF' for r in paired_rows)),indent=2)+'\n')
    source=REPORT/'source';source.mkdir(exist_ok=True)
    for p in HERE.iterdir():
        if p.is_file() and (p.suffix in ['.py','.pbs','.json']):
            shutil.copy2(p,source/p.name)
    # Keep the raw short-test proof, including its successful-episode videos,
    # independently inspectable instead of packaging only a "passed" flag.
    shutil.copytree(HERE/'smoke'/'baseline',source/'smoke'/'baseline',dirs_exist_ok=True)
    manifest=json.loads((HERE/'source_manifest.json').read_text())
    native=Path('/scratch/e1538633/liuyi/SIGN-coverage-eval')
    for name,digest in manifest['trees']['SIGN-coverage-eval']['files'].items():
        original=native/name
        assert sha256_file(original)==digest
        target=source/'native'/'SIGN-coverage-eval'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(original,target)
    # Small dependency excerpts let readers inspect the actual STOP/success
    # chain offline; do not copy dependencies, environments or scene assets.
    dependency=Path('/scratch/e1538633/liuyi/habitat-lab')
    excerpts={}
    for name in ['habitat-lab/habitat/core/env.py','habitat-lab/habitat/tasks/nav/nav.py',
                 'habitat-lab/habitat/utils/visualizations/maps.py',
                 'habitat-lab/habitat/utils/visualizations/fog_of_war.py']:
        target=source/'native'/'habitat-lab'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(dependency/name,target)
        excerpts[name]=sha256_file(target)
    for original,target in [(native/'LICENSE',source/'native'/'SIGN-coverage-eval'/'LICENSE'),
                            (dependency/'LICENSE',source/'native'/'habitat-lab'/'LICENSE')]:
        if original.exists():shutil.copy2(original,target)
    (source/'dependency_excerpt_manifest.json').write_text(json.dumps(dict(
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=dependency,text=True).strip(),
        files=excerpts),indent=2)+'\n')
    (REPORT/'reproduce.txt').write_text('''服务器上的原始支持目录：/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104
本包analysis/index.html和review/index.html可离线打开，所有图像/精选完整视频在包内。
analysis/source包含采集、分析、绘图脚本及输入/协议/权重SHA与作业回执，不含模型权重、原场景或环境。
failure_analysis_evidence.zip另含全部三模型诊断的traces/videos/episodes/diagnostics/native结果，解压到同一上级目录可恢复full/...相对路径。
每条NPZ对应一个真实episode。position_xyz单位m，rotation_xyzw是四元数，metrics列名保存在metric_fields。
所有逐步数组长度为T+1：第0行为初始观测；command[t]由position[t-1]执行到position[t]，第0行command/action仅为占位。
action_normalized_linear_angular与command_mps_degps都按线速度/角速度排列，后者是FP64名义单位换算；STOP审计使用native的FP32缩放边界。
视频左为固定目标、右为动作后RGB，frame0是初始观测；10fps仅为播放速度，保留所有T+1帧。图中文字距离有四舍五入，分类使用全精度d<1。
审查视频是有损H264，关键帧JPEG也有损，不能据此逐像素重建原Actor输入或隐藏状态；目标PNG无损并核对原RGB字节SHA。
地图蓝色是包含初始视野的累计已见并集；橙色统计线是扣除初始视野的新增面积。多高度背景只显示初始层；面积仍为原XZ投影代理。
所有失败有视频，成功仅保存预先选定的每场景3个对照；所有12600条都保存完整数值轨迹。人审主因字段留空。
重算（需要原服务器依赖，输出应使用新的空目录）：
  envs/sign-baseline/bin/python logs/sign_failure_replay_20261104/analyze.py --out 新的输出目录
当前report.py/package.py按既有analysis目录生成浏览和打包资料；不重复提交已完成的GPU作业。
实际被动性/原目标起点/轨迹一致性见smoke_passed与各full/case/diagnostic/result.json。
真实观测阶段和非互斥行为证据分开，人工标签留空；AI初审不等于人工真值。
''')
    files=[(p,str(p.relative_to(HERE))) for p in sorted(REPORT.rglob('*')) if p.is_file()]
    report_zip=HERE/'failure_analysis_report.zip'
    report_info=archive(report_zip,files)
    with tempfile.TemporaryDirectory(prefix='unzip_verify_',dir=HERE) as tmp:
        with zipfile.ZipFile(report_zip) as z:z.extractall(tmp)
        tmp=Path(tmp);links=0
        for file in (tmp/'analysis').rglob('*.html'):
            parser=LocalLinks();parser.feed(file.read_text())
            for relative in parser.links:
                target=(file.parent/relative).resolve()
                try:
                    target.relative_to(tmp.resolve())
                except ValueError:
                    raise AssertionError((file,relative,'outside extracted archive'))
                assert target.exists(), (file,relative)
                links+=1
    # Full trace/video/data archive keeps the on-server relative layout. Never
    # include source checkpoints or training/output directories outside full/.
    raw=[]
    for case in ['baseline','coverage256','coverage32']:
        folder=HERE/'full'/case/'diagnostic'
        assert json.loads((folder/'result.json').read_text())['episodes']==4200
        raw.extend((p,str(p.relative_to(HERE))) for p in sorted(folder.rglob('*')) if p.is_file())
    evidence_info=archive(HERE/'failure_analysis_evidence.zip',raw)
    result=dict(created_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
                report=report_info,evidence=evidence_info,actual_report_unzip_passed=True,
                offline_html_local_links_verified=links,archives_crc_passed=True)
    (HERE/'package_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()

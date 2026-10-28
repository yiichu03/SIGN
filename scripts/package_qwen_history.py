#!/usr/bin/env python3
"""Build a blind-by-default offline review bundle. Human labels remain empty."""
import argparse
import csv
import hashlib
import html
import json
import shutil
import zipfile
from pathlib import Path


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def csv_file(path, rows):
    with Path(path).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def category(result):
    return ['LOW','MEDIUM','HIGH'][max(range(3), key=lambda i: result[['p_low','p_medium','p_high'][i]])]


def paired(a, b):
    return dict(q_a=a['q'], q_b=b['q'], q_delta=b['q']-a['q'],
                class_a=category(a), class_b=category(b),
                total_variation=.5*sum(abs(a[k]-b[k]) for k in ['p_low','p_medium','p_high']))


def package(data, zip_path):
    spec = json.loads((data/'windows.json').read_text())
    segments = spec['segments']
    results = json.loads((data/'scores/results.json').read_text())
    run = json.loads((data/'scores/run.json').read_text())
    assert run['status'] == 'complete' and run['valid'] == run['total'] == len(spec['inputs'])
    result_map = {(r['segment_id'], r['variant']):r for r in results}
    assert len(result_map) == len(results)
    flat, review, comparisons = [], [], []
    for s in segments:
        for variant in ['legacy','history'] + (['history_no_yellow'] if s['history_action_count'] else []):
            row = result_map[(s['id'], variant)]
            assert row['result']['valid'] and row['result']['error'] is None
            expected = s['legacy_stats'] if variant == 'legacy' else s['history_stats']
            assert all(value == expected[k] for k,value in row['metadata'].items())
            assert hashlib.sha256((data/row['image']).read_bytes()).hexdigest() == row['image_sha256']
            flat.append(dict(id=row['id'], trajectory_id=s['trajectory_id'], segment_id=s['id'],
                scene=s['scene'], episode_id=s['episode_id'], variant=variant,
                requested_windows=';'.join(map(str,s['requested_windows'])),
                window_start=s['start'], window_end=s['end'], action_count=s['action_count'],
                history_action_count=s['history_action_count'],
                short_for=';'.join(map(str,s['short_for'])), image=row['image'],
                new_area_m2=expected['new_area_m2'], new_area_m2_per_action=expected['new_area_m2_per_action'],
                prior_seen_area_m2=expected['prior_seen_area_m2'],
                total_covered_area_m2=expected['total_covered_area_m2'],
                p_low=row['result']['p_low'], p_medium=row['result']['p_medium'],
                p_high=row['result']['p_high'], q=row['result']['q'],
                logits=json.dumps(row['result']['logits']), valid=True, error='',
                inference=row['inference'], seconds=row['seconds'], timing_scope=row['timing_scope'],
                prompt_version=row['prompt_version'], image_sha256=row['image_sha256']))
        old = result_map[(s['id'],'legacy')]['result']
        full = result_map[(s['id'],'history')]['result']
        comp = dict(segment_id=s['id'], action_count=s['action_count'],
                    requested_windows=s['requested_windows'], short_for=s['short_for'],
                    history_action_count=s['history_action_count'],
                    history_bundle_vs_legacy=paired(old, full))
        if s['history_action_count']:
            hidden = result_map[(s['id'],'history_no_yellow')]
            shown = result_map[(s['id'],'history')]
            assert hidden['metadata'] == shown['metadata'] and hidden['prompt_version'] == shown['prompt_version']
            comp['yellow_line_only'] = paired(hidden['result'], shown['result'])
        comparisons.append(comp)
        review.append(dict(segment_id=s['id'], scene=s['scene'], episode_id=s['episode_id'],
            window_start=s['start'], window_end=s['end'], action_count=s['action_count'],
            history_action_count=s['history_action_count'], short_for=';'.join(map(str,s['short_for'])),
            legacy_image=result_map[(s['id'],'legacy')]['image'],
            history_image=result_map[(s['id'],'history')]['image'],
            hidden_yellow_image=result_map.get((s['id'],'history_no_yellow'),{}).get('image',''),
            human_repeated_search='', human_necessary_return='', human_effective_extension='',
            human_collision_or_blocked='', human_quality_ABC='', human_unknown_reason='',
            reviewer='', reviewed_at='', notes=''))
    csv_file(data/'scores.csv', flat)
    dump(data/'results.json', flat)
    csv_file(data/'human_review.csv', review)
    csv_file(data/'window_list.csv', [{k:v for k,v in r.items() if k not in
        ['human_repeated_search','human_necessary_return','human_effective_extension',
         'human_collision_or_blocked','human_quality_ABC','human_unknown_reason','reviewer','reviewed_at','notes']} for r in review])
    # Purposeful cues are review leads, never human labels or prevalence estimates.
    historical = [s for s in segments if s['history_action_count']]
    low_collision = [s for s in historical if s['collision_actions']/s['action_count'] < .5]
    cue_sets = {
        '重复搜索待核查': sorted(low_collision, key=lambda s:(-s['exact_history_path_cell_fraction'],s['history_stats']['new_area_m2_per_action']))[:2],
        '必要返回待核查': sorted(historical, key=lambda s:-(s['exact_history_path_cell_fraction']*s['history_stats']['new_area_m2']))[:2],
        '有效扩展待核查': sorted(historical, key=lambda s:-s['history_stats']['new_area_m2_per_action'])[:2],
        '碰撞受阻待核查': sorted(segments, key=lambda s:-s['collision_actions']/s['action_count'])[:2],
    }
    candidates = []
    for cue, chosen in cue_sets.items():
        for s in chosen:
            candidates.append(dict(candidate_type=cue, segment_id=s['id'],
                collision_actions=s['collision_actions'], low_translation_actions=s['low_translation_actions'],
                exact_history_path_cell_fraction=s['exact_history_path_cell_fraction'],
                new_m2_per_action=s['history_stats']['new_area_m2_per_action'], human_label=None))
    dump(data/'review_candidates.json', candidates)
    analysis = dict(
        note='Descriptive score changes only. No human ground truth, no mean-q merit ranking.',
        preparation=json.loads((data/'audit/preparation.json').read_text()),
        full128=[c for c in comparisons if c['action_count']==128],
        full256=[c for c in comparisons if c['action_count']==256],
        short_segments=[c for c in comparisons if c['short_for']],
        yellow_line_pairs=[c for c in comparisons if 'yellow_line_only' in c],
        paired_same_endpoint_full128_full256=[
            dict(trajectory_id=a['trajectory_id'], segment128=a['id'], segment256=b['id'])
            for a in segments for b in segments if a['trajectory_id']==b['trajectory_id']
            and a['action_count']==128 and b['action_count']==256])
    dump(data/'analysis.json', analysis)
    lines = ['# Qwen3.5-2B 真实历史窗口离线测评\n',
        '32条已发布原始轨迹，无重新采样；独立单图、FP32、ABC候选softmax、T=1，q=0.5×p_medium+p_high。所有图只显示完整段轨迹，没有中间时间标记。人审标签全部留空。\n',
        '## 样本边界\n',
        f"64次128/256截取请求去重为{len(segments)}个片段，共{len(results)}张输入；32个全轨迹旧协议输入满足图片/prompt/统计完全相同，复用原2B评分，剩余{run['total']-run['reused']}张新前向。去重短段不重复计入比较。\n",
        f"完整128步{len(analysis['full128'])}段，均有真实前置历史；完整256步{len(analysis['full256'])}段，全部没有前置历史。其余{len(analysis['short_segments'])}个短段单列。原轨迹最长256步，**本数据不能验证256步历史能力，也不能验证更长episode、多层或在线PPO收益**。\n",
        '## 128与256分别看\n',
        '以下逐段表按原轨迹ID排列，不按q排序。q只表示模型三候选条件分布，非校准质量/成功率；不以平均q高低认定方案优劣。128/256同终点但当前动作、面积及历史量不同，只有5条轨迹提供完整的两种长度，且256无历史，不能把差异单独归因于窗口长度。\n']
    for label, group in [('完整128步',analysis['full128']), ('完整256步（无前置历史）',analysis['full256']),
                         ('短段（不混入完整窗口主结果）',analysis['short_segments'])]:
        lines += [f'### {label}\n', '| 片段 | 当前/历史动作 | 旧协议q | 历史图q | 隐藏黄线q |',
                  '|---|---:|---:|---:|---:|']
        for c in group:
            sid=c['segment_id']; legacy=result_map[(sid,'legacy')]['result']['q']; hist=result_map[(sid,'history')]['result']['q']
            hidden=result_map.get((sid,'history_no_yellow'),{}).get('result',{}).get('q')
            lines.append(f"| {sid} | {c['action_count']}/{c['history_action_count']} | {legacy:.4f} | {hist:.4f} | "+(f'{hidden:.4f}' if hidden is not None else '—')+' |')
        lines.append('')
    for title,key,cohort in [('历史信息整体作用（完整128步）','history_bundle_vs_legacy',analysis['full128']),
                             ('黄线额外作用','yellow_line_only',analysis['yellow_line_pairs']),
                             ('完整256步无历史协议对照','history_bundle_vs_legacy',analysis['full256']),
                             ('短段无历史协议对照（单列）','history_bundle_vs_legacy',analysis['short_segments'])]:
        changed=sum(c[key]['class_a']!=c[key]['class_b'] for c in cohort)
        changes=[c[key]['q_delta'] for c in cohort]
        lines += [f'## {title}\n',
            f"匹配样本{len(cohort)}对，最高概率类别改变{changed}对；q变化范围{min(changes):+.4f}至{max(changes):+.4f}。完整逐对概率差/TV在analysis.json；这是输入敏感性描述，不是准确率。\n"]
    lines += [
        '旧协议→历史图同时改变历史覆盖背景、面积扣除基线、提示词与总覆盖统计，属于整体输入方案对照，不能拆成单一因果因素。无历史片段主要控制prompt/额外统计/图例影响，不能算历史能力验证。\n',
        '隐藏黄线→完整历史图仅增加黄色历史路径，prompt、深浅蓝覆盖、统计、当前红线、起终点、视野与比例相同。这个配对可隔离黄线对输出的影响，但没有人工真值仍无法判定变化是否正确。\n',
        '整体评分变化也可能来自面积数值或prompt，不证明模型理解历史重复搜索。无前置历史的256步对照也出现输出变化，进一步说明不能把协议变化直接当历史推理能力。隐藏黄线图仍保留历史覆盖底色，并不是完全没有历史信息。\n',
        '## 待人审案例\n',
        '以下为可观测线索筛选的候选，不是自动标注：重复搜索需独立搜索证据；普通返回/公共走廊不自动算冗余，碰撞/受阻/摆动/脱困单列。低位移动作为位移<2cm，历史同格比例仅为2.5cm网格的精确重合线索，都不等于重复搜索。地图缺少RGB语义与中间时序，尤其无法独立确认返回“必要”。所有human_label为空。\n',
        '| 待核查类型 | 片段 | 实测碰撞动作 | 低位移动作 | 历史路径同格比例 |',
        '|---|---|---:|---:|---:|']
    for c in candidates:
        lines.append(f"| {c['candidate_type']} | {c['segment_id']} | {c['collision_actions']} | {c['low_translation_actions']} | {c['exact_history_path_cell_fraction']:.3f} |")
    lines += ['\n请先盲看index.html图像，在human_review.csv填标签/未知/理由，再主动显示模型分数。候选筛选有目的性，不估计各种行为的总体比例。\n']
    (data/'REPORT.md').write_text('\n'.join(lines))
    cards=[]
    for s in segments:
        panels=[]
        for variant,label in [('legacy','旧协议'),('history','完整历史'),('history_no_yellow','隐藏黄线')]:
            row=result_map.get((s['id'],variant))
            if not row:
                continue
            q=row['result'];meta=row['metadata']
            panels.append('<div class="panel"><h3>'+label+'</h3><a href="'+row['image']+'"><img loading="lazy" src="'+row['image']+'" alt="'+html.escape(row['id'])+'"></a>'
                +'<p>当前新增 '+f"{meta['new_area_m2']:.4f} m²；效率 {meta['new_area_m2_per_action']:.5f} m²/action"
                +(f"；总覆盖 {meta['total_covered_area_m2']:.4f} m²" if 'total_covered_area_m2' in meta else '')+'</p>'
                +'<div class="score">LOW '+f"{q['p_low']:.4f} / MEDIUM {q['p_medium']:.4f} / HIGH {q['p_high']:.4f}<br>q={q['q']:.4f}"+'</div></div>')
        cards.append('<section class="case" data-windows="'+','.join(map(str,s['requested_windows']))+'" data-short="'+str(bool(s['short_for'])).lower()+'"><h2>'
            +html.escape(s['scene']+' / '+str(s['episode_id'])+' / '+s['id'])+'</h2><p>动作窗口 ('+str(s['start'])+', '+str(s['end'])+']；当前 '+str(s['action_count'])+' 动作；历史 '+str(s['history_action_count'])+' 动作；请求 '+str(s['requested_windows'])+'；短段 '+str(s['short_for'])
            +'。人审标签：<strong>未填写</strong></p><div class="panels">'+''.join(panels)+'</div></section>')
    page='''<!doctype html><html lang="zh"><meta charset="utf-8"><title>Qwen2B历史窗口盲审</title>
<style>body{font:16px sans-serif;margin:24px;background:#fafafa;color:#202834}.controls{position:sticky;top:0;background:#fff;padding:14px;z-index:20;border:1px solid #ccc}.panels{display:flex;gap:12px}.panel{flex:1;min-width:0;background:white;padding:8px}.panel img{width:100%;height:auto}.score{display:none;background:#edf1fa;padding:10px}body.show-scores .score{display:block}.case{border-top:2px solid #ccd2dc;margin:24px 0}.case[hidden]{display:none}h2{font-size:17px}h3{font-size:16px}p{line-height:1.6}a{color:#234e9b}@media(max-width:800px){.panels{display:block}}</style>
<h1>Qwen3.5-2B：历史窗口离线盲审</h1>
<p>原32条轨迹，不重新采样。历史图：黄色=历史，红色=当前段，深蓝=段前累计已见，浅蓝=本段真正新增。旧协议图：深蓝仅为窗口初始视野，浅蓝仅扣初始视野。绿点与叉只对应当前红色段。无历史256步不验证历史能力。评分默认隐藏，标签尚未填写。</p>
<div class="controls"><label><input id="scores" type="checkbox">显示模型概率与q</label>
<select id="window"><option value="">全部窗口</option><option value="128">请求128步</option><option value="256">请求256步</option></select>
<label><input id="short" type="checkbox">仅看短段</label>
<input id="search" placeholder="场景 / 片段ID">
<a href="human_review.csv">空白人审表CSV</a> · <a href="window_list.csv">窗口清单</a> · <a href="REPORT.md">报告</a> · <a href="scores.csv">评分CSV</a> · <a href="README.md">复现</a></div>
'''+''.join(cards)+'''
<script>
document.getElementById('scores').addEventListener('change',function(){document.body.classList.toggle('show-scores',this.checked)});
function filter(){var w=document.getElementById('window').value,s=document.getElementById('short').checked,q=document.getElementById('search').value.toLowerCase();document.querySelectorAll('.case').forEach(function(e){e.hidden=(w&&!e.dataset.windows.split(',').includes(w))||(s&&e.dataset.short!=='true')||!e.textContent.toLowerCase().includes(q)})}
['window','short','search'].forEach(function(id){document.getElementById(id).addEventListener('input',filter)});
</script></html>'''
    (data/'index.html').write_text(page)
    (data/'README.md').write_text('''# 复现与审计

先用浏览器打开本目录index.html；无需服务器或网络，默认不显示分数。手工标签在human_review.csv，所有人工列为空。
原始轨迹在sources/*/trajectory.json.gz（poses[0]为初始观测，动作记录在poses[1:]），含逐步XYZ/朝向/action/collision。
windows.json记录64次请求到去重片段/100张输入的映射；window_list.csv为便于阅读的清单。
当前动作为(start,end]，当前红线路径含两端pose；历史动作为(0,start]。段前累计已见含pose[start]，避免把起点视野重复发奖。
总覆盖=深蓝+浅蓝=段前已见+本段真正新增。mask来自原2.5cm固定楼层栅格、3m/90°视域，原fog原点≤5cm边界投影不变。
初末重放mask须与已发布原NPZ逐像素相同；不修改原轨迹、不从覆盖百分比推算平方米。不同场景各用原图范围，相互对照保持相同1400×1120画布、地图范围与2m比例尺。
完整历史/隐藏黄线仅路径可见性不同，覆盖、统计、prompt与图例相同；黄色宽虚线衬在红细线下，重合可见黄色两侧。
legacy从当前起点重置可见集合，新增仅扣当前起点视野；history扣全部段前已见。两者统计语义不同，不能把差分当纯黄线因果。

Git分支phase2/qwen-history-window；运行时代码和提交见audit/provenance.json及code/。
在仓库根、已配置的Habitat CPU环境运行（OUT必须全新）：

    python scripts/prepare_qwen_history.py --source docs/experiments/qwen-topdown --prompt scripts/prompts/qwen_single_coverage_abc.txt --out /new/OUT

在PBS GPU的qwen35环境运行，仅Qwen3.5-2B、FP32，模型只加载一次：

    python scripts/evaluate_qwen_history.py --data /new/OUT --model-dir /path/to/Qwen3.5-2B
    python scripts/package_qwen_history.py --data /new/OUT --zip /new/qwen2b_history_review.zip

复用原SingleImageJudge，temperature=1，q=0.5*p_medium+p_high。模型/环境版本、推理耗时、概率、原logits、padding、token IDs、实际chat统计在scores/。
seconds为批次共享耗时，不是单图独立延迟；复用的旧分数seconds留空，原run耗时在sources/*_2b_run.json。
只在PNG SHA、prompt SHA、三个统计完全相同，并核对相同2B配置/FP32/版本后复用旧分数。失败会保存scores/run.json错误及partial_results.json，不以零分填充。
本次数据未给出人审真值；输入敏感性和q变化不是准确率，不用平均q判优，不证明导航训练收益。
''')
    code=data/'code'
    code.mkdir(exist_ok=True)
    tree=Path(__file__).resolve().parents[1]
    for relative in ['scripts/prepare_qwen_history.py','scripts/evaluate_qwen_history.py',
                     'scripts/package_qwen_history.py','src/qwen_single_image.py','src/qwen_topdown.py',
                     'scripts/prompts/qwen_single_coverage_abc.txt','tests/test_qwen_history.py']:
        p=code/relative;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(tree/relative,p)
    files={str(p.relative_to(data)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
           for p in sorted(data.rglob('*')) if p.is_file() and p.name != 'bundle_manifest.json'}
    dump(data/'bundle_manifest.json', dict(files=files, scores=len(results), segments=len(segments),
        human_labels='blank; no automated labels substituted', relative_paths=True))
    if zip_path.exists():
        raise FileExistsError(zip_path)
    with zipfile.ZipFile(zip_path,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(data.rglob('*')):
            if p.is_file():
                z.write(p,p.relative_to(data))
    with zipfile.ZipFile(zip_path) as z:
        assert z.testzip() is None
        assert len([n for n in z.namelist() if n.startswith('images/') and n.endswith('.png')]) == len(results)
    print('Packaged',zip_path,zip_path.stat().st_size,'bytes')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--zip',type=Path,required=True)
    a=p.parse_args()
    package(a.data.resolve(),a.zip.resolve())

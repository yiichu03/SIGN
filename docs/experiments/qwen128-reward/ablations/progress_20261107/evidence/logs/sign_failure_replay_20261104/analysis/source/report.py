"""Offline evidence browser and conventional plots, never an agent controller."""
from collections import Counter, defaultdict
import csv
import html
import json
from pathlib import Path
import shutil

import imageio.v2 as imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE/'analysis'
STAGES = {
    'stop_without_ever_entering_goal_region': '未进入目标区域就STOP',
    'stop_after_leaving_goal_region': '曾进入目标区域、离开后STOP',
    'time_limit_in_goal_region_without_stop': '到限时仍在目标区域、未STOP',
    'time_limit_after_leaving_goal_region': '曾进入目标区域、离开后到限',
    'time_limit_never_entered_goal_region': '从未进入目标区域、用尽步数',
    'other_or_invalid': '其他终止或无效数据',
    'success': '成功对照',
}
BEHAVIORS = {
    'strong_blocked_tail_candidate': '末段持续受阻候选',
    'blocked_run_anywhere_candidate': '曾有连续受阻候选',
    'low_gain_closed_loop_candidate': '低新增闭环候选',
    'stationary_turn_tail_candidate': '末段原地旋转候选',
}
LABELS = {'baseline': '冻结基线（74.240M）', 'coverage256': '覆盖256（125.952M）', 'coverage32': '覆盖32（48.128M）'}


def select_cases(episodes, maximum=96):
    buckets = defaultdict(list)
    for row in episodes:
        if row['success'] or not row['video']:
            continue
        signature = next((tag for tag in BEHAVIORS if row[tag]), 'none')
        buckets[(row['case'], row['observed_stage'], signature)].append(row)
    selected, scenes = [], Counter()
    for key in sorted(buckets):
        candidates = buckets[key]
        chosen = min(candidates, key=lambda r:(scenes[r['scene_id']], r['scene_id'], int(r['episode_id'])))
        selected.append(chosen);scenes[chosen['scene_id']] += 1
    for case in LABELS:
        candidates = [r for r in episodes if r['case']==case and r['success'] and r['video']]
        for with_flag in [False, True]:
            group = [r for r in candidates if any(r[tag] for tag in BEHAVIORS)==with_flag]
            if group:
                chosen = min(group, key=lambda r:(scenes[r['scene_id']], r['scene_id'], int(r['episode_id'])))
                selected.append(chosen);scenes[chosen['scene_id']] += 1
    assert len(selected) <= maximum
    return selected


def panel(row, target, folder=None):
    folder = Path(folder) if folder is not None else HERE/'full'/row['case']/'diagnostic'
    with np.load(folder/row['trace'], allow_pickle=False) as data:
        position = data['position_xyz'];metrics=data['metrics'];names=data['metric_fields'].tolist()
        fields = {name:i for i,name in enumerate(names)}
        grid = data['initial_grid'];seen=data['final_seen'];bounds=data['map_bounds_xyz']
        goal=data['goal_position_xyz']
    fig = plt.figure(figsize=(14, 10), constrained_layout=True)
    gs = fig.add_gridspec(3,4,height_ratios=[1.5,1,1])
    ax=fig.add_subplot(gs[0,:2])
    colors=np.ones((*grid.shape,3));colors[grid==1]=[.78,.78,.78];colors[seen.astype(bool)]=[.66,.80,.94]
    ax.imshow(colors, origin='lower', extent=[bounds[0,0],bounds[1,0],bounds[0,2],bounds[1,2]])
    points=position[:,[0,2]]
    segments=np.stack([points[:-1],points[1:]],axis=1)
    collection=LineCollection(segments,cmap='viridis',linewidth=1.5)
    collection.set_array(np.arange(len(segments)));ax.add_collection(collection)
    collisions=metrics[:,fields['collision_step']].astype(bool)
    ax.scatter(points[collisions,0],points[collisions,1],s=5,c='red',alpha=.5)
    ax.scatter(points[0,0],points[0,1],c='green',s=35,label='start')
    ax.scatter(points[-1,0],points[-1,1],c='black',marker='x',s=40,label='end')
    ax.scatter(goal[0],goal[2],c='gold',edgecolors='black',marker='*',s=110,label='goal')
    ax.set_aspect('equal');ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');ax.legend(fontsize=7)
    title='GT XZ projection; red=collision; path=time colour\nblue=seen union including initial view'
    if row['height_range_m']>.3:title+='\nMulti-height: background is initial floor only'
    ax.set_title(title,fontsize=9)
    ax=fig.add_subplot(gs[0,2:]);steps=np.arange(len(position))
    ax.plot(steps,metrics[:,fields['distance_to_goal']],label='geodesic goal distance',c='navy')
    ax.axhline(1,c='green',ls='--',lw=1,label='SR radius1m')
    ax.scatter(steps[collisions],np.zeros(collisions.sum()),s=4,c='red',alpha=.6)
    if row['stop_called']:ax.axvline(row['steps'],c='black',ls=':',label='STOP')
    ax.set_xlabel('Action step');ax.set_ylabel('Goal distance (m)');ax.grid(alpha=.2)
    second=ax.twinx();second.plot(steps,metrics[:,fields['coverage_new_area_m2']],c='orange',alpha=.7,label='new observed area')
    second.set_ylabel('New observed area (m2)',color='darkorange');ax.legend(fontsize=7,loc='upper right')
    indices={0,row['steps']//4,row['steps']//2,3*row['steps']//4,row['steps'],int(np.argmin(metrics[:,fields['distance_to_goal']]))}
    if row['first_near_step'] is not None:indices.add(row['first_near_step'])
    if row['closed_loops']:
        indices.update([row['closed_loops'][0]['start'],row['closed_loops'][0]['end']])
    # Always retain start, minimum-distance and terminal frames, then spread extras.
    essential=[0,int(np.argmin(metrics[:,fields['distance_to_goal']])),row['steps']]
    indices=list(dict.fromkeys(essential+sorted(indices)))[:7]
    video=folder/row['video'];reader=imageio.get_reader(str(video))
    pictures=[('Fixed goal image',np.asarray(Image.open(video.with_suffix('.goal.png'))))]
    try:
        for index in indices:
            jpeg=video.with_name(str(row['episode_id'])+'.rgb_%03d.jpg'%index)
            rgb=np.asarray(Image.open(jpeg)) if jpeg.exists() else reader.get_data(index)[:128,128:256]
            pictures.append(('t=%d d=%.2fm'%(index,metrics[index,fields['distance_to_goal']]),rgb))
    finally:
        reader.close()
    for i,(title,image) in enumerate(pictures):
        ax=fig.add_subplot(gs[1+i//4,i%4]);ax.imshow(image);ax.set_title(title,fontsize=9);ax.axis('off')
    fig.suptitle('%s | %s task%s | %s\nsteps=%d min_d=%.3fm final_d=%.3fm exact_reference_pose=%s'%(
        row['case'],Path(row['scene_id']).stem,row['episode_id'],row['observed_stage'],row['steps'],
        row['minimum_distance'],row['final_distance'],row['reference_pose_hash_equal']),fontsize=11)
    fig.savefig(target,dpi=140);plt.close(fig)


def table(headers, rows):
    return '<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'


def main():
    report=json.loads((OUT/'analysis.json').read_text())
    episodes=json.loads((OUT/'episodes.json').read_text())
    review=OUT/'review';assets=review/'assets';assets.mkdir(parents=True,exist_ok=True)
    notes_path=OUT/'ai_case_notes.json'
    ai_notes=json.loads(notes_path.read_text())['cases'] if notes_path.exists() else {}
    selected=select_cases(episodes)
    selected_keys={(r['case'],r['scene_id'],r['episode_id']) for r in selected}
    for row in episodes:
        stem=row['case']+'_'+Path(row['scene_id']).stem+'_'+row['episode_id']
        if stem in ai_notes and (row['case'],row['scene_id'],row['episode_id']) not in selected_keys:
            assert row['video'], stem
            selected.append(row)
            selected_keys.add((row['case'],row['scene_id'],row['episode_id']))
    previous={}
    if (review/'human_review.csv').exists():
        with (review/'human_review.csv').open() as stream:
            previous={(r['case'],r['scene_id'],r['episode_id']):r for r in csv.DictReader(stream)}
    cards=[];review_rows=[]
    for i,row in enumerate(selected):
        stem=row['case']+'_'+Path(row['scene_id']).stem+'_'+row['episode_id']
        png=assets/(stem+'.png')
        if not png.exists():panel(row,png)
        source=HERE/'full'/row['case']/'diagnostic'/row['video']
        destination=assets/(stem+'.mp4')
        if not destination.exists():shutil.copy2(source,destination)
        flags=[text for tag,text in BEHAVIORS.items() if row[tag]]
        title=LABELS[row['case']]+' / '+Path(row['scene_id']).stem+' / '+row['episode_id']
        note=STAGES[row['observed_stage']]+'；'+('、'.join(flags) if flags else '无预设行为候选')
        fraction=row.get('coverage_projected_nonvalid_fraction')
        if fraction:
            note+='；静态2D栅格中%.1f%%位置落在非可通行格（栅格代理限制，非真实navmesh不可达）'%(100*fraction)
        ai_note=ai_notes.get(stem,{}).get('review','')
        cards.append('<article data-model="%s"><h3>%s</h3><p>%s</p><p>自动阶段/行为证据；不是人工因果真值。原轨迹哈希一致：%s</p><a href="assets/%s.png"><img loading="lazy" src="assets/%s.png"></a><video controls preload="none" src="assets/%s.mp4"></video></article>'%(
            html.escape(row['case']),html.escape(title),html.escape(note),row['reference_pose_hash_equal'],stem,stem,stem))
        if ai_note:
            cards[-1]=cards[-1].replace('</article>','<p class="note">AI证据复核（非人工真值）：'+html.escape(ai_note)+'</p></article>')
        contacts=ai_notes.get(stem,{}).get('contact_sheets',[])
        if contacts:
            thumbnails=[]
            for name in contacts:
                assert Path(name).name==name
                shutil.copy2(HERE/'inspection_previews'/name,assets/name)
                thumbnails.append('<a href="assets/%s"><img loading="lazy" src="assets/%s"></a>'%(name,name))
            metadata=HERE/'inspection_previews'/(stem+'_contact.json')
            shutil.copy2(metadata,assets/metadata.name)
            cards[-1]=cards[-1].replace('</article>','<details><summary>完整视频的均匀抽帧与目标邻域密集抽帧（非逐帧人审）</summary>'+''.join(thumbnails)+'</details></article>')
        review_row=dict(case=row['case'],scene_id=row['scene_id'],episode_id=row['episode_id'],
            observed_stage=row['observed_stage'],automatic_behavior_flags='|'.join(flags),
            evidence_panel='assets/'+stem+'.png',video='assets/'+stem+'.mp4',
            ai_review_notes=ai_note,human_primary_cause='',human_secondary_causes='',human_review_notes='')
        prior=previous.get((row['case'],row['scene_id'],row['episode_id']),{})
        for field in ['human_primary_cause','human_secondary_causes','human_review_notes']:
            review_row[field]=prior.get(field,'')
        review_rows.append(review_row)
        print('review panel',i+1,'/',len(selected),stem,flush=True)
    with (review/'human_review.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(review_rows[0]));writer.writeheader();writer.writerows(review_rows)
    (review/'selection.json').write_text(json.dumps([{'case':r['case'],'scene_id':r['scene_id'],'episode_id':r['episode_id']} for r in selected],indent=2)+'\n')
    css='body{font:16px system-ui;max-width:1200px;margin:30px auto;padding:0 20px;color:#20252b}table{border-collapse:collapse;width:100%;margin:20px 0}td,th{padding:9px;border:1px solid #ccd3da;text-align:left}th{background:#eef3f7}article{padding:20px 0;border-bottom:2px solid #ccd3da}img{max-width:100%}video{max-width:100%;width:600px}.note{background:#fff4d4;padding:14px}code{background:#edf0f3;padding:2px}'
    viewer='<html lang="zh"><meta charset="utf-8"><title>SIGN失败证据浏览</title><style>'+css+'</style><h1>SIGN失败证据与成功对照</h1><p class="note">这是按自动阶段/行为挑选的诊断案例，不是随机样本，不用此页案例比例估计全体验证的原因占比。人工标签目前留空，AI说明与人工真值分开。</p><p><a href="../index.html">返回总体报告</a> · <a href="human_review.csv">人审表CSV</a></p><label>模型：<select id="model"><option value="">全部</option>'+''.join('<option>'+c+'</option>' for c in LABELS)+'</select></label>'+''.join(cards)+'<script>document.getElementById("model").onchange=function(){document.querySelectorAll("article").forEach(a=>a.hidden=this.value&&a.dataset.model!==this.value)}</script></html>'
    (review/'index.html').write_text(viewer)
    stage_rows=[];opportunities=[];sensitivity=[];positive_controls=[];scene_rows=[];projection_rows=[]
    for case,summary in report['cases'].items():
        failures=summary['failures']
        opportunities.append([LABELS[case],failures,summary['failures_ever_near'],
            '%.2fpp'%(100*summary['failures_ever_near']/4200),summary['failures_near_and_view_aligned'],
            '%d/4200'%summary['reference_pose_matches']])
        for profile,values in summary['sensitivity'].items():
            sensitivity.append([LABELS[case],profile]+['%d (%.2f%%)'%(values['failed'][tag],100*values['failed'][tag]/failures) for tag in BEHAVIORS])
        for tag,label in BEHAVIORS.items():
            values=summary['sensitivity']['base']
            positive_controls.append([LABELS[case],label,
                '%d/%d (%.2f%%)'%(values['failed'][tag],failures,100*values['failed'][tag]/failures),
                '%d/%d (%.2f%%)'%(values['succeeded'][tag],4200-failures,100*values['succeeded'][tag]/(4200-failures))])
        for scene,values in summary['by_scene'].items():
            scene_rows.append([LABELS[case],scene,values['failures'],values['episodes'],
                               '%.2f%%'%(100*values['failures']/values['episodes'])])
        audit=summary['coverage_raster_projection_audit']
        projection_rows.append([LABELS[case],audit['audit_states'].get('single_saved_grid_assessable',0),
            audit['assessable_failed_with_any_nonvalid_projection'],
            audit['low_gain_loop_candidates_with_all_projected_states_valid'],
            audit['low_gain_loop_candidates_with_any_nonvalid_projection'],
            audit['low_gain_loop_candidates_with_unknown_height_maps']])
    for stage,label in STAGES.items():
        if stage=='success':continue
        stage_rows.append([label]+['%d (%.2f%%)'%(
            report['cases'][case]['observed_stages'].get(stage,0),
            100*report['cases'][case]['observed_stages'].get(stage,0)/report['cases'][case]['failures'])
            for case in LABELS])
    chart=OUT/'stage_distribution.png'
    fig,ax=plt.subplots(figsize=(12,5),constrained_layout=True)
    left=np.zeros(3);colors=plt.cm.Set2(np.linspace(0,1,len(STAGES)-1))
    for color,stage in zip(colors,[s for s in STAGES if s!='success']):
        values=np.array([100*report['cases'][c]['observed_stages'].get(stage,0)/report['cases'][c]['failures'] for c in LABELS])
        ax.barh(list(LABELS),values,left=left,label=stage,color=color);left+=values
    ax.set_xlabel('Percent of failed episodes');ax.set_xlim(0,100);ax.legend(fontsize=7,loc='lower center',bbox_to_anchor=(.5,1.02),ncol=2)
    fig.savefig(chart,dpi=160);fig.savefig(chart.with_suffix('.pdf'));plt.close(fig)
    content='<html lang="zh"><meta charset="utf-8"><title>SIGN全量失败诊断</title><style>'+css+'</style><h1>SIGN Gibson全量失败诊断</h1>'
    content+='<p class="note">同任务/目标图/起点、原native策略与6环境/500步/seed100/hash0，三组各4200。训练预算不同，不能据此确认奖励的因果收益。真实终止阶段、非互斥行为候选、语义因果解释分开。</p>'
    content+='<p><a href="review/index.html">逐案例图像与完整视频</a> · <a href="episodes.csv">12600条明细CSV</a> · <a href="failed_episodes.csv">全部失败与空白主因CSV</a> · <a href="analysis.json">统计与阈值敏感性JSON</a> · <a href="review/human_review.csv">空白人审表</a></p>'
    content+='<h2>一、可直接核实的结束阶段</h2><p>单元格为失败条数与占该模型全部失败的比例；不是因果病因比例。</p>'+table(['观测阶段']+[LABELS[c]+' / 失败'+str(report['cases'][c]['failures']) for c in LABELS],stage_rows)+'<img src="stage_distribution.png">'
    content+='<h2>二、停止判断机会与原轨迹一致性</h2>'+table(['模型','失败数','失败中曾进入1m','完美GT停止判断的SR上界增量','曾近且目标视角≤25°','原轨迹哈希完全一致'],opportunities)
    content+='<p>上界只表示在原轨迹首次进入成功半径时若有完美GT STOP，可挽回多少失败；不是实际VLM、目标识别器或Agent的预期提升。GT距离/地图仅用于离线诊断，不能当部署输入。朝向25°是附加诊断，不改变原SR判据。</p>'
    content+='<h2>三、非互斥行为证据与敏感性</h2>'+table(['模型','阈值档位']+list(BEHAVIORS.values()),sensitivity)
    content+='<p>受阻依据请求前进却缺少实际位移，并检查连续性。原地旋转单列。闭环需要3D位置与朝向闭合、有真实路径长度和空间跨度、覆盖新增较低；仍只是重复搜索候选，共同通路/必要返回可能合理。不同候选可重叠，不相加成100%。成功轨迹也可能出现同样行为，需结合发生时间与视频判断。</p>'
    content+='<h3>成功对照中的同类行为（base阈值）</h3>'+table(['模型','行为候选','失败轨迹发生率','成功轨迹发生率'],positive_controls)
    content+='<p>这里比较的是P(候选行为|失败)与P(候选行为|成功)，不是“该行为造成失败的概率”。低新增闭环也可能发生在合理返回或临近目标确认阶段。</p>'
    content+='<h3>覆盖代理的额外质量审计</h3>'+table(['模型','可审计单地图失败','其中存在非可通行投影','闭环候选：全程投影有效','闭环候选：有非可通行投影','闭环候选：中间高度图未知'],projection_rows)
    content+='<p>保持原0.1m/3m/90°统计，不改变训练奖励或预先声明的候选规则。额外检查保存的地图不变且高度变化≤一个像素的轨迹，使用原Habitat to_grid口径投影位置。二维栅格边缘/障碍格与真实navmesh可通行性并非等价。Habitat fog_of_war从当前格发射视线，若当前格为无效格，所有射线在起点就退出；这可解释部分零增量，不是模型没有看见任何新内容的证明。少量边缘格不证明整个面积指标失效，面积不增也不能单独证明没有新视觉信息。多高度中间地图未保存时明确未知。这项补充质量审计是在采集中发现个例后新增，未改预先固定的行为阈值；它本身不是预注册分析。</p>'
    content+='<details><summary>各场景完整分层（各300任务）</summary>'+table(['模型','场景','失败数','任务数','失败率'],scene_rows)+'</details>'
    interpretation=OUT/'interpretation.html'
    if interpretation.exists():
        content+='<h2>证据复核后的具体结论</h2>'+interpretation.read_text()
    content+='<h2>四、证据限制及后续Agent设计</h2><p>主因标签与人工真值尚空。单种子、不同训练步数、目的性抽查案例均不支持总体因果/显著性声明。旧参考哈希不一致的轨迹需单列，不能强称精确重放。优先根据全量阶段和视频证据决定是目标确认/STOP复核、局部解困、外部搜索记忆或重规划；本轮未实施任何Agent或干预。</p>'
    content+='<p>目标图在左、实际观测在右；每个视频保留全部动作帧，10fps仅为播放速度。多楼层案例地图为XZ投影，背景是初始层，不能从投影推断穿墙。原代码/权重/协议/规则SHA与PBS资源回执在源资料中。</p></html>'
    (OUT/'index.html').write_text(content)
    (OUT/'report_ready.json').write_text(json.dumps({'cases_packaged_for_review':len(selected),
        'ai_cases_with_explicit_notes':sum(bool(r['ai_review_notes']) for r in review_rows),
        'review_selection_is_not_population_estimator':True,
        'human_labels_filled':sum(bool(r['human_primary_cause']) for r in review_rows),
        'offline_html':True},indent=2)+'\n')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Prepare, freeze, run and summarize the 24-pair relative-search diagnostic."""
import argparse
import hashlib
import json
import os
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE/'results/qwen_diagnostic/pairwise_pilot_20261013'
MODEL=Path('/scratch/e1538633/liuyi/models/Qwen3.5-9B')
CHOICES={'A更少':'A_LESS','B更少':'B_LESS','并列':'TIE','无法判断':'UNKNOWN'}
PROMPT='''Compare two complete trajectories A and B from the SAME ImageNav task, start and goal. Judge ONLY their relative burden of material repeated SEARCH.
Repeated search means searching substantially the same already searched local region, branch, circuit or viewing directions again, with temporal evidence of recurrence. A normal first inspection, its return route, passing a shared junction to explore different branches, and negligible extra checking do not establish material repeated search. New branches or substantially different viewpoints may justify revisiting a location.
Pure trapping, collision, blocked oscillation and escape attempts are execution/recovery behavior. Describe them separately and EXCLUDE them from repeated-search burden unless independent search repetition is supported. Their duration or collision count alone must not determine the preference.
Compare the additional repeated SEARCH supported by the complete history. Do not rank by total episode length, total path length, total collisions, task success, termination, or efficiency in general. A short unsuccessful trajectory may have less repeated search. A longer trajectory may perform useful new exploration. A repeated path alone is insufficient. Do not require proof of exactly zero information gain, but do not invent unseen walls, dead ends, camera content or task outcomes.
Return A_LESS if A has meaningfully less supported repeated search, B_LESS if B has less, TIE if the available evidence supports no meaningful difference, or UNKNOWN if missing/ambiguous evidence prevents a supported comparison. TIE is not a substitute for uncertainty. Do not force a strict order or first assign absolute grades.
Check earlier versus later behavior and distinguish re-search from transit/recovery. Cite the supplied evidence identifiers or actual step intervals. Do not invent counts, durations, full rotations or constant positions. Keep the reason factual and concise.
Return only one JSON object:
{"preference":"A_LESS|B_LESS|TIE|UNKNOWN","evidence_refs":["A:...","B:..."],"reason":"at most 70 English words","recovery_note":"at most 30 English words","uncertainty":"at most 30 English words"}
Use one allowed preference value. Explain both trajectories when evidence permits. UNKNOWN is a valid response. No markdown or extra commentary.
'''

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def now():return datetime.now(timezone.utc).isoformat()
def manifest(root):return json.loads((root/'manifest.json').read_text())

def prepare(root):
    requests=[]
    for pair in manifest(root)['pairs']:
        folder=root/pair['id']
        for condition in ('A0','A1'):
            for swapped in ([False,True] if pair['swap'] else [False]):
                order=['B','A'] if swapped else ['A','B']
                variant='swapped' if swapped else 'normal'
                dest=root/'model_requests'/f'{pair["id"]}_{condition}_{variant}'
                dest.mkdir(parents=True,exist_ok=True)
                images=[]
                if condition=='A0':
                    text=PROMPT+'\nINPUT: complete original waypoint JSON for each trajectory. Positions are post-action map pixels, not meters; commands are normalized [angular_velocity, linear_velocity], not realized displacement. Heading is in radians. Cite references such as A:steps 25-80.\n'
                    for shown,original in zip('AB',order):
                        payload=json.loads((folder/f'{original}_waypoints.json').read_text())
                        text+=f'\nTRAJECTORY {shown}:\n'+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n'
                else:
                    text=PROMPT+'\nINPUT: overview images with shared pixel scale and step color scale, plus mechanically computed facts. The white background does not show walls. Geometric window matches are candidates, NOT behavioral labels or proof of leaving and returning. Read their intervening movement. Complete window summaries are included; the candidate list is selective and its absence proves nothing. Unwrapped angular range/variation does not establish visual search. Cite references such as A:W03 or B:E02.\n'
                    for shown,original in zip('AB',order):
                        packet=json.loads((folder/f'{original}_evidence.json').read_text())
                        text+=f'\nTRAJECTORY {shown} FACTS:\n'+json.dumps(packet,ensure_ascii=False,separators=(',',':'))+'\n'
                        images.append(dict(shown_as=shown,path=str((folder/f'{original}_overview.png').resolve()),sha256=digest(folder/f'{original}_overview.png')))
                request=dest/'request.txt'
                if request.exists() and request.read_text()!=text:raise RuntimeError(f'Existing request differs: {request}')
                request.write_text(text)
                spec=dict(id=dest.name,pair=pair['id'],condition=condition,variant=variant,
                    shown_A_original=order[0],shown_B_original=order[1],images=images,
                    request_sha256=digest(request),source_sha256=pair['source_sha256'])
                dump(dest/'input.json',spec);requests.append(spec)
    dump(root/'requests.json',requests)
    (root/'protocol.md').write_text('''# 成对诊断运行协议

- 24 对目的性选择的开发案例，来自现有同任务组；没有新采集或训练。
- A0：两条原始 JSON。A1：共享比例的两张白底概览图＋程序事实；不发送 RGB/GIF、人工标签、旧 AI/Qwen 回答、任务成功指标。
- 相同英文判断标准，直接输出 A_LESS/B_LESS/TIE/UNKNOWN，不产生单条绝对等级。
- 24×2=48 个正常请求；选定 8 对在两个条件都交换顺序，另16个请求，共64个。
- 人工标签在模型运行前冻结；审核页与模型请求/输出分开。
- 默认每批2个独立的成对请求，减少双份完整 JSON 的显存压力。batch 大小不代表比较组大小。沿用现有分块 prefill；greedy，关闭 thinking，最多512输出token。
- 耗时包括输入处理和生成，不含排队/模型加载；同时保存批次耗时、摊销耗时、token数和峰值显存。格式错误和截断均保留，不自动改写为 UNKNOWN。
- A0/A1 是整体方案对照；A1 同时改变了模态、组织和输入长度，不能单独归因。人工可见 RGB，因此输入缺失造成的 UNKNOWN 另看，不能把它直接视为推理错误。
- 比较是组内相对判断。本轮不由24对稀疏关系补出每个8条组的完整奖励。

## 使用

先在 human_labels.md 填完24行（无法判断也是有效判断），告知 Codex 完成后固定参考并运行：

```bash
/scratch/e1538633/liuyi/envs/sign/bin/python scripts/qwen_pairwise_diagnostic.py freeze
qsub scripts/qwen_pairwise_diagnostic.pbs
```

准备脚本不覆盖人工填写或既有审核页。程序统计不代替依据真实性复核；模型完成后生成单独的 model_review.md。
''')
    print(f'Prepared {len(requests)} requests in {root}',flush=True)

def read_human(path):
    rows={}
    for line in path.read_text().splitlines():
        if not line.startswith('| [pair_'):continue
        cells=[v.strip() for v in line.split('|')[1:-1]]
        key=re.search(r'pair_\d+',cells[0]).group()
        if len(cells)!=6:raise ValueError(f'{key}: expected six columns; avoid | within cells')
        if cells[1] not in CHOICES or not cells[5]:raise ValueError(f'{key}: judgment and reason must be filled')
        if cells[2] and cells[2] not in ('高','中','低'):raise ValueError(f'{key}: confidence must be 高/中/低 or blank')
        if key in rows:raise ValueError(f'Duplicate {key}')
        rows[key]=dict(preference=CHOICES[cells[1]],confidence=cells[2],A_intervals=cells[3],B_intervals=cells[4],reason=cells[5])
    return rows

def freeze(root):
    rows=read_human(root/'human_labels.md')
    assert set(rows)=={p['id'] for p in manifest(root)['pairs']}
    target=root/'human_labels_frozen.json'
    if target.exists():raise RuntimeError('Reference already frozen; preserve it and explicitly version any later revision.')
    (root/'human_labels_frozen.md').write_bytes((root/'human_labels.md').read_bytes())
    dump(target,dict(frozen_at=now(),human_markdown_sha256=digest(root/'human_labels_frozen.md'),manifest_sha256=digest(root/'manifest.json'),requests_sha256=digest(root/'requests.json'),labels=rows))
    print(f'Frozen {len(rows)} direct human judgments',flush=True)

def parse(raw):
    try:
        d=json.loads(raw)
        if d['preference'] not in set(CHOICES.values()):raise ValueError('Invalid preference')
        if not isinstance(d['evidence_refs'],list) or not all(isinstance(v,str) for v in d['evidence_refs']):raise ValueError('Invalid evidence references')
        for key in ('reason','recovery_note','uncertainty'):
            if not isinstance(d[key],str):raise ValueError(f'Invalid {key}')
        if not d['reason'].strip():raise ValueError('Empty reason')
        return d,None
    except (ValueError,KeyError,TypeError) as exc:return None,str(exc)

def canonical(preference,spec):
    if spec['variant']=='swapped':return {'A_LESS':'B_LESS','B_LESS':'A_LESS'}.get(preference,preference)
    return preference

def readable_preference(raw):
    """Read an explicit, unambiguous field without repairing the JSON response."""
    values=set(re.findall(r'"preference"\s*:\s*"(A_LESS|B_LESS|TIE|UNKNOWN)"',raw))
    return next(iter(values)) if len(values)==1 else None

def diagnose(root):
    """Auxiliary decision-only analysis; preserve strict results and human prose."""
    reference=json.loads((root/'human_labels_frozen.json').read_text())
    assert digest(root/'human_labels_frozen.md')==reference['human_markdown_sha256']
    labels=reference['labels'];rows=[]
    for spec in json.loads((root/'requests.json').read_text()):
        folder=root/'model_requests'/spec['id']
        if not (folder/'result.json').exists():continue
        result=json.loads((folder/'result.json').read_text())
        shown=readable_preference((folder/'response.txt').read_text())
        rows.append(dict(id=spec['id'],pair=spec['pair'],condition=spec['condition'],variant=spec['variant'],
            human=labels[spec['pair']]['preference'],shown_preference=shown,
            readable_canonical=canonical(shown,spec),strict_canonical=result['canonical_preference'],
            parse_error=result['parse_error'],hit_output_limit=result['hit_output_limit'],
            amortized_seconds=result['amortized_seconds'],input_tokens=result['input_tokens'],
            raw_response_sha256=digest(folder/'response.txt')))
    summary={}
    for mode in ('A0','A1'):
        all_rows=[r for r in rows if r['condition']==mode]
        normal=[r for r in all_rows if r['variant']=='normal'];lookup={r['pair']:r for r in normal}
        known=[r for r in normal if r['human']!='UNKNOWN']
        swaps=[r for r in all_rows if r['variant']=='swapped' and r['pair'] in lookup]
        readable_swaps=[r for r in swaps if r['readable_canonical'] is not None and lookup[r['pair']]['readable_canonical'] is not None]
        strict_swaps=[r for r in swaps if r['strict_canonical'] is not None and lookup[r['pair']]['strict_canonical'] is not None]
        summary[mode]=dict(normal_requests=len(normal),strict_valid=sum(r['strict_canonical'] is not None for r in normal),
            strict_agreement=sum(r['strict_canonical']==r['human'] for r in known),known_human_pairs=len(known),
            readable_preferences=sum(r['readable_canonical'] is not None for r in normal),
            readable_agreement=sum(r['readable_canonical']==r['human'] for r in known),
            readable_distribution={v:sum(r['readable_canonical']==v for r in normal) for v in ('A_LESS','B_LESS','TIE','UNKNOWN')},
            always_tie_matches=sum(r['human']=='TIE' for r in known),
            strict_swap_valid=len(strict_swaps),strict_swap_consistent=sum(r['strict_canonical']==lookup[r['pair']]['strict_canonical'] for r in strict_swaps),
            readable_swap_valid=len(readable_swaps),readable_swap_consistent=sum(r['readable_canonical']==lookup[r['pair']]['readable_canonical'] for r in readable_swaps),
            mean_amortized_seconds=statistics.mean(r['amortized_seconds'] for r in all_rows) if all_rows else None,
            mean_input_tokens=statistics.mean(r['input_tokens'] for r in all_rows) if all_rows else None)
    dump(root/'decision_diagnostics.json',dict(summary=summary,requests=rows,method='Auxiliary exact-field extraction only: require one distinct allowed quoted preference value. Does not repair JSON, validate reasons, overwrite strict scores, or change human labels. Swap choices are mapped back to the original human A/B identities.'))
    text='# 成对诊断：严格解析与可读判断分开统计\n\n自动生成的辅助统计；不覆盖 comparison.json、原始回答或人工审核。\n\n'
    text+='| 条件 | 完整合法输出 | 严格一致 | 可读字段一致 | 严格交换一致/可比较 | 可读字段交换一致/可比较 | 平均摊销秒/请求 |\n|---|---:|---:|---:|---:|---:|---:|\n'
    for mode,s in summary.items():
        latency='—' if s['mean_amortized_seconds'] is None else f'{s["mean_amortized_seconds"]:.2f}'
        text+=f'| {mode} | {s["strict_valid"]}/{s["normal_requests"]} | {s["strict_agreement"]}/{s["known_human_pairs"]} | {s["readable_agreement"]}/{s["known_human_pairs"]} | {s["strict_swap_consistent"]}/{s["strict_swap_valid"]} | {s["readable_swap_consistent"]}/{s["readable_swap_valid"]} | {latency} |\n'
    text+='\n[逐请求统计与原始回答哈希](decision_diagnostics.json) · [严格结果](comparison.json) · [原始回答审核](model_review.md)\n\n'
    text+='可读字段统计包括完整JSON不合法但有唯一明确 preference 字段的回答；不代表理由完整、真实或支持结论。不能用它替换严格解析成功率。交换一致只衡量展示顺序稳定性，不代表判断正确。样本为目的性选择，且共享任务/轨迹，不是独立测试集。耗时基于实际batch=2的摊销，不等于单请求等待时间。\n'
    (root/'decision_diagnostics.md').write_text(text)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

def run(root,batch_size):
    frozen=json.loads((root/'human_labels_frozen.json').read_text())
    assert digest(root/'human_labels_frozen.md')==frozen['human_markdown_sha256']
    assert digest(root/'manifest.json')==frozen['manifest_sha256']
    assert digest(root/'requests.json')==frozen['requests_sha256']
    import torch
    import transformers
    from transformers import AutoProcessor,Qwen3_5ForConditionalGeneration
    from qwen_chunked_prefill import install_chunked_prefill
    torch.manual_seed(100)
    processor=AutoProcessor.from_pretrained(MODEL,local_files_only=True);processor.tokenizer.padding_side='left'
    model=Qwen3_5ForConditionalGeneration.from_pretrained(MODEL,dtype='auto',device_map='auto',local_files_only=True).eval()
    install_chunked_prefill(model,chunk_size=2048)
    meta=dict(started_at=now(),status='running',model=str(MODEL),batch_size=batch_size,torch=torch.__version__,transformers=transformers.__version__,gpu=torch.cuda.get_device_name(),pbs_job=os.environ.get('PBS_JOBID'),reference_sha256=digest(root/'human_labels_frozen.json'))
    dump(root/'model_run.json',meta)
    eos=model.generation_config.eos_token_id;eos=set(eos if isinstance(eos,list) else [eos])
    try:
        all_specs=json.loads((root/'requests.json').read_text())
        for condition in ('A0','A1'):
            pending=[s for s in all_specs if s['condition']==condition and not (root/'model_requests'/s['id']/'result.json').exists()]
            for offset in range(0,len(pending),batch_size):
                specs=pending[offset:offset+batch_size];chats=[]
                for spec in specs:
                    folder=root/'model_requests'/spec['id'];assert digest(folder/'request.txt')==spec['request_sha256']
                    content=[]
                    for pic in spec['images']:
                        assert digest(Path(pic['path']))==pic['sha256']
                        content.extend([{'type':'text','text':f'Overview of trajectory {pic["shown_as"]}:'},{'type':'image','path':pic['path']}])
                    content.append({'type':'text','text':(folder/'request.txt').read_text()})
                    chats.append([{'role':'user','content':content}])
                torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
                inputs=processor.apply_chat_template(chats,add_generation_prompt=True,enable_thinking=False,tokenize=True,return_dict=True,return_tensors='pt',padding=True).to(model.device)
                torch.cuda.synchronize();prepared=time.perf_counter()
                with torch.inference_mode():generated=model.generate(**inputs,max_new_tokens=512,do_sample=False)
                torch.cuda.synchronize();end=time.perf_counter()
                for i,spec in enumerate(specs):
                    ids=generated[i,inputs['input_ids'].shape[-1]:].tolist();stop=next((j+1 for j,x in enumerate(ids) if x in eos),len(ids));ids=ids[:stop]
                    raw=processor.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False);parsed,error=parse(raw)
                    folder=root/'model_requests'/spec['id'];(folder/'response.txt').write_text(raw)
                    dump(folder/'result.json',dict(parsed=parsed,parse_error=error,canonical_preference=canonical(parsed['preference'],spec) if parsed else None,
                        batch_seconds=end-start,amortized_seconds=(end-start)/len(specs),preprocessing_seconds=prepared-start,generation_seconds=end-prepared,
                        batch_members=[s['id'] for s in specs],input_tokens=int(inputs['attention_mask'][i].sum()),padded_input_tokens=int(inputs['input_ids'].shape[-1]),output_tokens=len(ids),hit_output_limit=len(ids)>=512 and ids[-1] not in eos,peak_gib=torch.cuda.max_memory_allocated()/1024**3,request_sha256=spec['request_sha256']))
                print(f'{condition} {offset+len(specs)}/{len(pending)}: {end-start:.2f}s',flush=True)
                del inputs,generated
        meta['status']='complete'
    except Exception as exc:
        meta.update(status='failed',error=repr(exc));raise
    finally:
        meta['finished_at']=now();dump(root/'model_run.json',meta)
    summarize(root)

def summarize(root):
    labels=json.loads((root/'human_labels_frozen.json').read_text())['labels'];rows=[]
    for spec in json.loads((root/'requests.json').read_text()):
        file=root/'model_requests'/spec['id']/'result.json'
        if file.exists():rows.append({**spec,**json.loads(file.read_text()),'human':labels[spec['pair']]['preference']})
    summaries={}
    for condition in ('A0','A1'):
        normal=[r for r in rows if r['condition']==condition and r['variant']=='normal']
        known=[r for r in normal if r['human']!='UNKNOWN'];strict=[r for r in known if r['human']!='TIE']
        swapped=[r for r in rows if r['condition']==condition and r['variant']=='swapped']
        lookup={r['pair']:r for r in normal}
        valid_swaps=[r for r in swapped if r['pair'] in lookup and r['canonical_preference'] is not None and lookup[r['pair']]['canonical_preference'] is not None]
        timings=[r for r in rows if r['condition']==condition]
        summaries[condition]=dict(normal_requests=len(normal),known_human_pairs=len(known),agreement_with_known_human=sum(r['human']==r['canonical_preference'] for r in known),
            strict_human_pairs=len(strict),correct_strict_direction=sum(r['human']==r['canonical_preference'] for r in strict),
            model_unknown=sum(r['canonical_preference']=='UNKNOWN' for r in normal),invalid=sum(r['canonical_preference'] is None for r in normal),
            human_tie_pairs=sum(r['human']=='TIE' for r in normal),human_unknown_pairs=sum(r['human']=='UNKNOWN' for r in normal),
            valid_swaps=len(valid_swaps),swap_consistent=sum(r['canonical_preference']==lookup[r['pair']]['canonical_preference'] for r in valid_swaps),
            mean_amortized_request_seconds=statistics.mean(r['amortized_seconds'] for r in timings) if timings else None,
            mean_input_tokens=statistics.mean(r['input_tokens'] for r in timings) if timings else None)
    dump(root/'comparison.json',dict(summary=summaries,requests=rows,limits='Development pairs share tasks and trajectories. Correct preferences do not establish factual correctness. UNKNOWN and invalid outputs remain separate. Human reviewers see additional RGB evidence.'))
    if (root/'model_review.md').exists():return
    text='# 模型成对结果：人工参考已冻结\n\n[统计](comparison.json) · [冻结人工判断](human_labels_frozen.md)\n\n请补充每项回答的依据复核：事实是否正确、理由是否真正支持重复搜索的比较。\n\n'
    for pair in manifest(root)['pairs']:
        text+=f'## {pair["id"]}\n\n[轨迹证据]({pair["id"]}/review.md)；人工判断：{labels[pair["id"]]["preference"]}\n\n'
        for row in [r for r in rows if r['pair']==pair['id']]:
            text+=f'### {row["condition"]} / {row["variant"]}\n\n[实际文本](model_requests/{row["id"]}/request.txt) · [图片顺序与输入清单](model_requests/{row["id"]}/input.json) · [原始输出](model_requests/{row["id"]}/response.txt)\n\n'
            text+=f'模型展示 A 对应人工审核 {row["shown_A_original"]}，模型展示 B 对应人工审核 {row["shown_B_original"]}；换算成人工审核顺序后的判断：`{row["canonical_preference"]}`。下方原始回答的 A/B 仍指模型展示顺序。\n\n'
            text+='```json\n'+json.dumps(row['parsed'],ensure_ascii=False,indent=2)+'\n```\n\n'
            text+='- 依据事实正确：\n- 依据支持比较结论：\n- 备注：\n\n'
    (root/'model_review.md').write_text(text)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','freeze','run','summarize','diagnose']);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--batch-size',type=int,default=2);args=p.parse_args()
    if args.batch_size<1:raise ValueError('batch-size must be positive')
    if args.action=='run':run(args.root,args.batch_size)
    else:globals()[args.action](args.root)

if __name__=='__main__':main()

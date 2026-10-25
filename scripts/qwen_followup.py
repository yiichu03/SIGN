#!/usr/bin/env python3
"""Corrected JSON, clarified criteria, and eight independent prompts per batch."""

import argparse
import csv
import hashlib
import json
import os
import shutil
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from prepare_qwen_review import build_prompt
from prepare_qwen_v2 import build_prompt2, find_cases

ROOT = Path('/scratch/e1538633/liuyi/SIGN/results/qwen_diagnostic/graded60')
MODEL = Path('/scratch/e1538633/liuyi/models/Qwen3.5-9B')
MODES = ('image_only', 'json_only', 'image_json')
TITLES = {'image_only': '仅 PNG', 'json_only': '仅 JSON', 'image_json': 'PNG + JSON'}
PROTOCOLS = {2: 'action_fix_original_prompt', 3: 'clarified_single', 4: 'clarified_batch8'}
OLD_ORDER = '[linear_velocity, angular_velocity], normalized SIGN commands'
NEW_ORDER = '[angular_velocity, linear_velocity], normalized SIGN commands'
ARCHIVE = 'archive_before_action_fix'
CRITERIA = '''请判断整条 episode 是否存在值得关注的冗余探索行为，并区分冗余探索与重复路径。
分级：无或只有可忽略的冗余探索行为；有冗余探索行为；有明显的冗余探索行为；不确定是否有冗余探索行为。
“有”需要具体行为证据支持；“明显有”指较持续或多次反复、对整段过程影响较大的冗余现象。不要只因存在细微调整就判“有”。
允许正常探索中的必要转向、观察、避障、退出死胡同和前往新区域的折返。短暂同坐标、多步转向、一次回访或路径交叉，本身不足以证明冗余。重复路径指再次经过走过的路段，包括反向经过；它不一定构成冗余探索。
先结合前后过程描述可观察到的行为，再说明为何支持判断。改变朝向可能带来新观察；缺少目标图和 RGB 时，不要直接断言“没有获得新信息”。整数地图坐标相同不严格等于真实位置完全不变，朝向角跨越 0 与 2π 时也不代表额外转了一圈。
局部卡住、连续碰撞或反复脱困应在依据中单独说明，不自动等同于重复搜索。仅凭轨迹与坐标不能确认墙体或死胡同；无法区分合理探索与冗余时，请回答不确定，不要强行归为有或无。
请严格用中文回答四行：
冗余探索程度：无或只有可忽略的冗余探索行为 / 有冗余探索行为 / 有明显的冗余探索行为 / 不确定是否有冗余探索行为
大致step区间：有或明显有时给出支持判断的区间，否则写无或不确定
重复路径：有 / 无 / 无法判断
依据：先给具体行为事实，再解释判断；区分重复搜索、正常观察或折返、局部卡住或脱困。简短回答。'''


def dump(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def file_for(folder, kind, mode, version):
    return folder / f'{kind}_{mode}{version}.{"json" if kind == "timing" else "txt"}'


def completed(folder, mode, version):
    response = file_for(folder, 'response', mode, version)
    timing = file_for(folder, 'timing', mode, version)
    if not response.exists() or not timing.exists():
        return False
    if version == 2 and mode == 'image_only':
        return True
    return json.loads(timing.read_text()).get('protocol') == PROTOCOLS[version]


def human_tail(path, heading='## 人工复核'):
    if not path.exists():
        return ''
    text = path.read_text(encoding='utf-8')
    return text[text.index(heading):] if heading in text else ''


def new_prompt(payload, mode):
    introduction = (build_prompt(payload, mode) if mode == 'json_only'
                    else build_prompt2(payload, mode)).split('\n', 1)[0]
    prompt = introduction + '\n' + CRITERIA
    if mode != 'image_only':
        prompt += '\n\nwaypoint JSON:\n' + json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    return prompt


def write_report(root, folder, version):
    target = folder / f'review{version}.md'
    original_human = human_tail(folder / 'review2.md')
    if version == 2:
        annotations = original_human
    else:
        annotations = human_tail(target, '## 本轮人工复核') or (
            '## 本轮人工复核\n\n'
            '| 输入条件 | 程度判断是否合理 | 依据是否真实且支持结论 | step 区间与备注 |\n'
            '| --- | --- | --- | --- |\n'
            '| 仅 PNG |  |  |  |\n| 仅 JSON |  |  |  |\n| PNG + JSON |  |  |  |\n\n综合备注：\n'
        )
    payload = json.loads((folder / 'waypoints_corrected.json').read_text())
    descriptions = {
        2: '动作字段说明已纠正；JSON 两组重跑，提示词其余部分不变；仅 PNG 复用原 v2。',
        3: '修正后的 JSON；明确后的四级判断标准；每次独立处理一条轨迹。',
        4: '输入与 review3 完全相同；每批最多 8 个独立 prompt，逐条返回回答。',
    }
    text = (f'# {folder.parent.name} / {folder.name} — review{version}\n\n'
            f'- 场景：`{payload["scene_id"]}`；episode ID：`{payload["episode_id"]}`\n'
            f'- 模型：`Qwen/Qwen3.5-9B`；{descriptions[version]}\n'
            '- 实际图片：[trajectory2.png](trajectory2.png)；修正版数据：'
            '[waypoints_corrected.json](waypoints_corrected.json)\n'
            '- 对照：[review2](review2.md) / [review3](review3.md) / [review4](review4.md)\n\n'
            '![模型输入轨迹图](trajectory2.png)\n\n')
    if version == 2:
        archive = f'../../{ARCHIVE}/{folder.parent.name}/{folder.name}/review2.md'
        text += f'[修正前的完整 v2 报告及人工备注]({archive})\n\n'
    for mode in MODES:
        request = file_for(folder, 'request', mode, version)
        text += f'## {TITLES[mode]}\n\n实际输入：[{request.name}]({request.name})'
        if mode != 'json_only':
            text += '、[trajectory2.png](trajectory2.png)'
        if completed(folder, mode, version):
            timing = json.loads(file_for(folder, 'timing', mode, version).read_text())
            response = file_for(folder, 'response', mode, version)
            if version == 4:
                latency = (f'批次总耗时 {timing["batch_seconds"]:.2f} s；'
                           f'实际 {timing["batch_size"]} 条；摊销 {timing["amortized_seconds"]:.2f} s/条'
                           '（摊销值不是单条等待时间）')
            else:
                latency = f'{timing["inference_seconds"]:.2f} s'
                if version == 2 and mode == 'image_only':
                    latency += '（复用原 v2）'
            text += f'；{latency}\n\n[原始输出]({response.name})\n\n```text\n{response.read_text()}\n```\n\n'
            if timing.get('hit_output_limit'):
                text += '**输出完整性：达到 512 token 输出上限，依据可能截断；原始输出保留。**\n\n'
        else:
            text += '\n\n（待运行 Qwen）\n\n'
    text += '## 人工审核动画\n\n仅供人工查看，未发送给模型。\n\n![动态轨迹](trajectory.gif)\n\n'
    if version != 2:
        reference = original_human.replace('## 人工复核', '## 既有人工判断（来自 review2）', 1)
        text += reference + '\n\n'
    else:
        text += '以下人工复核内容沿用您原有记录，未改写：\n\n'
    temporary = target.with_name(target.name + '.tmp')
    temporary.write_text(text + annotations, encoding='utf-8')
    temporary.replace(target)


def write_index(root, cases, version):
    lines = [f'# 实验 {version-1}：{PROTOCOLS[version]}', '',
             '[耗时汇总](timing_summary.csv)（随实验完成更新）', '',
             '| 难度 | 序列 | 三组就绪数 | 审核 |', '| --- | --- | ---: | --- |']
    for folder in cases:
        n = sum(completed(folder, mode, version) for mode in MODES)
        relative = folder.relative_to(root).as_posix()
        lines.append(f'| {folder.parent.name} | {folder.name} | {n}/3 | [review{version}]({relative}/review{version}.md) |')
    (root / f'index{version}.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def prepare(root):
    cases = find_cases(root, 60)
    archive = root / ARCHIVE
    marker = archive / 'manifest.json'
    if not marker.exists():
        if archive.exists():
            raise RuntimeError('Incomplete archive: inspect before preparing again')
        archive.mkdir()
        hashes = {}
        for folder in cases:
            dest = archive / folder.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(folder, dest)
            for path in folder.iterdir():
                if path.is_file():
                    hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        for name in ('index.md', 'index2.md', 'run_metadata.json', 'run_metadata2.json'):
            if (root / name).exists():
                shutil.copy2(root / name, archive / name)
        dump(marker, {'created_at': datetime.now(timezone.utc).isoformat(), 'sha256': hashes})
    for folder in cases:
        payload = json.loads((folder / 'waypoints.json').read_text())
        assert payload['action_order'] in (OLD_ORDER, NEW_ORDER)
        payload['action_order'] = NEW_ORDER
        dump(folder / 'waypoints_corrected.json', payload)
        archived = archive / folder.relative_to(root)
        for mode in ('json_only', 'image_json'):
            old_name = 'request_json_only.txt' if mode == 'json_only' else 'request_image_json2.txt'
            previous = (archived / old_name).read_text(encoding='utf-8')
            assert previous.count(OLD_ORDER) == 1
            file_for(folder, 'request', mode, 2).write_text(previous.replace(OLD_ORDER, NEW_ORDER), encoding='utf-8')
        for mode in MODES:
            prompt = new_prompt(payload, mode)
            for version in (3, 4):
                file_for(folder, 'request', mode, version).write_text(prompt, encoding='utf-8')
        for version in (2, 3, 4):
            write_report(root, folder, version)
    for version in (2, 3, 4):
        write_index(root, cases, version)
    print('Prepared 60 cases; original files archived; human annotations retained.', flush=True)


def summarize(root):
    # Several independent PBS jobs may finish close together; serialize summaries.
    import fcntl
    with (root / '.timing_summary.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cases = find_cases(root, 60)
        rows = []
        for version in (2, 3, 4):
            for mode in MODES:
                timings = [json.loads(file_for(f, 'timing', mode, version).read_text())
                           for f in cases if completed(f, mode, version)]
                if not timings:
                    continue
                batches = {}
                for t in timings:
                    key = t.get('batch_id', str(len(batches)))
                    batches[key] = t
                latencies = [t.get('batch_seconds', t.get('inference_seconds')) for t in batches.values()]
                ordered = sorted(latencies)
                p95 = ordered[max(0, __import__('math').ceil(.95 * len(ordered)) - 1)]
                elapsed = sum(latencies)
                rows.append(dict(
                    experiment=version-1, protocol=PROTOCOLS[version], modality=mode,
                    source='reused_v2' if version == 2 and mode == 'image_only' else 'new',
                    episodes=len(timings), batches=len(batches),
                    requested_batch_size=8 if version == 4 else 1,
                    mean_request_or_batch_seconds=statistics.mean(latencies),
                    median_request_or_batch_seconds=statistics.median(latencies),
                    p95_request_or_batch_seconds=p95,
                    total_inference_seconds=elapsed, amortized_seconds_per_episode=elapsed/len(timings),
                    episodes_per_second=len(timings)/elapsed,
                    mean_input_tokens=statistics.mean(t['input_tokens'] for t in timings),
                    mean_output_tokens=statistics.mean(t['output_tokens'] for t in timings),
                    gpu=';'.join(sorted(set(t.get('gpu', 'A40 (historical)') for t in timings))),
                ))
        if rows:
            with (root / 'timing_summary.csv').open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        dump(root / 'timing_summary.json', {
            'updated_at': datetime.now(timezone.utc).isoformat(), 'rows': rows,
            'all_experiments_complete': len(rows)==9 and all(row['episodes']==60 for row in rows),
            'note': 'Timing includes processor/transfer/generate; excludes queue, model load, report export. '
                    'Batch latency is not per-example amortized time. Last four-example batch is included. '
                    'Batch implementation validation is excluded and separately timed in run metadata. '
                    'First measured request is marked in each timing file. '
                    'Historical image-only timing is reused. Raw outputs and token lengths are retained.',
        })


def run(root, version):
    import torch
    import transformers
    from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration

    cases = find_cases(root, 60)
    protocol = PROTOCOLS[version]
    batch_size = 8 if version == 4 else 1
    modes = ('json_only', 'image_json') if version == 2 else MODES
    assert torch.cuda.is_available()
    metadata_file = root / f'run_followup{version}.json'
    setup = dict(protocol=protocol, version=version, batch_size=batch_size,
                 pbs_job_id=os.environ.get('PBS_JOBID'), status='loading')
    dump(metadata_file, setup)
    loaded = time.perf_counter()
    processor = AutoProcessor.from_pretrained(MODEL, local_files_only=True)
    processor.tokenizer.padding_side = 'left'
    model = Qwen3_5ForConditionalGeneration.from_pretrained(
        MODEL, dtype='auto', device_map='auto', local_files_only=True).eval()
    load_seconds = time.perf_counter()-loaded
    validation = None
    if version == 4:
        from qwen_chunked_prefill import install_chunked_prefill, validate_chunked_prefill
        checked = time.perf_counter()
        setup.update(status='validating', load_seconds=load_seconds)
        dump(metadata_file, setup)
        try:
            validation = validate_chunked_prefill(model, processor, cases[0]/'trajectory2.png')
        except Exception as error:
            setup.update(status='failed', error=repr(error))
            dump(metadata_file, setup)
            raise
        validation['seconds'] = time.perf_counter()-checked
        install_chunked_prefill(model, chunk_size=2048)
        print(f'Chunked prefill verified: {validation}', flush=True)
    metadata = dict(protocol=protocol, version=version, batch_size=batch_size,
                    model=str(MODEL), load_seconds=load_seconds,
                    gpu=torch.cuda.get_device_name(0), torch=torch.__version__,
                    transformers=transformers.__version__, pbs_job_id=os.environ.get('PBS_JOBID'),
                    started_at=datetime.now(timezone.utc).isoformat(), status='running',
                    max_new_tokens=512, do_sample=False, enable_thinking=False,
                    independent_contexts=True, padding_side='left', truncated=False,
                    prefill_chunk_size=2048 if version==4 else None,
                    cuda_allocator_config=os.environ.get('PYTORCH_CUDA_ALLOC_CONF'),
                    attention_backend=model.config.get_text_config()._attn_implementation,
                    preflight_validation=validation)
    metadata_file = root / f'run_followup{version}.json'
    dump(metadata_file, metadata)
    print(json.dumps(metadata), flush=True)
    # Group similarly sized episodes to limit padding; test the longest batch first.
    ordered = sorted(cases, key=lambda f: -len(json.loads((f/'waypoints_corrected.json').read_text())['waypoints']))
    ordinal = 0
    eos = model.generation_config.eos_token_id
    eos = set(eos if isinstance(eos, list) else [eos])
    try:
        # Long combined inputs first in the batch experiment to check actual capacity.
        if version == 4:
            modes = ('image_json', 'json_only', 'image_only')
        for mode in modes:
            for offset in range(0, len(ordered), batch_size):
                folders = ordered[offset:offset+batch_size]
                done = [completed(f, mode, version) for f in folders]
                if all(done):
                    continue
                # A partially written batch is recomputed intact, retaining its batch size.
                conversations = []
                for folder in folders:
                    request = file_for(folder, 'request', mode, version).read_text(encoding='utf-8')
                    content = []
                    if mode != 'json_only':
                        content.append({'type': 'image', 'path': str(folder/'trajectory2.png')})
                    content.append({'type': 'text', 'text': request})
                    conversations.append([{'role': 'user', 'content': content}])
                torch.cuda.synchronize()
                torch.cuda.reset_peak_memory_stats()
                started = time.perf_counter()
                inputs = processor.apply_chat_template(
                    conversations if version == 4 else conversations[0],
                    add_generation_prompt=True, enable_thinking=False,
                    tokenize=True, return_dict=True, return_tensors='pt', padding=True,
                ).to(model.device)
                assert inputs['input_ids'].shape[0] == len(folders)
                torch.cuda.synchronize()
                prepared = time.perf_counter()
                with torch.inference_mode():
                    generated = model.generate(**inputs, max_new_tokens=512, do_sample=False)
                torch.cuda.synchronize()
                ended = time.perf_counter()
                latency = ended-started
                padded_length = inputs['input_ids'].shape[-1]
                batch_id = f'{protocol}:{mode}:{offset//batch_size:03d}'
                peak = torch.cuda.max_memory_allocated()/1024**3
                for i, folder in enumerate(folders):
                    ids = generated[i, padded_length:].tolist()
                    stop = next((j+1 for j, token in enumerate(ids) if token in eos), len(ids))
                    ids = ids[:stop]
                    response = processor.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
                    file_for(folder, 'response', mode, version).write_text(response, encoding='utf-8')
                    timing = dict(protocol=protocol, model='Qwen/Qwen3.5-9B', batch_id=batch_id,
                                  batch_size=len(folders), requested_batch_size=batch_size,
                                  batch_seconds=latency, inference_seconds=latency,
                                  amortized_seconds=latency/len(folders), preprocessing_seconds=prepared-started,
                                  generation_seconds=ended-prepared, input_tokens=int(inputs['attention_mask'][i].sum().item()),
                                  padded_input_tokens=padded_length, output_tokens=len(ids), max_new_tokens=512,
                                  hit_output_limit=stop==512 and ids[-1] not in eos,
                                  image=None if mode=='json_only' else 'trajectory2.png',
                                  request=file_for(folder,'request',mode,version).name,
                                  gpu=metadata['gpu'], peak_allocated_gib=peak,
                                  pbs_job_id=metadata['pbs_job_id'], first_measured_batch=ordinal==0,
                                  attention_backend=metadata['attention_backend'],
                                  prefill_chunk_size=metadata['prefill_chunk_size'],
                                  members=[str(f.relative_to(root)) for f in folders])
                    dump(file_for(folder,'timing',mode,version), timing)
                print(f'{batch_id}: n={len(folders)} tokens={padded_length} time={latency:.2f}s peak={peak:.2f}GiB', flush=True)
                ordinal += 1
                del inputs, generated
                for folder in folders:
                    write_report(root, folder, version)
                write_index(root, cases, version)
        metadata['status'] = 'complete'
    except Exception as error:
        metadata.update(status='failed', error=repr(error))
        raise
    finally:
        metadata['finished_at'] = datetime.now(timezone.utc).isoformat()
        dump(metadata_file, metadata)
        summarize(root)
    print(f'Complete: {protocol}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run', 'summarize'))
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--version', type=int, choices=(2, 3, 4))
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.root)
    elif args.command == 'summarize':
        summarize(args.root)
    else:
        if args.version is None:
            parser.error('--version is required for run')
        run(args.root, args.version)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Ask one local Qwen model about each episode in three aligned input conditions."""

import argparse
import json
import time
from pathlib import Path

import torch
from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration

from prepare_qwen_review import build_prompt


MODALITIES = ("image_only", "json_only", "image_json")
TITLES = {"image_only": "仅俯视图", "json_only": "仅 waypoint JSON", "image_json": "俯视图 + waypoint JSON"}


def write_review(folder, payload, split):
    sections = []
    rows = []
    for modality in MODALITIES:
        title = TITLES[modality]
        timing = json.loads((folder / f"timing_{modality}.json").read_text(encoding="utf-8"))
        response = (folder / f"response_{modality}.txt").read_text(encoding="utf-8")
        rows.append(
            f"| {title} | {timing['inference_seconds']:.2f} s | "
            f"[输入](request_{modality}.txt) | [原始输出](response_{modality}.txt) |"
        )
        sections.append(
            f"### {title}\n\n"
            f"实际输入：[request_{modality}.txt](request_{modality}.txt)"
            + ("、[trajectory.png](trajectory.png)" if modality != "json_only" else "")
            + f"；推理耗时：{timing['inference_seconds']:.2f} s\n\n"
            f"```text\n{response}\n```\n"
        )
    report = (
        f"# {split} / Episode {folder.name} 审核\n\n"
        f"- Habitat episode ID：`{payload['episode_id']}`\n"
        f"- 场景：`{payload['scene_id']}`\n"
        f"- 模型：`Qwen/Qwen3.5-9B`\n"
        f"- 轨迹：[trajectory.png](trajectory.png)；完整记录：[waypoints.json](waypoints.json)\n\n"
        "![带起点、终点、step 和朝向的俯视轨迹](trajectory.png)\n\n"
        "| 输入条件 | 推理耗时 | 实际文本输入 | 模型原始输出 |\n"
        "| --- | ---: | --- | --- |\n"
        + "\n".join(rows)
        + "\n\n## 三组原始回答\n\n"
        + "\n".join(sections)
        + "\n## 人工复核\n\n"
        "| 输入条件 | 冗余探索判断是否合理 | 重复路径判断是否合理 | 我认为的大致 step 区间及依据 |\n"
        "| --- | --- | --- | --- |\n"
        "| 仅俯视图 |  |  |  |\n"
        "| 仅 waypoint JSON |  |  |  |\n"
        "| 俯视图 + waypoint JSON |  |  |  |\n\n"
        "综合备注：\n"
    )
    (folder / "review.md").write_text(report, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--model-dir", type=Path, default=Path("/scratch/e1538633/liuyi/models/Qwen3.5-9B"))
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--expected-count", type=int, default=60)
    args = parser.parse_args()

    root = args.root.resolve()
    cases = [(split.name, folder) for split in sorted(root.glob("val_*")) for folder in sorted(split.glob("episode_*")) if (folder / "waypoints.json").exists() and (folder / "trajectory.png").exists()]
    if len(cases) != args.expected_count:
        raise RuntimeError(f"Expected {args.expected_count} complete episodes, found {len(cases)} under {root}")
    assert torch.cuda.is_available(), "Qwen inference needs a GPU node"

    load_start = time.perf_counter()
    processor = AutoProcessor.from_pretrained(args.model_dir, local_files_only=True)
    model = Qwen3_5ForConditionalGeneration.from_pretrained(
        args.model_dir, dtype="auto", device_map="auto", local_files_only=True
    ).eval()
    load_seconds = time.perf_counter() - load_start
    (root / "run_metadata.json").write_text(
        json.dumps({"model": "Qwen/Qwen3.5-9B", "model_dir": str(args.model_dir), "load_seconds": load_seconds, "case_count": len(cases), "conditions": MODALITIES}, indent=2), encoding="utf-8"
    )

    index = [f"# 分级采集：{len(cases)} 条 ImageNav episode，三种输入条件", "", f"模型加载耗时：{load_seconds:.2f} s。每行三组判断使用同一条序列。", "", "| 难度 | 序列 | 人工审核 |", "| --- | --- | --- |"]
    for split, folder in cases:
        payload = json.loads((folder / "waypoints.json").read_text(encoding="utf-8"))
        for modality in MODALITIES:
            prompt = build_prompt(payload, modality)
            (folder / f"request_{modality}.txt").write_text(prompt, encoding="utf-8")
            if modality == "image_json":
                (folder / "request.txt").write_text(prompt, encoding="utf-8")
            response_path = folder / f"response_{modality}.txt"
            timing_path = folder / f"timing_{modality}.json"
            if response_path.exists() and timing_path.exists():
                continue
            content = []
            if modality != "json_only":
                content.append({"type": "image", "path": str((folder / "trajectory.png").resolve())})
            content.append({"type": "text", "text": prompt})
            start = time.perf_counter()
            inputs = processor.apply_chat_template(
                [{"role": "user", "content": content}],
                add_generation_prompt=True, enable_thinking=False,
                tokenize=True, return_dict=True, return_tensors="pt",
            ).to(model.device)
            torch.cuda.synchronize()
            with torch.inference_mode():
                generated = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False)
            torch.cuda.synchronize()
            latency = time.perf_counter() - start
            new_ids = generated[0, inputs["input_ids"].shape[-1]:]
            response_path.write_text(
                processor.decode(new_ids, skip_special_tokens=False, clean_up_tokenization_spaces=False),
                encoding="utf-8",
            )
            timing_path.write_text(
                json.dumps({"model": "Qwen/Qwen3.5-9B", "inference_seconds": latency, "input_tokens": int(inputs["input_ids"].shape[-1]), "output_tokens": int(new_ids.shape[-1]), "max_new_tokens": args.max_new_tokens}, indent=2), encoding="utf-8"
            )
            print(f"{split}/{folder.name} {modality}: {latency:.2f}s", flush=True)
        write_review(folder, payload, split)
        index.append(f"| {split} | {folder.name} | [review.md]({split}/{folder.name}/review.md) |")
        (root / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

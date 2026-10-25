#!/usr/bin/env python3
"""Rerun the two image conditions; keep the original JSON-only inference."""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration

from prepare_qwen_v2 import NEW_CONDITIONS, find_cases, write_index2, write_review2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--model-dir", type=Path, default=Path("/scratch/e1538633/liuyi/models/Qwen3.5-9B"))
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--expected-count", type=int, default=60)
    args = parser.parse_args()
    root = args.root.resolve()
    cases = find_cases(root, args.expected_count)
    for folder in cases:
        for name in ("trajectory2.png", "request_image_only2.txt", "request_image_json2.txt",
                     "request_json_only.txt", "response_json_only.txt", "timing_json_only.json"):
            if not (folder / name).is_file():
                raise FileNotFoundError(folder / name)
    assert torch.cuda.is_available(), "Qwen inference needs a GPU node"

    load_start = time.perf_counter()
    processor = AutoProcessor.from_pretrained(args.model_dir, local_files_only=True)
    model = Qwen3_5ForConditionalGeneration.from_pretrained(
        args.model_dir, dtype="auto", device_map="auto", local_files_only=True
    ).eval()
    metadata = {
        "model": "Qwen/Qwen3.5-9B", "model_dir": str(args.model_dir),
        "load_seconds": time.perf_counter() - load_start,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "pbs_job_id": os.environ.get("PBS_JOBID"),
        "case_count": len(cases), "new_conditions": NEW_CONDITIONS,
        "reused_condition": "json_only", "image": "trajectory2.png",
        "renderer": "preview_trajectory_layouts.white_gradient",
        "do_sample": False, "enable_thinking": False,
        "max_new_tokens": args.max_new_tokens, "status": "running",
    }
    metadata_path = root / "run_metadata2.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Loaded model in {metadata['load_seconds']:.2f}s", flush=True)

    for folder in cases:
        updated = False
        for modality in NEW_CONDITIONS:
            response_path = folder / f"response_{modality}2.txt"
            timing_path = folder / f"timing_{modality}2.json"
            if response_path.exists() and timing_path.exists():
                continue
            # Read the saved request verbatim; each call starts a fresh conversation.
            request_path = folder / f"request_{modality}2.txt"
            prompt = request_path.read_text(encoding="utf-8")
            content = [
                {"type": "image", "path": str(folder / "trajectory2.png")},
                {"type": "text", "text": prompt},
            ]
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
            timing_path.write_text(json.dumps({
                "model": "Qwen/Qwen3.5-9B", "inference_seconds": latency,
                "input_tokens": int(inputs["input_ids"].shape[-1]),
                "output_tokens": int(new_ids.shape[-1]), "max_new_tokens": args.max_new_tokens,
                "image": "trajectory2.png", "request": request_path.name,
                "pbs_job_id": os.environ.get("PBS_JOBID"),
            }, indent=2), encoding="utf-8")
            print(f"{folder.relative_to(root)} {modality}: {latency:.2f}s", flush=True)
            updated = True
            del inputs, generated, new_ids
        if updated or not (folder / "review2.md").exists():
            write_review2(folder)
        write_index2(root, cases)

    metadata.update(status="complete", finished_at=datetime.now(timezone.utc).isoformat())
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Complete: {len(cases)} episodes; two v2 conditions + reused JSON-only", flush=True)


if __name__ == "__main__":
    main()

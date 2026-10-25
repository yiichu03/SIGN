#!/usr/bin/env python3
"""Run one offline Qwen3.5-9B image + trajectory review on a GPU node."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import torch
from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_dir", type=Path)
    parser.add_argument(
        "--model-dir", type=Path,
        default=Path("/scratch/e1538633/liuyi/models/Qwen3.5-9B"),
    )
    parser.add_argument("--max-new-tokens", type=int, default=512)
    args = parser.parse_args()

    folder = args.episode_dir.resolve()
    prompt = (folder / "request.txt").read_text(encoding="utf-8")
    image = (folder / "trajectory.png").resolve()
    assert torch.cuda.is_available(), "Qwen inference needs a GPU node"

    load_start = time.perf_counter()
    processor = AutoProcessor.from_pretrained(args.model_dir, local_files_only=True)
    model = Qwen3_5ForConditionalGeneration.from_pretrained(
        args.model_dir, dtype="auto", device_map="auto", local_files_only=True
    ).eval()
    load_seconds = time.perf_counter() - load_start

    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "path": str(image)},
            {"type": "text", "text": prompt},
        ],
    }]
    start = time.perf_counter()
    inputs = processor.apply_chat_template(
        messages, add_generation_prompt=True, enable_thinking=False,
        tokenize=True, return_dict=True, return_tensors="pt",
    ).to(model.device)
    torch.cuda.synchronize()
    with torch.inference_mode():
        generated = model.generate(
            **inputs, max_new_tokens=args.max_new_tokens, do_sample=False
        )
    torch.cuda.synchronize()
    latency = time.perf_counter() - start
    new_ids = generated[0, inputs["input_ids"].shape[-1]:]
    response = processor.decode(
        new_ids, skip_special_tokens=False, clean_up_tokenization_spaces=False
    )
    (folder / "response.txt").write_text(response, encoding="utf-8")
    (folder / "timing.json").write_text(
        json.dumps({
            "model": "Qwen/Qwen3.5-9B",
            "model_dir": str(args.model_dir),
            "load_seconds": load_seconds,
            "inference_seconds": latency,
            "input_tokens": int(inputs["input_ids"].shape[-1]),
            "output_tokens": int(new_ids.shape[-1]),
            "max_new_tokens": args.max_new_tokens,
        }, indent=2), encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, str(Path(__file__).with_name("prepare_qwen_review.py")),
         str(folder), "--latency-seconds", str(latency)],
        check=True,
    )
    print(f"Qwen inference: {latency:.2f}s; response saved to {folder / 'response.txt'}")


if __name__ == "__main__":
    main()

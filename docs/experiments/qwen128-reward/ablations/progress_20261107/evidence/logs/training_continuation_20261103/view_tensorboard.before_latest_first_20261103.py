#!/usr/bin/env python3
"""Keep TensorBoard and its SSH session together; reuse an identical viewer."""
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import urllib.request

HOST = "127.0.0.1"
PORT = int(os.environ.get("SIGN_TENSORBOARD_PORT", "6008"))
if not 1 <= PORT <= 65535:
    raise SystemExit("SIGN_TENSORBOARD_PORT must be between 1 and 65535")
ROOT = "/scratch/e1538633/liuyi"
RUNS = [
    ('coverage256', ROOT + '/SIGN-continue-coverage256/results/continuation_20261103/coverage256/train/tb'),
    ('coverage32', ROOT + '/SIGN-continue-coverage32/results/continuation_20261103/coverage32/train/tb'),
    ('qwen128_beta01', ROOT + '/SIGN-continue-qwen128/results/continuation_20261103/qwen01/train/tb'),
    ('A_qwen128_beta003', ROOT + '/SIGN-continue-ablation/results/continuation_20261103/A/train/tb'),
    ('B_qwen256_beta003', ROOT + '/SIGN-continue-ablation/results/continuation_20261103/B/train/tb'),
    ('C_geometry128', ROOT + '/SIGN-continue-ablation/results/continuation_20261103/C/train_after_latest_eval/tb'),
]
if os.environ.get("SIGN_TENSORBOARD_HISTORY") == "1":
    with open(ROOT + "/logs/training_continuation_20261103/plan.json") as source:
        plan = json.load(source)
    cases = {
        'coverage256': 'coverage256', 'coverage32': 'coverage32',
        'qwen128_beta01': 'qwen01', 'A_qwen128_beta003': 'A',
        'B_qwen256_beta003': 'B', 'C_geometry128': 'C',
    }
    original = [('baseline_frozen/original', ROOT + '/SIGN/results/gibson_frozen_encoder_20261026/train_personal_8env/tb')]
    original.extend((name + '/original', plan[cases[name]]['old_output'] + '/tb')
                    for name, path in RUNS)
    continued = [(name + '/continue_latest', path) for name, path in RUNS]
    stopped = [('C_geometry128/continue_1_stopped', ROOT + '/SIGN-continue-ablation/results/continuation_20261103/C/train/tb')]
    RUNS = original + continued + stopped
SPEC = ",".join(name + ":" + path for name, path in RUNS)
URL = "http://{}:{}".format(HOST, PORT)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
stopped = threading.Event()
child = None

def stop(signum, frame):
    stopped.set()

for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(sig, stop)

def listening():
    with socket.socket() as sock:
        sock.settimeout(2)
        return sock.connect_ex((HOST, PORT)) == 0

def check_existing():
    with opener.open(URL + "/data/logdir", timeout=5) as response:
        actual = json.load(response).get("logdir")
    if actual != SPEC:
        raise RuntimeError("Port {} belongs to a different viewer: {!r}".format(PORT, actual))

try:
    if listening():
        try:
            check_existing()
        except Exception as exc:
            raise SystemExit("Cannot reuse port {}: {}. Existing process was left running.".format(PORT, exc))
        print("Reusing TensorBoard at {} on {}. Keep this SSH terminal open.".format(URL, socket.gethostname()), flush=True)
        while not stopped.wait(10):
            try:
                check_existing()
            except Exception as exc:
                raise SystemExit("The reused TensorBoard stopped responding: {}. Run the same SSH command again.".format(exc))
    else:
        print("Starting TensorBoard at {} on {}. Keep this SSH terminal open.".format(URL, socket.gethostname()), flush=True)
        child = subprocess.Popen([
            ROOT + "/envs/sign-baseline/bin/tensorboard",
            "--logdir_spec", SPEC, "--host", HOST, "--port", str(PORT),
            "--load_fast=false", "--max_reload_threads", "3",
        ], start_new_session=True)
        while not stopped.wait(0.25):
            result = child.poll()
            if result is not None:
                raise SystemExit(result)
finally:
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()

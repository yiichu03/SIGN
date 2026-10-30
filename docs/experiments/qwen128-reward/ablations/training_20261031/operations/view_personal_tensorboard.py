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
PORT = int(os.environ.get("SIGN_TENSORBOARD_PORT", "6006"))
if not 1 <= PORT <= 65535:
    raise SystemExit("SIGN_TENSORBOARD_PORT must be between 1 and 65535")
ROOT = "/scratch/e1538633/liuyi"
RUNS = [
    ("baseline_frozen", ROOT + "/SIGN/results/gibson_frozen_encoder_20261026/train_personal_8env/tb"),
    ("coverage_rollout256", ROOT + "/SIGN-frozen-rollout-coverage/results/gibson_rollout_coverage_20261027/train_personal_8env/tb"),
    ("coverage_settle32", ROOT + "/SIGN-frozen-coverage-settle32/results/gibson_coverage_settle32_20261028/train_personal_8env/tb"),
]
for _, path in RUNS:
    if not os.path.isdir(path):
        raise SystemExit("Missing TensorBoard log directory: " + path)
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

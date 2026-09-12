"""Train a linear head: ridge regression from frozen arm-B states to arm-A states.

Supervision is distillation (arm A vectors as targets on the 75 sentence chunks),
because the corpus has only 2 gold queries -- query-supervised training at
d=2048 would be vacuous. The eval queries are never training inputs.

Usage: train_head.py <run_name> <src_arm_chunks> <tgt_arm_chunks> [--lam L]
Writes results/<run_name>_head.json {W, b, train_cos, lam, src, tgt}.
"""
import json
import sys

import numpy as np

from common import SPIKE_DIR, log, norm

RES = SPIKE_DIR / "results"
run_name = sys.argv[1]
src_arm, tgt_arm = sys.argv[2], sys.argv[3]
lam = float(sys.argv[sys.argv.index("--lam") + 1]) if "--lam" in sys.argv else 1e3

Xs = np.array(json.load(open(RES / f"{src_arm}_chunks.json"))["vecs"])  # n x d
Ys = np.array([norm(v) for v in
               json.load(open(RES / f"{tgt_arm}_chunks.json"))["vecs"]])  # n x t
Xs = Xs / np.linalg.norm(Xs, axis=1, keepdims=True)

n, d = Xs.shape
t = Ys.shape[1]
A = Xs.T @ Xs + lam * np.eye(d)
W = np.linalg.solve(A, Xs.T @ Ys)  # d x t
pred = Xs @ W
pred = pred / np.linalg.norm(pred, axis=1, keepdims=True)
train_cos = float(np.mean(np.sum(pred * Ys, axis=1)))

out = RES / f"{run_name}_head.json"
json.dump({"W": W.tolist(), "b": [0.0] * t, "lam": lam, "src": src_arm,
           "tgt": tgt_arm, "n_train": n, "d_in": d, "d_out": t,
           "train_cos": train_cos}, open(out, "w"))
log(run_name, "head_trained", src=src_arm, tgt=tgt_arm, lam=lam, n=n,
    d_in=d, d_out=t, train_cos=round(train_cos, 4), path=str(out))
print(f"lam={lam} n={n} d={d}->{t} mean_train_cos={train_cos:.4f}")

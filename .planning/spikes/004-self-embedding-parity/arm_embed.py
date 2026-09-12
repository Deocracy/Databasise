"""One embedding arm: load a GGUF with a fixed pooling policy, embed a JSON list of
{texts}, save vectors as JSON. Runs under the GPU lock via run.sh.

Usage: arm_embed.py <run_name> <model_file> <pooling> <prefix> <marker_mode> <in.json> <out.json>
  pooling: native | last
  marker_mode: none | emb   (append the literal [EMB] marker per SCORE-IO-SPEC fallback)
  prefix: '' | 'passage:'   ('passage:' prepends 'Passage: ' to docs, 'Query: ' is handled by caller input)
"""
import json
import sys
import time
from pathlib import Path

from common import MARKER, log

run_name, model_file, pooling, prefix, marker_mode, in_path, out_path = sys.argv[1:8]

import os
models_dir = os.environ.get("MELODYSCRIBE_MODELS", "/tmp/no-models")

from llama_cpp import (Llama, LLAMA_POOLING_TYPE_LAST)

raw = json.loads(open(in_path, encoding="utf-8").read())
if isinstance(raw, dict) and "texts" in raw:
    texts = raw["texts"]
    ids = raw.get("ids", [str(i) for i in range(len(texts))])
else:
    texts = raw
    ids = [str(i) for i in range(len(texts))]


def prep(t):
    if prefix == "passage:":
        t = "Passage: " + t
    if marker_mode == "emb":
        t = t + MARKER
    return t


t0 = time.time()
kwargs = dict(model_path=os.path.join(models_dir, model_file), embedding=True,
              n_ctx=2048, n_gpu_layers=-1, verbose=False)
if pooling == "last":
    kwargs["pooling_type"] = LLAMA_POOLING_TYPE_LAST
m = Llama(**kwargs)
load_s = time.time() - t0
log(run_name, "model_loaded", model=model_file, pooling=pooling,
    effective_pooling=int(m.pooling_type()), n_embd=int(m.n_embd()), load_s=round(load_s, 2))

t0 = time.time()
vecs = m.embed([prep(t) for t in texts])
embed_s = time.time() - t0
log(run_name, "embedded", n=len(texts), prefix=prefix, marker_mode=marker_mode,
    embed_s=round(embed_s, 3), per_text_ms=round(embed_s / max(len(texts), 1) * 1000, 2))

Path(out_path).parent.mkdir(parents=True, exist_ok=True)
json.dump({"model": model_file, "pooling": pooling,           "effective_pooling": int(m.pooling_type()), "n_embd": int(m.n_embd()),
           "prefix": prefix, "marker_mode": marker_mode,
           "vecs": [list(v) for v in vecs],
           "ids": ids},
          open(out_path, "w", encoding="utf-8"))
log(run_name, "saved", path=out_path)

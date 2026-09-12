"""One embedding run: load a GGUF with a fixed pooling policy, embed pre-rendered
texts, save vectors as JSON. Runs under the GPU lock via run.sh. One model per
process (CONVENTIONS.md).

Usage: embed_run.py <run_name> <model_file> <pooling> <in.json> <out.json>
  pooling: native | last
"""
import json
import os
import sys
import time
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
LOGS = SPIKE_DIR / "logs"

run_name, model_file, pooling, in_path, out_path = sys.argv[1:6]


def log(event, **fields):
    import datetime
    LOGS.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "run": run_name, "event": event, **fields}
    with open(LOGS / f"{run_name}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


models_dir = os.environ.get("MELODYSCRIBE_MODELS", "/tmp/no-models")

from llama_cpp import Llama, LLAMA_POOLING_TYPE_LAST

raw = json.loads(open(in_path, encoding="utf-8").read())
texts, ids = raw["texts"], raw["ids"]
assert len(texts) == len(ids) and len(texts) > 0
assert all(isinstance(t, str) and len(t) > 0 for t in texts), "empty text refused"

t0 = time.time()
kwargs = dict(model_path=os.path.join(models_dir, model_file), embedding=True,
              n_ctx=4096, n_gpu_layers=-1, verbose=False)
if pooling == "last":
    kwargs["pooling_type"] = LLAMA_POOLING_TYPE_LAST
m = Llama(**kwargs)
load_s = time.time() - t0
log("model_loaded", model=model_file, pooling=pooling,
    effective_pooling=int(m.pooling_type()), n_embd=int(m.n_embd()),
    load_s=round(load_s, 2))

t0 = time.time()
vecs = m.embed(texts)
embed_s = time.time() - t0
log("embedded", n=len(texts), embed_s=round(embed_s, 3),
    per_text_ms=round(embed_s / len(texts) * 1000, 2))

Path(out_path).parent.mkdir(parents=True, exist_ok=True)
json.dump({"model": model_file, "pooling": pooling,
           "effective_pooling": int(m.pooling_type()), "n_embd": int(m.n_embd()),
           "vecs": [list(v) for v in vecs], "ids": ids},
          open(out_path, "w", encoding="utf-8"))
log("saved", path=out_path)

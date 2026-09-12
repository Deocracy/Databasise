"""B-model edge cases that need a fresh process (empty-B errors poison CUDA state,
so empty is NOT run here; see edge.py part1 B and the README). Usage: edgeB.py <run_name>."""
import gc
import sys

from common import MARKER, log

run_name = sys.argv[1]

import os
models_dir = os.environ.get("MELODYSCRIBE_MODELS", "/tmp/no-models")
from llama_cpp import Llama, LLAMA_POOLING_TYPE_LAST

m = Llama(model_path=os.path.join(models_dir, "MiniCPM5-2B-Q8_0.gguf"),
          embedding=True, pooling_type=LLAMA_POOLING_TYPE_LAST,
          n_ctx=2048, n_gpu_layers=-1, verbose=False)
long_text = "Scott Derrickson directed Doctor Strange. " * 600
toks = m.tokenize(long_text.encode("utf-8"))
v = m.embed([long_text])
log(run_name, "truncation", model="B", ok=True, tokens=len(toks),
    n_ctx=int(m.n_ctx()), dim=len(v[0]))
print(f"trunc B: tokens={len(toks)} n_ctx={m.n_ctx()} ok", flush=True)
tricky = "A note about markers " + MARKER + " inside text."
v1 = m.embed([tricky])
v2 = m.embed([tricky + MARKER])
import math
c = (sum(a * b for a, b in zip(v1[0], v2[0]))
     / math.sqrt(sum(a * a for a in v1[0]) * sum(b * b for b in v2[0])))
log(run_name, "marker_escape", model="B", ok=True,
    cos_with_and_without_trailing=round(c, 4))
print(f"escape B: ok cos={c:.3f}", flush=True)

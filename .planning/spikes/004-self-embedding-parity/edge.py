"""Edge cases (GPU, under lock): empty input, over-ctx truncation, marker escape,
query/doc prefix asymmetry. Usage: edge.py <run_name> <part1|part2>.
part1 loads A then B sequentially (del + gc between: two live Llama instances
crash at interpreter exit with double-free). part2 loads A only."""

import gc
import json
import sys

from common import log

run_name, part = sys.argv[1], sys.argv[2]

import os
models_dir = os.environ.get("MELODYSCRIBE_MODELS", "/tmp/no-models")
from llama_cpp import Llama, LLAMA_POOLING_TYPE_LAST


def load_a():
    return Llama(model_path=os.path.join(models_dir, "Qwen3-Embedding-0.6B-Q8_0.gguf"),
                 embedding=True, n_ctx=2048, n_gpu_layers=-1, verbose=False)


def load_b():
    return Llama(model_path=os.path.join(models_dir, "MiniCPM5-2B-Q8_0.gguf"),
                 embedding=True, pooling_type=LLAMA_POOLING_TYPE_LAST,
                 n_ctx=2048, n_gpu_layers=-1, verbose=False)

# 1. empty section
def one_empty(tag, mk):
    m = mk()
    try:
        v = m.embed([""])
        import math
        n = math.sqrt(sum(x * x for x in v[0]))
        log(run_name, "empty_input", model=tag, ok=True, dim=len(v[0]),
            norm=round(n, 4))
        print(f"empty {tag}: ok dim={len(v[0])} norm={n:.3f}", flush=True)
    except Exception as e:  # noqa: BLE001
        log(run_name, "empty_input", model=tag, ok=False, error=str(e)[:200])
        print(f"empty {tag}: ERROR {str(e)[:120]}", flush=True)
    finally:
        del m
        gc.collect()

# 2. over-context truncation (5k tokens of repeated text, n_ctx=2048)
long_text = "Scott Derrickson directed Doctor Strange. " * 600


def one_trunc(tag, mk):
    m = mk()
    try:
        toks = m.tokenize(long_text.encode("utf-8"))
        v = m.embed([long_text])
        log(run_name, "truncation", model=tag, ok=True,
            tokens=len(toks), n_ctx=int(m.n_ctx()), dim=len(v[0]))
        print(f"trunc {tag}: tokens={len(toks)} n_ctx={m.n_ctx()} ok", flush=True)
    except Exception as e:  # noqa: BLE001
        log(run_name, "truncation", model=tag, ok=False, error=str(e)[:200])
        print(f"trunc {tag}: ERROR {str(e)[:120]}", flush=True)
    finally:
        del m
        gc.collect()

# 3. marker escape: content containing the literal marker
from common import MARKER  # noqa: E402
tricky = "A note about markers " + MARKER + " inside text."


def one_escape(tag, mk):
    m = mk()
    try:
        v1 = m.embed([tricky])
        v2 = m.embed([tricky + MARKER])
        import math
        c = sum(a * b for a, b in zip(v1[0], v2[0]))
        c /= math.sqrt(sum(a * a for a in v1[0]) * sum(b * b for b in v2[0]))
        log(run_name, "marker_escape", model=tag, ok=True,
            cos_with_and_without_trailing=round(c, 4))
        print(f"escape {tag}: ok cos={c:.3f}", flush=True)
    except Exception as e:  # noqa: BLE001
        log(run_name, "marker_escape", model=tag, ok=False, error=str(e)[:200])
        print(f"escape {tag}: ERROR {str(e)[:120]}", flush=True)
    finally:
        del m
        gc.collect()


if part == "part1":
    only = sys.argv[3] if len(sys.argv) > 3 else "AB"
    if "A" in only:
        one_empty("A", load_a)
        one_trunc("A", load_a)
        one_escape("A", load_a)
    if "B" in only:
        one_empty("B", load_b)
        one_trunc("B", load_b)
        one_escape("B", load_b)
    raise SystemExit(0)

if part == "part2":
    A = load_a()
import json as J  # noqa: E402
from pathlib import Path  # noqa: E402
from common import SPIKE_DIR, rank_docs, recall_at_k  # noqa: E402
IN = SPIKE_DIR / "inputs"
docs = J.load(open(IN / "docs.json"))
gold = J.load(open(IN / "queries_gold.json"))
for dp, qp in (("Passage: ", "Query: "), ("", "Query: "), ("Passage: ", "")):
    dv = A.embed([dp + t for t in docs["texts"]])
    qv = A.embed([qp + q["question"] for q in gold])
    dids = docs["ids"]
    rs = []
    for q, v in zip(gold, qv):
        rs.append(recall_at_k(rank_docs(v, list(zip(dids, dv))),
                              q["gold"], 3))
    log(run_name, "prefix_asymmetry", doc_prefix=dp, query_prefix=qp,
        gold_r3=round(sum(rs) / len(rs), 4))
    print(f"prefix doc={dp!r} query={qp!r}: gold r@3={sum(rs)/len(rs):.2f}")

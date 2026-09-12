"""Debug 009b: bisect the -1 (GPU, under flock)."""
from __future__ import annotations
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
from batchserve import raw_decode_rows  # noqa: E402
from llama_cpp import Llama  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
llm = Llama(model_path=os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf"),
            n_gpu_layers=-1, n_ctx=4096, n_batch=2048,
            embedding=True, verbose=False)


def tok(s: str) -> list[int]:
    return llm.tokenize(s.encode(), add_bos=False, special=False)


A = tok("MelodyScribe ingest v0.1. File facts. The cat sat.")
B = tok("MelodyScribe ingest v0.1. File facts. A dog ran.")
llm._ctx.kv_cache_clear()
# 1. multi-seq prefill, selective logits (wave_prefill_naive pattern)
rows = []
for j, T in enumerate([A, B]):
    for i, t in enumerate(T):
        rows.append((j + 1, i, t, i == len(T) - 1))
try:
    raw_decode_rows(llm, rows)
    print("1. multiseq selective-logits prefill OK", flush=True)
except Exception as e:
    print("1. PREFILL FAIL", repr(e), flush=True)
# 2. decode on slot seq directly (no rm/cp)
try:
    raw_decode_rows(llm, [(1, len(A) - 1, A[-1], True)])
    print("2. re-decode on slot seq OK", flush=True)
except Exception as e:
    print("2. SLOT-DECODE FAIL", repr(e), flush=True)
# 3. rm(0) + cp(1->0) + decode on seq 0 (slot_decode_grammar pattern)
try:
    llm._ctx.kv_cache_seq_rm(0, -1, -1)
    llm._ctx.kv_cache_seq_cp(1, 0, -1, -1)
    raw_decode_rows(llm, [(0, len(A) - 1, A[-1], True)])
    print("3. rm+cp+decode-scratch OK", flush=True)
except Exception as e:
    print("3. SCRATCH FAIL", repr(e), flush=True)

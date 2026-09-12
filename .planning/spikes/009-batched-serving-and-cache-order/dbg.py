"""Debug 009: isolate the failing decode (GPU, under flock)."""
from __future__ import annotations
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
from batchserve import raw_decode_rows  # noqa: E402
from llama_cpp import Llama  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
llm = Llama(model_path=os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf"),
            n_gpu_layers=-1, n_ctx=4096, n_batch=512,
            embedding=True, verbose=False)


def tok(s: str) -> list[int]:
    return llm.tokenize(s.encode(), add_bos=False, special=False)


A = tok("MelodyScribe ingest v0.1. File facts. The cat sat.")
print("lens", len(A), flush=True)
llm._ctx.kv_cache_clear()
# single-seq prefill, all outputs (002 style)
b = llm._batch.batch
llm._batch.reset()
b.n_tokens = len(A)
for i, t in enumerate(A):
    b.token[i] = t
    b.pos[i] = i
    b.seq_id[i][0] = 0
    b.n_seq_id[i] = 1
    b.logits[i] = True
try:
    llm._ctx.decode(llm._batch)
    print("prefill seq0 all-out OK", flush=True)
except Exception as e:
    print("prefill FAIL", repr(e), flush=True)
llm._batch.reset()
# cp 0 -> 1
try:
    llm._ctx.kv_cache_seq_cp(0, 1, -1, -1)
    print("cp(0->1) OK", flush=True)
except Exception as e:
    print("cp FAIL", repr(e), flush=True)
# single-token cont on seq 1
try:
    raw_decode_rows(llm, [(1, len(A), A[-1], True)])
    print("cont seq1 OK", flush=True)
except Exception as e:
    print("cont FAIL", repr(e), flush=True)
# sampler from that state
try:
    llm.n_tokens = len(A) + 1
    llm._sampler = llm._init_sampler(top_k=1, temp=0.0)
    t = llm.sample(top_k=1, temp=0.0, idx=None)
    print("sample OK", int(t), flush=True)
    llm._sampler = None
except Exception as e:
    print("sample FAIL", repr(e), flush=True)

"""Debug 009f: full-buffer logits read after multi-seq prefill (GPU)."""
from __future__ import annotations
import ctypes
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
from batchserve import raw_decode_rows, set_generative  # noqa: E402
from llama_cpp import Llama  # noqa: E402
import llama_cpp  # noqa: E402
import numpy as np  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
log = open(os.path.join(D, "logs", "dbg6.out"), "w")


def crumb(s: str):
    log.write(s + "\n")
    log.flush()
    print(s, flush=True)


llm = Llama(model_path=os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf"),
            n_gpu_layers=-1, n_ctx=4096, n_batch=2048,
            embedding=True, verbose=False)
set_generative(llm)


def tok(s: str) -> list[int]:
    return llm.tokenize(s.encode(), add_bos=False, special=False)


A = tok("MelodyScribe ingest v0.1. File facts. The cat sat.")
B = tok("MelodyScribe ingest v0.1. File facts. A dog ran.")
refs = []
for T in (A, B):
    gen = llm.generate(T, top_k=1, top_p=1.0, min_p=0.0, temp=0.0, reset=True)
    refs.append(next(gen))
    gen.close()
crumb(f"refs {refs}")
llm._ctx.kv_cache_clear()
rows = []
for j, T in enumerate([A, B]):
    for i, t in enumerate(T):
        rows.append((j + 1, i, t, i == len(T) - 1))
raw_decode_rows(llm, rows)
crumb("2-seq prefill OK")
ptr = llm._ctx.get_logits()
crumb(f"get_logits null={not bool(ptr)}")
if bool(ptr):
    buf = np.ctypeslib.as_array(ptr, shape=(2 * llm.n_vocab(),))
    a0 = int(np.argmax(buf[:llm.n_vocab()]))
    a1 = int(np.argmax(buf[llm.n_vocab():]))
    crumb(f"full-buffer argmax [{a0}, {a1}] match={[a0 == refs[0], a1 == refs[1]]}")
crumb("done")

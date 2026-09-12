"""Debug 009c: same-pos re-decode vs sampler idx on prefill outputs."""
from __future__ import annotations
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
from batchserve import raw_decode_rows  # noqa: E402
from llama_cpp import Llama  # noqa: E402
import numpy as np  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
llm = Llama(model_path=os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf"),
            n_gpu_layers=-1, n_ctx=4096, n_batch=2048,
            embedding=True, verbose=False)


def tok(s: str) -> list[int]:
    return llm.tokenize(s.encode(), add_bos=False, special=False)


A = tok("MelodyScribe ingest v0.1. File facts. The cat sat.")
B = tok("MelodyScribe ingest v0.1. File facts. A dog ran.")
# reference first tokens via generate()
refs = []
for T in (A, B):
    gen = llm.generate(T, top_k=1, top_p=1.0, min_p=0.0, temp=0.0, reset=True)
    refs.append(next(gen))
    gen.close()
print("refs", refs, flush=True)

llm._ctx.kv_cache_clear()
rows = []
for j, T in enumerate([A, B]):
    for i, t in enumerate(T):
        rows.append((j + 1, i, t, i == len(T) - 1))
raw_decode_rows(llm, rows)
print("prefill 2-seq OK (2 outputs)", flush=True)
# sample directly from prefill outputs: slot j -> idx j-K
llm._sampler = llm._init_sampler(top_k=1, top_p=1.0, min_p=0.0, temp=0.0)
try:
    t0 = llm._sampler.sample(llm._ctx, 0 - 2)
    t1 = llm._sampler.sample(llm._ctx, 1 - 2)
    print("sampler idx sample", [int(t0), int(t1)], "match refs:",
          [int(t0) == refs[0], int(t1) == refs[1]], flush=True)
except Exception as e:
    print("sampler-idx FAIL", repr(e), flush=True)
llm._sampler = None
# logits_ith readback per output
try:
    l0 = np.ctypeslib.as_array(llm._ctx.get_logits_ith(0),
                               shape=(llm.n_vocab(),))
    l1 = np.ctypeslib.as_array(llm._ctx.get_logits_ith(1),
                               shape=(llm.n_vocab(),))
    print("logits_ith argmax", [int(np.argmax(l0)), int(np.argmax(l1))],
          "match refs:", [int(np.argmax(l0)) == refs[0],
                          int(np.argmax(l1)) == refs[1]], flush=True)
except Exception as e:
    print("logits_ith FAIL", repr(e), flush=True)
# same-pos re-decode (the suspected trigger), isolated
try:
    raw_decode_rows(llm, [(1, len(A) - 1, A[-1], True)])
    print("same-pos re-decode OK (unexpected)", flush=True)
except Exception as e:
    print("same-pos re-decode FAIL (as suspected)", repr(e), flush=True)

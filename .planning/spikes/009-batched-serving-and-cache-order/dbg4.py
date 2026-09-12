"""Debug 009d: generative-output mode on a multi-seq instance (GPU)."""
from __future__ import annotations
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
from batchserve import raw_decode_rows  # noqa: E402
from llama_cpp import Llama  # noqa: E402
import llama_cpp  # noqa: E402
import numpy as np  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
llm = Llama(model_path=os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf"),
            n_gpu_layers=-1, n_ctx=4096, n_batch=2048,
            embedding=True, verbose=False)
llama_cpp.llama_set_embeddings(llm._ctx.ctx, False)
print("embeddings flag flipped to False (generative outputs)", flush=True)


def tok(s: str) -> list[int]:
    return llm.tokenize(s.encode(), add_bos=False, special=False)


A = tok("MelodyScribe ingest v0.1. File facts. The cat sat.")
B = tok("MelodyScribe ingest v0.1. File facts. A dog ran.")
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
print("2-seq prefill in generative mode OK", flush=True)
l0 = np.ctypeslib.as_array(llm._ctx.get_logits_ith(0),
                           shape=(llm.n_vocab(),))
l1 = np.ctypeslib.as_array(llm._ctx.get_logits_ith(1),
                           shape=(llm.n_vocab(),))
a0, a1 = int(np.argmax(l0)), int(np.argmax(l1))
print("logits_ith argmax", [a0, a1], "match:", [a0 == refs[0],
                                                a1 == refs[1]], flush=True)
llm._sampler = llm._init_sampler(top_k=1, top_p=1.0, min_p=0.0, temp=0.0)
try:
    s0 = int(llm._sampler.sample(llm._ctx, 0 - 2))
    s1 = int(llm._sampler.sample(llm._ctx, 1 - 2))
    print("sampler idx", [s0, s1], "match:", [s0 == refs[0],
                                              s1 == refs[1]], flush=True)
except Exception as e:
    print("sampler FAIL", repr(e), flush=True)
llm._sampler = None

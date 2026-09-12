"""Debug 009e: breadcrumb isolation of the sampler assert (GPU)."""
from __future__ import annotations
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
from batchserve import raw_decode_rows, set_generative  # noqa: E402
from llama_cpp import Llama, LlamaGrammar  # noqa: E402
import llama_cpp  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
log = open(os.path.join(D, "logs", "dbg5.out"), "w")


def crumb(s: str):
    log.write(s + "\n")
    log.flush()
    print(s, flush=True)


llm = Llama(model_path=os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf"),
            n_gpu_layers=-1, n_ctx=4096, n_batch=2048,
            embedding=True, verbose=False)
crumb("loaded")


def tok(s: str) -> list[int]:
    return llm.tokenize(s.encode(), add_bos=False, special=False)


A = tok("MelodyScribe ingest v0.1. File facts. The cat sat. " * 8)
crumb(f"prompt_len {len(A)}")
set_generative(llm)
crumb("flipped")
r = llm.create_completion(
    "MelodyScribe ingest v0.1. File facts. The cat sat. ",
    max_tokens=4, temperature=0.0, seed=11)
crumb(f"create_completion-after-flip OK len={len(r['choices'][0]['text'])}")
# single-seq raw prefill + single-output sample (the dbg.py pattern)
llm._ctx.kv_cache_clear()
raw_decode_rows(llm, [(1, i, t, i == len(A) - 1) for i, t in enumerate(A)])
crumb("single-seq raw prefill OK")
llm._sampler = llm._init_sampler(top_k=1, temp=0.0)
crumb(f"sample-last {int(llm._sampler.sample(llm._ctx, -1))}")
llm._sampler = None
crumb("done")

"""Debug 009h: is the scheduler first token in the ref top-5 (GPU)?"""
from __future__ import annotations
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
sys.path.insert(0, os.path.join(D, "..", "003-op-emission-size-sweep"))
from common import load_units, student_prompt  # noqa: E402
from v02_grammar import grammar_v02  # noqa: E402
from batchserve import (set_generative, wave_prefill,  # noqa: E402
                        fresh_greedy_sampler, slot_first)  # noqa: E402
from llama_cpp import Llama  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
log = open(os.path.join(D, "logs", "dbg8.out"), "w")


def crumb(s: str):
    log.write(s + "\n")
    log.flush()
    print(s, flush=True)


units, _ = load_units()
paras = []
for doc_id, text in units:
    body = text.split("\n", 1)[1] if "\n" in text else text
    for p in [x.strip().replace("\n", " ") for x in body.split("\n\n")]:
        if len(p) >= 200:
            paras.append(p[:600])
            break
prompts = [student_prompt(p) for p in paras[:4]]
llm = Llama(model_path=os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf"),
            n_gpu_layers=-1, n_ctx=4096, n_batch=2048, logits_all=True,
            embedding=True, verbose=False)
set_generative(llm)


def tok(s: str) -> list[int]:
    return llm.tokenize(s.encode(), add_bos=False, special=False)


ptoks = [tok(p) for p in prompts]
# ref top-5 first-token logprobs via public path (no grammar: raw next tok)
tops = []
for p in prompts:
    r = llm.create_completion(p, max_tokens=1, temperature=0.0, seed=11,
                              logprobs=5)
    lp = r["choices"][0]["logprobs"]["top_logprobs"][0]
    tops.append(sorted(lp.items(), key=lambda kv: -kv[1])[:5])
llm._ctx.kv_cache_clear()
_, lens = wave_prefill(llm, ptoks)
sampler = fresh_greedy_sampler(llm)
firsts = [slot_first(llm, j + 1, L, t[-1], sampler)[0]
          for j, (t, L) in enumerate(zip(ptoks, lens))]
llm._sampler = None
for j in range(4):
    det = llm.detokenize([firsts[j]]).decode("utf-8", errors="replace")
    top = [(llm.detokenize([int(k.split("token_")[1])]).decode(
        "utf-8", errors="replace") if k.startswith("token_") else k, round(v, 2))
        for k, v in tops[j]]
    crumb(f"slot{j} first={firsts[j]} ({det!r}) ref_top5={top}")
crumb("done")

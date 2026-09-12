"""Debug 009g: per-slot interference vs systematic divergence (GPU)."""
from __future__ import annotations
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
sys.path.insert(0, os.path.join(D, "..", "003-op-emission-size-sweep"))
from common import load_units, student_prompt  # noqa: E402
from v02_grammar import grammar_v02  # noqa: E402
from batchserve import (set_generative, wave_prefill, slot_decode_grammar,  # noqa: E402
                        fresh_greedy_sampler, slot_first)  # noqa: E402
from llama_cpp import Llama, LlamaGrammar  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
GRAMMAR = grammar_v02()
log = open(os.path.join(D, "logs", "dbg7.out"), "w")


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
            n_gpu_layers=-1, n_ctx=4096, n_batch=2048,
            embedding=True, verbose=False)
set_generative(llm)


def tok(s: str) -> list[int]:
    return llm.tokenize(s.encode(), add_bos=False, special=False)


ptoks = [tok(p) for p in prompts]
ref2 = llm.create_completion(
    prompts[2], grammar=LlamaGrammar.from_string(GRAMMAR, verbose=False),
    max_tokens=48, temperature=0.0, seed=11)["choices"][0]["text"]
# K=1 wave, prompt 2 alone on seq 1
llm._ctx.kv_cache_clear()
_, (L,) = wave_prefill(llm, [ptoks[2]])
got1, _, _, _ = slot_decode_grammar(llm, 1, L, ptoks[2][-1], GRAMMAR, 48)
crumb(f"K=1 prompt2 equal={got1 == ref2} got_len={len(got1)} ref_len={len(ref2)}")
# greedy first tokens: wave of 4, single-row calls
llm._ctx.kv_cache_clear()
_, lens = wave_prefill(llm, ptoks)
sampler = fresh_greedy_sampler(llm)
firsts = [slot_first(llm, j + 1, L, t[-1], sampler)[0]
          for j, (t, L) in enumerate(zip(ptoks, lens))]
llm._sampler = None
gen_firsts = []
for t in ptoks:
    gen = llm.generate(t, top_k=1, top_p=1.0, min_p=0.0, temp=0.0, reset=True)
    gen_firsts.append(next(gen))
    gen.close()
crumb(f"greedy firsts {firsts} vs generate {[int(g) for g in gen_firsts]}")
crumb("done")

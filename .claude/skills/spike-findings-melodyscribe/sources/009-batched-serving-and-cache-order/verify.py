"""Spike 009 verify: scheduler reproduces the production path up to
documented near-tie flips (GPU).

Production path = create_completion (spike 003's student path), greedy,
seed 11. Criteria:
  (a) serial-grammar: 4/4 first-token equal, >=3/4 full-text equal.
  (b) parallel-greedy vs free decode: 4/4 first-token equal; full-text
      agreement reported (split-prefill tie flips allowed, cf. spike 005).
Anything less -> ABORT (scheduler diverges beyond tie noise).
"""
from __future__ import annotations
import os, sys, time
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
sys.path.insert(0, os.path.join(D, "..", "003-op-emission-size-sweep"))
from common import load_units, student_prompt  # noqa: E402
from v02_grammar import grammar_v02  # noqa: E402
from batchserve import (set_generative, emit, wave_prefill,  # noqa: E402
                        slot_decode_grammar,
                        wave_decode_parallel_greedy, vram_used_mb)
from llama_cpp import Llama, LlamaGrammar  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
GRAMMAR = grammar_v02()
CAP = 48

log = open(os.path.join(D, "logs", "verify.jsonl"), "w")
units, chash = load_units()
paras = []
for doc_id, text in units:
    body = text.split("\n", 1)[1] if "\n" in text else text
    for p in [x.strip().replace("\n", " ") for x in body.split("\n\n")]:
        if len(p) >= 200:
            paras.append(p[:600])
            break
emit(log, "pool", docs=len(units), sections=len(paras), corpus_hash=chash)
prompts = [student_prompt(p) for p in paras[:4]]

t0 = time.perf_counter()
llm = Llama(model_path=os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf"),
            n_gpu_layers=-1, n_ctx=16384, n_batch=2048,
            embedding=True, verbose=False)
set_generative(llm)  # multi-output logits; never embed() here
emit(log, "load", seconds=round(time.perf_counter() - t0, 3),
     vram_mb=vram_used_mb(), n_seq_note="embedding=True for n_seq_max>1")


def tok(s: str) -> list[int]:
    return llm.tokenize(s.encode(), add_bos=False, special=False)


ptoks = [tok(p) for p in prompts]
emit(log, "prompt_tokens", lens=[len(t) for t in ptoks])

refs_g = []
for p in prompts:
    r = llm.create_completion(p, grammar=LlamaGrammar.from_string(
        GRAMMAR, verbose=False), max_tokens=CAP, temperature=0.0, seed=11)
    refs_g.append(r["choices"][0]["text"])
refs_f = []
for p in prompts:
    r = llm.create_completion(p, max_tokens=CAP, temperature=0.0, seed=11)
    refs_f.append(r["choices"][0]["text"])


def first_id(text: str) -> int:
    ids = llm.tokenize(text.encode(), add_bos=False, special=False)
    return ids[0] if ids else -1


# (a) serial grammar
llm._ctx.kv_cache_clear()
_, lens = wave_prefill(llm, ptoks)
got = []
firsts_a = []
for j, (t, L) in enumerate(zip(ptoks, lens)):
    text, ids, ttft, dec = slot_decode_grammar(llm, j + 1, L, t[-1],
                                               GRAMMAR, CAP)
    got.append(text)
    firsts_a.append(ids[0] if ids else -1)
eq_full_a = [a == b for a, b in zip(got, refs_g)]
eq_first_a = [a == first_id(b) for a, b in zip(firsts_a, refs_g)]
emit(log, "verify_serial_grammar", full_equal=eq_full_a,
     first_equal=eq_first_a,
     ref_lens=[len(r) for r in refs_g], got_lens=[len(g) for g in got])

# (b) parallel greedy vs free decode
llm._ctx.kv_cache_clear()
_, lens = wave_prefill(llm, ptoks)
outs, dec_s, _ = wave_decode_parallel_greedy(llm, [1, 2, 3, 4], lens,
                                             [t[-1] for t in ptoks], CAP)
texts_b = [llm.detokenize(o).decode("utf-8", errors="replace") for o in outs]
eq_full_b = [a == b for a, b in zip(texts_b, refs_f)]
eq_first_b = [(o[0] if o else -1) == first_id(r)
              for o, r in zip(outs, refs_f)]
emit(log, "verify_parallel_greedy", full_equal=eq_full_b,
     first_equal=eq_first_b, dec_s=round(dec_s, 3))

ok_a = all(eq_first_a) and sum(eq_full_a) >= 3
ok_b = all(eq_first_b)
emit(log, "verdict", ok=bool(ok_a and ok_b), note="tie flips allowed in b-full")
log.close()
print("VERIFY", "PASS" if ok_a and ok_b else "FAIL", eq_full_a, eq_full_b)
if not (ok_a and ok_b):
    raise SystemExit(1)

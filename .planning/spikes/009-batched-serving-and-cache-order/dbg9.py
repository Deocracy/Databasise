"""Debug 009i: replicate continuation R-decode with crumbs (GPU)."""
from __future__ import annotations
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
sys.path.insert(0, os.path.join(D, "..", "003-op-emission-size-sweep"))
from common import load_units, student_prompt  # noqa: E402
from v02_grammar import grammar_v02  # noqa: E402
from batchserve import (set_generative, wave_prefill, raw_decode_rows,  # noqa: E402
                        slot_decode_grammar)  # noqa: E402
from llama_cpp import Llama  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
GRAMMAR = grammar_v02()
log = open(os.path.join(D, "logs", "dbg9.out"), "w")


def crumb(s: str):
    log.write(s + "\n")
    log.flush()
    print(s, flush=True)


units, _ = load_units()
body = units[0][1].split("\n", 1)[1]
para = [x.strip().replace("\n", " ") for x in body.split("\n\n") if len(x.strip()) >= 200][0][:600]
SYS = ("You are MelodyScribe, a precise information-extraction harness. "
       "Output JSON only, no prose. ")
SKILL = ("MelodyScribe filing skill v0.2. Targets graph and sql. "
         "Graph op needs subject, predicate, object, quote. "
         "Sql op needs subject, attribute, value, value_type, quote. "
         "Dates as ISO 8601 or a year, numbers as decimals. "
         "Emit {\"ops\":[...]} with at most 32 ops. ")
DOC_PREFIX = "MelodyScribe ingest v0.1. File facts with evidence spans. "
from common import INSTRUCTION  # noqa: E402
P = SYS + SKILL + DOC_PREFIX
llm = Llama(model_path=os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf"),
            n_gpu_layers=-1, n_ctx=16384, n_batch=2048,
            embedding=True, verbose=False)
set_generative(llm)


def tok(s: str) -> list[int]:
    return llm.tokenize(s.encode(), add_bos=False, special=False)


F = tok(P + "Section:\n" + para + "\n\n" + INSTRUCTION + "\nJSON:\n")
R = tok("\nRecall: Who is described? {\"recall\":[{\"source\":\"vector\",\"k\":8}]}\nAnswer:\n")
crumb(f"F={len(F)} R={len(R)} Rids={R[:5]}")
llm._ctx.kv_cache_clear()
_, (Lb,) = wave_prefill(llm, [F])
crumb(f"prefill ok Lb={Lb}")
_, oids, _, _ = slot_decode_grammar(llm, 1, Lb, F[-1], GRAMMAR, 48)
crumb(f"slot_decode ok oids={len(oids)} last3={oids[-3:]}")
base = Lb + len(oids)
rows = [(1, base + i, tk, i == len(R) - 1) for i, tk in enumerate(R)]
crumb(f"rows base={base} n={len(rows)}")
h = len(rows) // 2
raw_decode_rows(llm, [(s_, p, t, False) for (s_, p, t, _) in rows[:h]])
crumb("R first-half ok")
raw_decode_rows(llm, [(s_, p, t, (i == len(rows) - 1)) for i, (s_, p, t, _) in enumerate(rows[h:], start=h)])
crumb("R second-half ok")
llm.n_tokens = base + len(R)
llm._sampler = llm._init_sampler(top_k=1, temp=0.0)
crumb(f"sample {int(llm.sample(top_k=1, temp=0.0, idx=None))}")
llm._sampler = None
crumb("done")

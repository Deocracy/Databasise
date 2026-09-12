"""Spike 009 token stats (CPU only, vocab_only load, no lock).

Precomputes everything that needs no GPU: pool paragraphs, prompt token
lengths, shared-prefix fractions for segment orders, sorted/shuffled
layouts. Output: logs/tokstats.json.
"""
from __future__ import annotations
import datetime
import importlib.util
import json
import os
import sys

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(D, "..", "003-op-emission-size-sweep"))
from common import load_units, student_prompt, INSTRUCTION  # noqa: E402

MODELS = os.environ.get("MELODYSCRIBE_MODELS",
                        os.path.join(D, "..", ".models"))
SKILL = ("MelodyScribe filing skill v0.2. Targets graph and sql. "
         "Graph op needs subject, predicate, object, quote. "
         "Sql op needs subject, attribute, value, value_type, quote. "
         "Dates as ISO 8601 or a year, numbers as decimals. "
         "Emit {\"ops\":[...]} with at most 32 ops. ")
SYS = ("You are MelodyScribe, a precise information-extraction harness. "
       "Output JSON only, no prose. ")
DOC_PREFIX = "MelodyScribe ingest v0.1. File facts with evidence spans. "


def main() -> int:
    from llama_cpp import Llama
    out: dict = {"ts": datetime.datetime.now(
        datetime.timezone.utc).isoformat()}
    m = Llama(model_path=os.path.join(MODELS, "MiniCPM5-2B-Q8_0.gguf"),
              vocab_only=True, verbose=False)

    def tok(s: str) -> list[int]:
        return m.tokenize(s.encode(), add_bos=False, special=False)

    units, chash = load_units()
    paras = []
    for doc_id, text in units:
        body = text.split("\n", 1)[1] if "\n" in text else text
        for p in [x.strip().replace("\n", " ") for x in body.split("\n\n")]:
            if len(p) >= 200:
                paras.append(p[:600])
                break
    out["corpus_hash"] = chash
    out["docs"] = len(units)
    out["sections"] = len(paras)
    prompts = [student_prompt(p) for p in paras]
    plens = sorted(len(tok(p)) for p in prompts)
    out["prompt_toks"] = {"min": plens[0], "p50": plens[len(plens) // 2],
                          "max": plens[-1], "mean": round(
                              sum(plens) / len(plens), 1)}
    P = tok(SYS + SKILL + DOC_PREFIX)
    out["shared_prefix_toks"] = len(P)
    T = [tok("Section:\n" + p + "\n\n" + INSTRUCTION + "\nJSON:\n")
         for p in paras]
    tls = sorted(len(t) for t in T)
    out["tail_toks"] = {"min": tls[0], "p50": tls[len(tls) // 2],
                        "max": tls[-1]}
    out["shared_frac_after"] = round(
        len(P) / (len(P) + sum(tls) / len(tls)), 4)
    Tb = [tok(INSTRUCTION + "\nSection:\n" + p + "\nJSON:\n") for p in paras]
    tbl = sorted(len(t) for t in Tb)
    out["instr_before_tail_p50"] = tbl[len(tbl) // 2]
    out["note"] = ("instr-before puts the shared instruction first: shared "
                   "run is INSTRUCTION+prefix; measured exactly in "
                   "cacheorder.py")
    P4 = [tok(SYS + SKILL + f"Corpus shard {k}. " + DOC_PREFIX)
          for k in range(4)]
    out["shard_prefix_toks"] = [len(p) for p in P4]
    # boundary-merge check: split vs single-string tokenisation
    bnd = [len(tok(SYS + SKILL + DOC_PREFIX)) + len(tok("Section:\n" + paras[0]))
           - len(tok(SYS + SKILL + DOC_PREFIX + "Section:\n" + paras[0]))]
    out["boundary_merge_delta"] = bnd
    os.makedirs(os.path.join(D, "logs"), exist_ok=True)
    json.dump(out, open(os.path.join(D, "logs", "tokstats.json"), "w"),
              indent=1)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

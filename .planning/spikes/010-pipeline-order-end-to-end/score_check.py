"""Spike 010 Score compile check (CPU, stdlib only).

For all 20 docs x {whole, split}: build the Score, validate through
spike 001's parse_score + compile_plan, assert plan shape (one decode
step per section with cap>0 and grammar, one read_vector per section
with unique (seq,pos), S0 order). Plus an I1 spot check: the same
section compiled at position 1 vs position 2 of a 2-section Score
yields identical E_i token-string lists.

Writes logs/score-check-<utc>.jsonl.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s10_common as C  # noqa: E402


def main() -> None:
    log_path = C.HERE / "logs" / (
        "score-check-"
        + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + ".jsonl")
    log_path.parent.mkdir(exist_ok=True)
    log_fh = open(log_path, "w")

    docs, corpus_hash = C.load_corpus()
    n_scores = 0
    for variant, chunk in (("whole", C.chunk_whole), ("split", C.chunk_split)):
        for doc_id, text in docs:
            sections = chunk(doc_id, text)
            spec, plan = C.compile_and_check(doc_id, sections)
            assert len(spec["sections"]) == len(sections)
            decodes = [s for s in plan["steps"] if s["kind"] == "decode"]
            reads = [s for s in plan["steps"] if s["kind"] == "read_vector"]
            assert len(decodes) == len(sections), (doc_id, variant)
            assert len(reads) == len(sections), (doc_id, variant)
            for d in decodes:
                assert d["cap"] and d["cap"] > 0
                assert d["grammar"] is not None
            assert len({(r["seq"], r["at"]) for r in reads}) == len(reads)
            n_scores += 1
    C.emit(log_fh, "compile_ok", n_scores=n_scores, corpus_hash=corpus_hash)

    # I1 spot check on a 2-section Score (title/body of doc 0)
    doc_id, text = docs[0]
    sections = C.chunk_split(doc_id, text)
    spec, plan = C.compile_and_check(doc_id, sections)
    ei = {s["id"]: C.score001.ei_tokens(plan, spec, s["id"])
          for s in spec["sections"]}
    # rebuild with sections swapped: E_i lists must be identical per section
    swapped = list(reversed(sections))
    spec2, plan2 = C.compile_and_check(doc_id, swapped)
    for s in spec2["sections"]:
        toks2 = C.score001.ei_tokens(plan2, spec2, s["id"])
        assert ei[s["id"]] == toks2, f"I1 fail on {s['id']}"
    C.emit(log_fh, "i1_spot_ok", doc=doc_id)
    print(f"compile_ok n_scores={n_scores} i1_spot_ok doc={doc_id} log={log_path}")


if __name__ == "__main__":
    sys.exit(main())

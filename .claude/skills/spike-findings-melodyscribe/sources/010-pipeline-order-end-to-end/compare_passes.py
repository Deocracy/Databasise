"""Spike 010 one-pass vs two-pass comparison (CPU, stdlib + numpy).

Identical inputs: whole-variant sections.
  one-pass: vectors/whole_onepass.json (one load, embed+decode per section)
  two-pass: vectors/whole2_embed2b.json + vectors/whole2_ops2b.json
Compares: embedding cosine per section, ops-text equality, wall time and
docs/min (from per-section seconds + load seconds), Proof pass counts.

Writes results/passes.json + logs/passes-<utc>.jsonl.
"""

from __future__ import annotations

import datetime
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s10_common as C  # noqa: E402


def cos(a, b):
    n = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (n or 1)


def prove_counts(rec):
    import s10_common as C2
    passed = failed = 0
    for e in rec["sections"].values():
        if "text" not in e:
            continue
        r = C2.prove_section(e["text"], e["content"])
        passed += len(r["passed"])
        failed += len(r["failed"])
    return {"passed": passed, "failed": failed}


def main() -> None:
    vec = C.HERE / "vectors"
    one = json.loads(next(vec.glob("whole_onepass.json")).read_text())
    emb = json.loads(next(vec.glob("whole2_embed2b.json")).read_text())
    ops = json.loads(next(vec.glob("whole2_ops2b.json")).read_text())

    rows = []
    for sec, e1 in one["sections"].items():
        e2, o2 = emb["sections"][sec], ops["sections"][sec]
        assert e1["content"] == e2["content"] == o2["content"], sec
        rows.append({
            "sec": sec,
            "emb_cos_1v2": cos(e1["emb"], e2["emb"]),
            "ops_identical": e1["text"] == o2["text"],
            "one_emb_s": e1["emb_seconds"], "one_ops_s": e1["ops_seconds"],
            "two_emb_s": e2["emb_seconds"], "two_ops_s": o2["ops_seconds"],
        })
    p1 = prove_counts(one)
    p2 = prove_counts(ops)

    one_wall = one["load_seconds"] + sum(
        e["emb_seconds"] + e["ops_seconds"] for e in one["sections"].values()
        if "text" in e)
    two_wall = (emb["load_seconds"] + ops["load_seconds"]
                + sum(e["emb_seconds"] for e in emb["sections"].values())
                + sum(e["ops_seconds"] for e in ops["sections"].values()))
    n = len(rows)
    out = {
        "n_sections": n,
        "emb_cos_min": min(r["emb_cos_1v2"] for r in rows),
        "emb_cos_mean": sum(r["emb_cos_1v2"] for r in rows) / n,
        "ops_identical": sum(r["ops_identical"] for r in rows),
        "one_wall_s": round(one_wall, 1), "two_wall_s": round(two_wall, 1),
        "one_docs_min": round(n / one_wall * 60, 2),
        "two_docs_min": round(n / two_wall * 60, 2),
        "one_proof": p1, "two_proof": p2,
        "one_load_s": one["load_seconds"],
        "two_load_s": round(emb["load_seconds"] + ops["load_seconds"], 2),
        "rows": rows,
    }
    log_path = C.HERE / "logs" / (
        "passes-"
        + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + ".jsonl")
    log_fh = open(log_path, "w")
    C.emit(log_fh, "passes", **{k: v for k, v in out.items() if k != "rows"})
    (C.HERE / "results" / "passes.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    sys.exit(main())

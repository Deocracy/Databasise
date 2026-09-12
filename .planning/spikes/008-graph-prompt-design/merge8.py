"""Merge split-half student files for spike 008 (no GPU, no network).

Usage: merge8.py <arm> <suffix1> <suffix2>   (e.g. merge8.py qwen4b _h1 _h2)
Reads students/<D>_<arm><suffix>.json for all 8 designs, asserts disjoint doc
sets jointly covering the SCORED set with one corpus_hash, and writes
students/<D>_<arm>.json. Deterministic: reruns are byte-identical.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import DESIGNS, HERE, split_docs  # noqa: E402


def main() -> None:
    arm, s1, s2 = sys.argv[1], sys.argv[2], sys.argv[3]
    _, scored = split_docs()
    for d in DESIGNS:
        a = json.loads((HERE / "students" / f"{d}_{arm}{s1}.json").read_text())
        b = json.loads((HERE / "students" / f"{d}_{arm}{s2}.json").read_text())
        assert a["corpus_hash"] == b["corpus_hash"], d
        assert set(a["outputs"]).isdisjoint(b["outputs"]), d
        assert set(a["outputs"]) | set(b["outputs"]) == set(scored), d
        m = dict(a)
        m["arm"] = f"{d}_{arm}"
        m["outputs"] = {**a["outputs"], **b["outputs"]}
        (HERE / "students" / f"{d}_{arm}.json").write_text(
            json.dumps(m, indent=1) + "\n")
    print(f"merged arm={arm}: 8 designs x {len(scored)} docs")


if __name__ == "__main__":
    sys.exit(main())

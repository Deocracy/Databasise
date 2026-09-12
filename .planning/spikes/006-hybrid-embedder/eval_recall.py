"""Score retrieval arms head-to-head (CPU only, numpy allowed).

Usage: eval_recall.py <run_name> <vecs1.json> [<vecs2.json> ...]
Each vecs file: {arm, doc_ids, doc_vecs, query_ids, query_vecs, query_doc,
query_split, gold_ids, gold_vecs, gold_docs}. All arms must share doc order
(asserted). Reports test-split (held-out docs) recall@1/3/10 + MRR, train
diagnostic, gold HotpotQA, and anisotropy. Writes
results/recall_<run_name>.json + logs/<run_name>.jsonl.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_eval import KS, RESULTS, anisotropy, emit, score_queries  # noqa: E402


def main() -> None:
    run_name = sys.argv[1]
    paths = sys.argv[2:]
    arms = [json.loads(Path(p).read_text()) for p in paths]
    doc_ids = arms[0]["doc_ids"]
    for a in arms[1:]:
        assert a["doc_ids"] == doc_ids, f"doc order drift in {a['arm']}"

    table = []
    for a in arms:
        dv = a["doc_vecs"]
        tq = [(i, v, [d]) for i, v, d in
              zip(a["query_ids"], a["query_vecs"], a["query_doc"])
              if a["query_split"][a["query_ids"].index(i)] == "test"]
        rq = [(i, v, [d]) for i, v, d in
              zip(a["query_ids"], a["query_vecs"], a["query_doc"])
              if a["query_split"][a["query_ids"].index(i)] == "train"]
        gq = list(zip(a["gold_ids"], a["gold_vecs"], a["gold_docs"]))
        _, test = score_queries(doc_ids, dv, tq)
        _, train = score_queries(doc_ids, dv, rq)
        _, gold = score_queries(doc_ids, dv, gq)
        row = {"arm": a["arm"], "n_test": len(tq), "n_train": len(rq),
               "test": {k: round(v, 4) for k, v in test.items()},
               "train": {k: round(v, 4) for k, v in train.items()},
               "gold": {k: round(v, 4) for k, v in gold.items()},
               "anisotropy": round(anisotropy(dv), 4),
               "ms_per_doc": a.get("ms_per_doc"), "ms_per_query": a.get("ms_per_query")}
        table.append(row)
        emit(run_name, "arm_scored", arm=a["arm"],
             test_mrr=round(test["mrr"], 4), train_mrr=round(train["mrr"], 4),
             gold_mrr=round(gold["mrr"], 4), anisotropy=row["anisotropy"])
    (RESULTS / f"recall_{run_name}.json").write_text(
        json.dumps({"run": run_name, "arms": table}, indent=1) + "\n")
    print(f"{'arm':<14}{'test r@1':>9}{'r@3':>7}{'r@10':>7}{'MRR':>7}"
          f"{'trainMRR':>9}{'goldMRR':>8}{'aniso':>7}")
    for r in table:
        t = r["test"]
        print(f"{r['arm']:<14}{t['r@1']:>9.3f}{t['r@3']:>7.3f}{t['r@10']:>7.3f}"
              f"{t['mrr']:>7.3f}{r['train']['mrr']:>9.3f}{r['gold']['mrr']:>8.3f}"
              f"{r['anisotropy']:>7.3f}")


if __name__ == "__main__":
    sys.exit(main())

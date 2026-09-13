"""Shared retrieval scoring for spike 006 (stdlib + numpy, CPU only).

Metrics mirror spike 004 (recall@k, MRR, mean pairwise doc cosine) but run
over the queries-v1 test split (30 queries, 5 held-out docs) plus the 2
HotpotQA gold queries, ranking all 20 docs per query.
"""
from __future__ import annotations

import datetime
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGS = HERE / "logs"
RESULTS = HERE / "results"
KS = (1, 3, 10)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def emit(run_name, event, **fields):
    LOGS.mkdir(parents=True, exist_ok=True)
    rec = {"ts": now_iso(), "run": run_name, "event": event, **fields}
    with open(LOGS / f"{run_name}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def norm(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else list(v)


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))


def rank_docs(query_vec, doc_vecs):
    q = norm(query_vec)
    scored = [(cos(q, norm(v)), did) for did, v in doc_vecs]
    scored.sort(reverse=True)
    return [did for _, did in scored]


def recall_at_k(ranked, gold, k):
    top, g = set(ranked[:k]), set(gold)
    return len(top & g) / len(g)


def score_queries(doc_ids, doc_vecs, queries):
    """queries: [(qid, qvec, [gold_ids])] -> per-query ranks + agg over KS+MRR."""
    per_q, ranks = {}, []
    for qid, qvec, gold in queries:
        ranked = rank_docs(qvec, list(zip(doc_ids, doc_vecs)))
        first = min(ranked.index(g) for g in gold) + 1
        r = {f"r@{k}": recall_at_k(ranked, gold, k) for k in KS}
        r["rank1"] = first
        per_q[qid] = r
        ranks.append(r)
    agg = {f"r@{k}": sum(x[f"r@{k}"] for x in ranks) / len(ranks) for k in KS}
    agg["mrr"] = sum(1.0 / x["rank1"] for x in ranks) / len(ranks)
    return per_q, agg


def anisotropy(doc_vecs):
    """Mean pairwise cosine over the 20 doc vectors (spike 004 mechanism)."""
    n = len(doc_vecs)
    nv = [norm(v) for v in doc_vecs]
    s, c = 0.0, 0
    for i in range(n):
        for j in range(i + 1, n):
            s += cos(nv[i], nv[j])
            c += 1
    return s / c

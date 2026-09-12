"""Controls: corpus-mean centering, and chunk-level (in-distribution) recall.

Usage: controls.py <run_name>
- center_control: subtract doc centroid from docs+queries per arm, re-rank.
- chunk_recall: each chunk as query over all chunks, same-doc hit = recall.
"""
import json

from common import SPIKE_DIR, rank_docs, recall_at_k, log, norm

RES = SPIKE_DIR / "results"
IN = SPIKE_DIR / "inputs"
KS = (1, 3, 5, 10)
run_name = __import__("sys").argv[1]

doc_ids = json.load(open(IN / "docs.json"))["ids"]
gold = json.load(open(IN / "queries_gold.json", encoding="utf-8"))
selfq = json.load(open(IN / "queries_self.json", encoding="utf-8"))
queries = ([{"qid": q["id"], "gold": q["gold"], "set": "gold"} for q in gold]
           + [{"qid": "self:" + q["id"], "gold": q["gold"], "set": "self"}
              for q in selfq])
chunks = json.load(open(IN / "chunks.json", encoding="utf-8"))


def center(vecs):
    dim = len(vecs[0])
    n = len(vecs)
    mean = [sum(v[j] for v in vecs) / n for j in range(dim)]
    return [[v[j] - mean[j] for j in range(dim)] for v in vecs]


for arm in ["armA", "armB", "armB2", "armBplain"]:
    try:
        d = json.load(open(RES / f"{arm}_docs.json"))["vecs"]
        q = json.load(open(RES / f"{arm}_q.json"))
        qmap = dict(zip(q["ids"], q["vecs"]))
    except FileNotFoundError:
        continue
    dc, qc = center(d), center(list(qmap.values()))
    qcmap = dict(zip(qmap.keys(), qc))
    agg = {}
    for s in ("gold", "self"):
        rows = [r for qq in queries if qq["set"] == s
                for r in [rank_docs(qcmap[qq["qid"]], list(zip(doc_ids, dc)))]]
        rr = {}
        for k in KS:
            vals = [recall_at_k(r, qq["gold"], k)
                    for r, qq in zip(rows, [qq for qq in queries if qq["set"] == s])]
            rr[f"r@{k}"] = sum(vals) / len(vals)
        agg[s] = rr
    log(run_name, "center_control", arm=arm,
        **{f"gold_r@{k}": round(agg['gold'][f'r@{k}'], 4) for k in KS},
        **{f"self_r@{k}": round(agg['self'][f'r@{k}'], 4) for k in KS})
    print(f"{arm:10s} CENTERED gold " +
          " ".join(f"r@{k}={agg['gold'][f'r@{k}']:.2f}" for k in KS) + " | self " +
          " ".join(f"r@{k}={agg['self'][f'r@{k}']:.2f}" for k in KS))

# chunk-level self retrieval: chunk -> all chunks, hit if top-k contains same doc
for arm in ["armA", "armB"]:
    cv = json.load(open(RES / f"{arm}_chunks.json"))
    ids, vecs = cv["ids"], cv["vecs"]
    doc_of = {c["id"]: c["doc"] for c in chunks}
    hits = {k: 0 for k in KS}
    for i, v in enumerate(vecs):
        ranked = rank_docs(v, list(zip(ids, vecs)))
        ranked = [r for r in ranked if r != ids[i]]  # exclude self
        for k in KS:
            if any(doc_of[r] == doc_of[ids[i]] for r in ranked[:k]):
                hits[k] += 1
    n = len(ids)
    log(run_name, "chunk_recall", arm=arm,
        **{f"r@{k}": round(hits[k] / n, 4) for k in KS})
    print(f"{arm:10s} CHUNK " + " ".join(f"r@{k}={hits[k]/n:.2f}" for k in KS))

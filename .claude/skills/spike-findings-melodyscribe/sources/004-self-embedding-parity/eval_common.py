"""Build the input lists (identical raw texts for every arm) and evaluate recall.

Step 1 (this file, --build): write inputs/docs.json, inputs/queries_gold.json,
inputs/queries_self.json, inputs/chunks.json from the corpus.
Step 2: arm_embed.py runs per arm under the GPU lock.
Step 3 (this file, --eval): cosine recall@k head-to-head + JSONL log.
"""
import json
import sys
from pathlib import Path

from common import (SPIKE_DIR, load_corpus, split_sentences, rank_docs,
                    recall_at_k, log)

IN = SPIKE_DIR / "inputs"
RES = SPIKE_DIR / "results"


def build():
    IN.mkdir(parents=True, exist_ok=True)
    docs, queries = load_corpus()
    doc_texts = [d["text"] for d in docs]
    doc_ids = [d["id"] for d in docs]
    json.dump({"ids": doc_ids, "texts": doc_texts},
              open(IN / "docs.json", "w"), ensure_ascii=False)
    json.dump([{"id": q["id"], "question": q["question"],
                "gold": q["gold_document_ids"]} for q in queries],
              open(IN / "queries_gold.json", "w"), ensure_ascii=False)
    # self-retrieval probes: title + first sentence of each doc
    self_q = []
    for d in docs:
        sents = split_sentences(d["text"])
        probe = sents[1] if len(sents) > 1 else sents[0]  # skip title line
        self_q.append({"id": d["id"], "question": probe, "gold": [d["id"]]})
    json.dump(self_q, open(IN / "queries_self.json", "w"), ensure_ascii=False)
    # sentence chunks (train pool for the head + chunk-level eval)
    chunks = []
    for d in docs:
        for i, s in enumerate(split_sentences(d["text"])):
            chunks.append({"id": f"{d['id']}#s{i}", "doc": d["id"], "text": s})
    json.dump(chunks, open(IN / "chunks.json", "w"), ensure_ascii=False)
    print(f"docs={len(docs)} gold_queries={len(queries)} "
          f"self_queries={len(self_q)} chunks={len(chunks)}")
    log("build", "inputs_built", docs=len(docs), gold=len(queries),
        self_q=len(self_q), chunks=len(chunks))


def load_arm(name):
    d = json.load(open(RES / f"{name}.json", encoding="utf-8"))
    return d


def eval_queries(arm_names, queries, doc_ids, ks=(1, 3, 5, 10)):
    arms = {n: load_arm(n) for n in arm_names}
    out = {}
    for n, a in arms.items():
        per_q = {}
        for q in queries:
            qv = a["qvecs"][q["id"]]
            ranked = rank_docs(qv, list(zip(doc_ids, a["dvecs"])))
            per_q[q["id"]] = {"ranked": ranked,
                              **{f"r@{k}": recall_at_k(ranked, q["gold"], k)
                                 for k in ks}}
        agg = {f"r@{k}": sum(v[f"r@{k}"] for v in per_q.values()) / len(per_q)
               for k in ks}
        out[n] = {"per_query": per_q, "mean": agg}
    return out


if __name__ == "__main__":
    if sys.argv[1] == "--build":
        build()

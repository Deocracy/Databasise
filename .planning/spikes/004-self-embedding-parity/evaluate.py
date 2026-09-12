"""Head-to-head recall eval (CPU only, numpy-free stdlib).

Usage: evaluate.py <run_name> <arm1,arm2,...> [--head <head.json>]
Merges results/<arm>_{docs,q}.json, computes recall@k on gold + self queries,
writes results/<run_name>_report.json, logs to logs/<run_name>.jsonl.
With --head: apply a linear head (matrix W + bias b) to the FIRST arm's vectors
before ranking; that arm is reported as '<arm>+head'.
"""
import json
import sys
from pathlib import Path

from common import SPIKE_DIR, rank_docs, recall_at_k, log, norm

RES = SPIKE_DIR / "results"
IN = SPIKE_DIR / "inputs"
KS = (1, 3, 5, 10)


def load_vecs(path):
    d = json.load(open(path, encoding="utf-8"))
    return d["ids"], d["vecs"]


def apply_head(vecs, head):
    W, b = head["W"], head["b"]
    out = []
    for v in vecs:
        out.append([sum(v[i] * W[i][j] for i in range(len(v))) + b[j]
                    for j in range(len(b))])
    return out


def main():
    run_name = sys.argv[1]
    arms = sys.argv[2].split(",")
    head = None
    if "--head" in sys.argv:
        head = json.load(open(sys.argv[sys.argv.index("--head") + 1], encoding="utf-8"))

    doc_ids, _ = load_vecs(RES / f"{arms[0]}_docs.json")
    gold = json.load(open(IN / "queries_gold.json", encoding="utf-8"))
    selfq = json.load(open(IN / "queries_self.json", encoding="utf-8"))
    queries = ([{"qid": q["id"], "question": q["question"], "gold": q["gold"],
                 "set": "gold"} for q in gold]
               + [{"qid": "self:" + q["id"], "question": q["question"],
                   "gold": q["gold"], "set": "self"} for q in selfq])

    report = {"arms": {}, "queries": [q["qid"] for q in queries]}
    for n in arms:
        dids, dvecs = load_vecs(RES / f"{n}_docs.json")
        assert dids == doc_ids, f"doc order drift in {n}"
        qids, qvecs = load_vecs(RES / f"{n}_q.json")
        qmap = dict(zip(qids, qvecs))
        label = n
        if head is not None and n == arms[0]:
            dvecs = apply_head(dvecs, head)
            qmap = {k: apply_head([v], head)[0] for k, v in qmap.items()}
            label = n + "+head"
        per_q, per_set = {}, {"gold": [], "self": []}
        for q in queries:
            ranked = rank_docs(qmap[q["qid"]], list(zip(doc_ids, dvecs)))
            r = {f"r@{k}": recall_at_k(ranked, q["gold"], k) for k in KS}
            r["rank_of_first_gold"] = min(ranked.index(g) for g in q["gold"]) + 1
            per_q[q["qid"]] = r
            per_set[q["set"]].append(r)
        agg = {}
        for s, rows in per_set.items():
            agg[s] = {f"r@{k}": sum(x[f"r@{k}"] for x in rows) / len(rows)
                      for k in KS}
            agg[s]["mrr"] = sum(1.0 / x["rank_of_first_gold"] for x in rows) / len(rows)
        report["arms"][label] = {"per_query": per_q, "agg": agg}
        log(run_name, "arm_scored", arm=label,
            **{f"gold_r@{k}": round(agg['gold'][f'r@{k}'], 4) for k in KS},
            **{f"self_r@{k}": round(agg['self'][f'r@{k}'], 4) for k in KS},
            gold_mrr=round(agg["gold"]["mrr"], 4),
            self_mrr=round(agg["self"]["mrr"], 4))

    out = RES / f"{run_name}_report.json"
    json.dump(report, open(out, "w"), ensure_ascii=False)
    log(run_name, "report_saved", path=str(out))
    for label, a in report["arms"].items():
        g, s = a["agg"]["gold"], a["agg"]["self"]
        print(f"{label:12s} gold " + " ".join(f"r@{k}={g[f'r@{k}']:.2f}" for k in KS)
              + f" mrr={g['mrr']:.2f} | self "
              + " ".join(f"r@{k}={s[f'r@{k}']:.2f}" for k in KS)
              + f" mrr={s['mrr']:.2f}")


if __name__ == "__main__":
    main()

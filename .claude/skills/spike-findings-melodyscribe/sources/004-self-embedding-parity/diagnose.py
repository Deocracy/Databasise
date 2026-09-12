"""Anisotropy + norm diagnostics per arm (CPU only). Usage: diagnose.py <run_name>"""
import json
import math
import sys

from common import SPIKE_DIR, log, norm

RES = SPIKE_DIR / "results"
IN = SPIKE_DIR / "inputs"
run_name = sys.argv[1]


def stats(vecs):
    Vn = [norm(v) for v in vecs]
    n = len(Vn)
    cos = [sum(a * b for a, b in zip(Vn[i], Vn[j]))
           for i in range(n) for j in range(i + 1, n)]
    norms = [math.sqrt(sum(x * x for x in v)) for v in vecs]
    return {"mean_pair_cos": sum(cos) / len(cos), "min_pair_cos": min(cos),
            "max_pair_cos": max(cos),
            "mean_norm": sum(norms) / len(norms),
            "min_norm": min(norms), "max_norm": max(norms)}


for arm in ["armA", "armB", "armB2", "armBplain"]:
    try:
        d = json.load(open(RES / f"{arm}_docs.json", encoding="utf-8"))
        q = json.load(open(RES / f"{arm}_q.json", encoding="utf-8"))
    except FileNotFoundError:
        continue
    ds, qs = stats(d["vecs"]), stats(q["vecs"])
    # query-to-doc centroid alignment: mean cos of each query to doc mean
    Vn = [norm(v) for v in d["vecs"]]
    dim = len(Vn[0])
    centroid = norm([sum(Vn[i][j] for i in range(len(Vn))) / len(Vn)
                     for j in range(dim)])
    qn = [norm(v) for v in q["vecs"]]
    q2c = [sum(a * b for a, b in zip(v, centroid)) for v in qn]
    rec = {"arm": arm, "dim": dim,
           "doc_pair_cos": round(ds["mean_pair_cos"], 4),
           "doc_pair_cos_min": round(ds["min_pair_cos"], 4),
           "query_pair_cos": round(qs["mean_pair_cos"], 4),
           "mean_query_to_doc_centroid": round(sum(q2c) / len(q2c), 4)}
    log(run_name, "anisotropy", **rec)
    print(f"{arm:10s} dim={dim} doc_pair_cos={rec['doc_pair_cos']:.3f} "
          f"(min {rec['doc_pair_cos_min']:.3f}) q_pair_cos={rec['query_pair_cos']:.3f} "
          f"q2centroid={rec['mean_query_to_doc_centroid']:.3f}")

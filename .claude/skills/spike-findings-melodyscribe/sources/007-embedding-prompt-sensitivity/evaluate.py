"""Head-to-head recall eval for spike 007 (CPU only, stdlib).

Usage: evaluate.py <run_name> <emb_vecs.json> <gen_vecs.json> [--det <emb_rep2> <gen_rep2>]
Writes results/<run_name>_report.json, logs to logs/<run_name>.jsonl.
With --det: max abs element diff between rep1 and rep2 vecs (determinism check).
"""
import datetime
import json
import math
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
IN = SPIKE_DIR / "inputs"
RES = SPIKE_DIR / "results"
LOGS = SPIKE_DIR / "logs"

EMB_DESIGNS = {
    "E01 none": ("d:bare", "q:bare"),
    "E02 vendor-q": ("d:bare", "q:vendor"),
    "E03 task-q": ("d:bare", "q:task"),
    "E04 wrong-q": ("d:bare", "q:wrong"),
    "E05 both": ("d:instr", "q:task"),
    "E06 titled": ("d:title", "q:bare"),
}
GEN_DESIGNS = {
    "G01 none": ("d:bareM", "q:bareM"),
    "G07 sys-prefix": ("d:sysM", "q:bareM"),
    "G07 task-prefix": ("d:taskM", "q:bareM"),
    "G08 eol": ("d:eol", "q:bareM"),
    "G08 about": ("d:about", "q:bareM"),
    "G06 titled": ("d:titleM", "q:bareM"),
}
KS = (1, 3, 10)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def log(run_name, event, **fields):
    LOGS.mkdir(parents=True, exist_ok=True)
    rec = {"ts": now_iso(), "run": run_name, "event": event, **fields}
    with open(LOGS / f"{run_name}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def norm(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))


def load_vecs(path):
    d = json.load(open(path, encoding="utf-8"))
    return {i: v for i, v in zip(d["ids"], d["vecs"])}


def rank(query_vec, doc_items):
    q = norm(query_vec)
    scored = sorted(((cos(q, norm(v)), did) for did, v in doc_items), reverse=True)
    return [did for _, did in scored], [s for s, _ in scored]


def recall_at_k(ranked, gold, k):
    return len(set(ranked[:k]) & set(gold)) / len(gold)


def rr(ranked, gold):
    for i, did in enumerate(ranked):
        if did in set(gold):
            return 1.0 / (i + 1)
    return 0.0


def main():
    run_name, emb_path, gen_path = sys.argv[1:4]
    det = sys.argv.index("--det") if "--det" in sys.argv else None
    emb, gen = load_vecs(emb_path), load_vecs(gen_path)
    meta = json.load(open(IN / "meta.json", encoding="utf-8"))
    queries = meta["queries"]
    doc_ids = sorted({q["doc"] for q in queries})
    keyword_ids = {q["id"] for q in queries if q["id"].endswith("#5")}

    out = {"designs": {}}
    for design, (dp, qp) in {**EMB_DESIGNS, **GEN_DESIGNS}.items():
        V = emb if design.startswith("E") else gen
        doc_items = [(did, V[f"{dp}:{did}"]) for did in doc_ids]
        # anisotropy: mean pairwise doc cosine (upper triangle)
        nv = [norm(v) for _, v in doc_items]
        pair = [cos(nv[i], nv[j]) for i in range(len(nv)) for j in range(i + 1, len(nv))]
        aniso = sum(pair) / len(pair)
        res = {"aniso": aniso, "sets": {}}
        qvec = {q["id"]: V[f"{qp}:{q['id']}"] for q in queries}
        # query-doc gap: mean gold cos minus mean non-gold cos, averaged over queries
        gaps = []
        for q in queries:
            qn = norm(qvec[q["id"]])
            gold_c = cos(qn, norm(dict(doc_items)[q["doc"]]))
            non = [cos(qn, norm(v)) for did, v in doc_items if did != q["doc"]]
            gaps.append(gold_c - sum(non) / len(non))
        res["gap"] = sum(gaps) / len(gaps)
        for sname, qsub in (("full", queries),
                            ("nl", [q for q in queries if q["id"] not in keyword_ids]),
                            ("keyword", [q for q in queries if q["id"] in keyword_ids])):
            agg = {f"r@{k}": 0.0 for k in KS}
            mrr = 0.0
            for q in qsub:
                ranked, _ = rank(qvec[q["id"]], doc_items)
                for k in KS:
                    agg[f"r@{k}"] += recall_at_k(ranked, [q["doc"]], k)
                mrr += rr(ranked, [q["doc"]])
            n = len(qsub)
            res["sets"][sname] = {"n": n, **{k: v / n for k, v in agg.items()},
                                  "mrr": mrr / n}
        # gold-2 HotpotQA queries (2 gold docs each)
        gres = {}
        for g in meta["gold2"]:
            gq = f"g:{qp[2:] if design.startswith('E') else 'bareM'}:{g['id']}"
            ranked, _ = rank(V[gq], doc_items)
            gres[g["id"]] = {f"r@{k}": recall_at_k(ranked, g["gold"], k) for k in KS}
            gres[g["id"]]["rr_first"] = rr(ranked, g["gold"])
        res["gold2"] = gres
        out["designs"][design] = res

    if det is not None:
        emb2, gen2 = load_vecs(sys.argv[det + 1]), load_vecs(sys.argv[det + 2])
        for label, a, b in (("emb", emb, emb2), ("gen", gen, gen2)):
            worst = 0.0
            assert set(a) == set(b), f"det id mismatch {label}"
            for k in a:
                worst = max(worst, max(abs(x - y) for x, y in zip(a[k], b[k])))
            out[f"determinism_max_abs_diff_{label}"] = worst

    RES.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(RES / f"{run_name}_report.json", "w", encoding="utf-8"), indent=1)
    log(run_name, "evaluated", designs=len(out["designs"]),
        **{k: v for k, v in out.items() if k.startswith("determinism")})
    # console head-to-head table (full set)
    print(f"{'design':18s} {'r@1':>6s} {'r@3':>6s} {'r@10':>6s} {'MRR':>6s} "
          f"{'aniso':>7s} {'gap':>6s}")
    for design in list(EMB_DESIGNS) + list(GEN_DESIGNS):
        s = out["designs"][design]["sets"]["full"]
        print(f"{design:18s} {s['r@1']:6.3f} {s['r@3']:6.3f} {s['r@10']:6.3f} "
              f"{s['mrr']:6.3f} {out['designs'][design]['aniso']:7.4f} "
              f"{out['designs'][design]['gap']:6.4f}")


if __name__ == "__main__":
    main()

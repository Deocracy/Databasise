"""Spike 010 retrieval eval (CPU only; MELODYSCRIBE_PY for faiss/numpy).

Modes per SPEC recall-time I/O, on identical inputs (118 queries: 116
teacher queries-v1 with 1 gold doc each + 2 HotpotQA with 2 gold docs):
  vec2b / vec06 : faiss top-10 on the whole-doc index (split index: rank
                  sections, map to doc by max section score).
  graph         : seed nodes whose normalised name is a substring of the
                  normalised query (or shares a word of length >= 4);
                  doc score = seed evidence-links (1.0) + 1-hop neighbour
                  evidence-links (0.5). Rank desc, tie-break doc id.
  sql           : rows whose normalised subject is a substring of the
                  normalised query or vice versa; doc score = #rows.
  fused         : candidates = vec06 top-10 ∪ graph docs ∪ sql docs;
                  score = 1/(vec_rank+1) + 0.15*graph_hit + 0.15*sql_hit.

Store sets Vs in {STU,SPL,TEA} x {write,revise} (batched writes only;
streamed==batched is checked by checksum in build_stores).

Metrics: recall@1/@3/@10 (HotpotQA: |top∩gold|/|gold|), MRR, median
retrieval latency (3 reps), payload words (recall-list JSON + fenced
results block of top-3 docs truncated to 200 chars each; tokens =
words x FERTILITY, fertility measured from 003 student prompt_tokens).

Writes results/retrieval.json + logs/retrieval-<utc>.jsonl.
"""

from __future__ import annotations

import datetime
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s10_common as C  # noqa: E402

FERTILITY = 1.71  # MiniCPM tokens per whitespace word on the exact D0
# prompt bytes: 6736 prompt_tokens / 3930 words over the 20 whole-unit
# prompts (003 students/minicpm2b.json prompt_tokens vs student_prompt
# words in s10_common, measured 2026-09-12, CPU, no GPU).
KS = (1, 3, 10)


def load_all():
    res = C.HERE / "results"
    vec = C.HERE / "vectors"
    onepass = json.loads(next(vec.glob("whole_onepass.json")).read_text())
    emb06 = json.loads(next(vec.glob("*_embed06.json")).read_text())
    v06 = {i: v for i, v in zip(emb06["ids"], emb06["vecs"])}
    queries = [(q["id"], q["q"], [q["doc"]]) for q in C.load_queries_v1()]
    queries += [(q["id"], q["question"], sorted(q["gold_document_ids"]))
                for q in C.load_hotpot_queries()]
    return res, queries, onepass, v06


def norm_rank(query_vec, doc_ids, doc_mat):
    import numpy as np

    q = np.array(query_vec, dtype=np.float32)
    q /= (np.linalg.norm(q) or 1)
    m = doc_mat.copy()
    m /= (np.linalg.norm(m, axis=1, keepdims=True) + 1e-12)
    s = (m @ q).tolist()
    order = sorted(range(len(doc_ids)), key=lambda i: -s[i])
    return [doc_ids[i] for i in order], {doc_ids[i]: float(s[i]) for i in order}


def load_index(name):
    import faiss
    import numpy as np

    res = C.HERE / "results"
    idx = faiss.read_index(str(res / f"faiss_{name}.index"))
    ids = json.loads((res / f"faiss_{name}_ids.json").read_text())
    mat = np.array([idx.reconstruct(i) for i in range(len(ids))],
                   dtype=np.float32)
    return ids, mat


def graph_scores(graph, query):
    nq = C.norm(query)
    qwords = {w for w in nq.split() if len(w) >= 4}
    seeds = set()
    for key, node in graph["nodes"].items():
        hit = False
        for name in node["names"]:
            nn = C.norm(name)
            if nn and (nn in nq or nq in nn):
                hit = True
                break
            if not hit and qwords and set(nn.split()) & qwords and len(nn) >= 4:
                # word-overlap only for multiword names (avoid "ed" storms)
                if len(nn.split()) > 1:
                    hit = True
                    break
        if hit:
            seeds.add(key)
    # 1-hop neighbours
    nbrs = set()
    for e in graph["edges"]:
        if e["s"] in seeds:
            for key, node in graph["nodes"].items():
                for name in node["names"]:
                    if C.norm(e["o"]) == C.norm(name) or C.norm(name) in C.norm(e["o"]):
                        nbrs.add(key)
    scores = {}
    for e in graph["edges"]:
        if e["s"] in seeds:
            scores[e["doc"]] = scores.get(e["doc"], 0) + 1.0
        elif e["s"] in nbrs:
            scores[e["doc"]] = scores.get(e["doc"], 0) + 0.5
    # seed-name docs: nodes carry doc lists
    for key in seeds:
        for d in graph["nodes"][key]["docs"]:
            scores[d] = scores.get(d, 0) + 1.0
    return scores, sorted(seeds)


def sql_scores(con, query):
    nq = C.norm(query)
    scores = {}
    subjects = {}
    for (subj, doc) in con.execute("SELECT DISTINCT subject, doc FROM facts"):
        ns = C.norm(subj)
        if ns and (ns in nq or nq in ns):
            scores[doc] = scores.get(doc, 0) + 1
            subjects.setdefault(doc, []).append(subj)
    return scores, subjects


def rank_from_scores(scores, universe):
    return sorted(universe, key=lambda d: (-scores.get(d, 0), d))


def payload_words(query, vec_rank, graph_seeds, sql_subjects, doc_texts):
    recall_obj = {"recall": [
        {"source": "vector", "k": 8},
        {"source": "graph", "seeds": graph_seeds[:2], "hops": 1},
        {"source": "sql", "attribute": "auto",
         "subject": (sql_subjects[0] if sql_subjects else "")}]}
    block = ["```results"]
    for d in vec_rank[:3]:
        block.append(f"[{d}] {doc_texts[d][:200]}")
    block.append("```")
    text = json.dumps(recall_obj) + "\n" + "\n".join(block)
    return len(text.split())


def main() -> None:
    import datetime

    res, queries, onepass, v06 = load_all()
    log_fh = open(res.parent / f"logs/retrieval-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl", "w")
    docs, _ = C.load_corpus()
    doc_texts = dict(docs)
    universe = sorted(doc_texts)

    q06 = {i[2:]: v06[i] for i in v06 if i.startswith("q|")}
    q2b = onepass.get("queries", {})
    assert len(q06) == len(queries), (len(q06), len(queries))
    assert len(q2b) == len(queries), (len(q2b), len(queries))

    ids06, mat06 = load_index("06_whole")
    ids2b, mat2b = load_index("2b_whole")
    try:
        ids06s, mat06s = load_index("06_split")
        split_map06 = json.loads((res / "split_docmap.json").read_text())["06"]
        has_split = True
    except Exception:
        has_split = False

    variants = []
    for v in ("STU", "SPL", "TEA"):
        for m in ("write", "revise"):
            g = res / f"graph_{v}-{m}.json"
            f = res / f"facts_{v}-{m}.sqlite"
            if g.exists():
                variants.append((f"{v}-{m}",
                                 json.loads(g.read_text()), str(f)))

    report = {"n_queries": len(queries), "modes": {}}

    def score_ranking(ranked):
        per = []
        for qid, _, gold in queries:
            r = ranked[qid]
            per.append({"qid": qid, "gold": gold,
                        "r": {f"r@{k}": (len(set(r[:k]) & set(gold)) / len(gold))
                              for k in KS},
                        "first": min((r.index(g) for g in gold if g in r),
                                     default=10**9) + 1})
        agg = {f"r@{k}": sum(p["r"][f"r@{k}"] for p in per) / len(per)
               for k in KS}
        agg["mrr"] = sum(1.0 / p["first"] if p["first"] < 10**9 else 0.0
                         for p in per) / len(per)
        return agg, per

    # vector modes (store-independent)
    vec_rank06, vec_rank2b, vec_rank06s = {}, {}, {}
    for qid, _, _ in queries:
        ranked, _ = norm_rank(q06[qid], ids06, mat06)
        # map whole sec ids ("doc#s1") -> doc
        vec_rank06[qid] = [d.split("#")[0] for d in ranked]
        ranked2, _ = norm_rank(q2b[qid], ids2b, mat2b)
        vec_rank2b[qid] = [d.split("#")[0] for d in ranked2]
        if has_split:
            ranked3, sc3 = norm_rank(q06[qid], ids06s, mat06s)
            best = {}
            for s in ranked3:
                d = split_map06[s]
                best[d] = max(best.get(d, -9), sc3[s])
            vec_rank06s[qid] = sorted(best, key=lambda d: (-best[d], d))
    for name, rk in (("vec06", vec_rank06), ("vec2b", vec_rank2b)):
        agg, _ = score_ranking(rk)
        report["modes"][name] = agg
        C.emit(log_fh, "mode", mode=name, **{k: round(v, 4) for k, v in agg.items()})
    if has_split:
        agg, _ = score_ranking(vec_rank06s)
        report["modes"]["vec06_split"] = agg
        C.emit(log_fh, "mode", mode="vec06_split",
               **{k: round(v, 4) for k, v in agg.items()})

    # graph/sql/fused per store set
    for vname, graph, fpath in variants:
        con = sqlite3.connect(fpath)
        g_rank, s_rank, f_rank = {}, {}, {}
        lat = {"graph": [], "sql": [], "fused": []}
        pw = []
        seeds_of, subj_of = {}, {}
        for qid, qtext, _ in queries:
            t0 = time.perf_counter()
            gs, seeds = graph_scores(graph, qtext)
            lat["graph"].append(time.perf_counter() - t0)
            g_rank[qid] = rank_from_scores(gs, universe)
            seeds_of[qid] = seeds
            t0 = time.perf_counter()
            ss, subjs = sql_scores(con, qtext)
            lat["sql"].append(time.perf_counter() - t0)
            flat = sorted({s for v in subjs.values() for s in v})
            subj_of[qid] = flat
            s_rank[qid] = rank_from_scores(ss, universe)
            t0 = time.perf_counter()
            vr = vec_rank06[qid]
            vrank = {d: i for i, d in enumerate(vr)}
            cand = set(vr[:10]) | set(gs) | set(ss)
            f_rank[qid] = sorted(
                cand, key=lambda d: (-(1.0 / (vrank.get(d, 99) + 1)
                                       + 0.15 * (d in gs) + 0.15 * (d in ss)), d))
            lat["fused"].append(time.perf_counter() - t0)
            pw.append(payload_words(qtext, vr, seeds, flat, doc_texts))
        con.close()
        for mname, rk in (("graph", g_rank), ("sql", s_rank), ("fused", f_rank)):
            agg, _ = score_ranking(rk)
            key = f"{mname}_{vname}"
            agg["lat_ms_med"] = round(sorted(lat[mname])[len(lat[mname]) // 2] * 1000, 3)
            report["modes"][key] = agg
            C.emit(log_fh, "mode", mode=key,
                   **{k: (round(v, 4) if isinstance(v, float) else v)
                      for k, v in agg.items()})
        report["modes"][f"payload_{vname}"] = {
            "words_mean": round(sum(pw) / len(pw), 1),
            "tokens_mean": round(sum(pw) / len(pw) * FERTILITY, 1)}

    (res / "retrieval.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    sys.exit(main())

"""Spike 010 store builder (CPU only; MELODYSCRIBE_PY for faiss/numpy).

Inputs: vectors/*_onepass.json (fresh 2B student decodes + embeddings),
  003 teacher.json (ceiling labels), *_embed06.json (0.6B vectors).
Proof: spike 001 + spike 003 resolve, read-only (via s10_common).

Ordering arms (identical inputs throughout):
  write timing: streamed (file each op as Proof passes it) vs batched
    (collect per section, file at section end). Expectation: identical
    stores (checksum), timing delta ~ 0 single-threaded.
  entity merge: write (node key = normalised name at file time) vs revise
    (node key = raw string, then a post-pass merges keys whose norm
    collides, rewiring edges). Expectation: revise exposes the alias
    count; merged graph == write graph.

Store variants: STU (fresh one-pass whole-unit student ops),
  SPL (fresh one-pass split-section student ops),
  TEA (teacher.json labels, ceiling).

Graph: stdlib dicts (networkx is absent from .planning/spikes/.venv;
  production target is Cozo through Databasise -- stated, not built).
SQL: sqlite3 facts(subject, attribute, value, value_type, quote, doc,
  section, span_start, span_end).
Vectors: faiss IndexFlatIP on L2-normalised vectors (whole + split).

Writes results/graph_<V>.json, results/facts_<V>.sqlite,
results/faiss_*.index + *_ids.json, logs/stores-<utc>.jsonl.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s10_common as C  # noqa: E402


def subj_of(op):
    return op.get("s", op.get("subject", ""))


def pred_of(op):
    return op.get("p", op.get("attribute", ""))


def val_of(op):
    return op.get("o", op.get("value", ""))


def load_student_ops(onepass_path):
    """Proof over fresh student decodes. Returns list of section records:
    {sec, doc, content, passed:[ops with _span], failed}."""
    rec = json.loads(Path(onepass_path).read_text())
    out = []
    for sec, e in rec["sections"].items():
        if "text" not in e:
            continue
        proof = C.prove_section(e["text"], e["content"])
        out.append({"sec": sec, "doc": e["doc"], "content": e["content"],
                    "passed": proof["passed"], "failed": proof["failed"],
                    "how": proof["how"]})
    return out


def load_teacher_ops():
    t = json.loads((C.SPIKE003 / "teacher.json").read_text())
    docs, _ = C.load_corpus()
    text_of = dict(docs)
    out = []
    for doc_id in sorted(t["labels"]):
        content = text_of[doc_id]
        for op in t["labels"][doc_id]["ops"]:
            span = C.v02.resolve_quote(op["quote"], content)
            assert not isinstance(span, str), f"teacher quote lost: {doc_id}"
            out.append({"sec": f"{doc_id}#s1", "doc": doc_id, "content": content,
                        "passed": [{**op, "_span": [span[0], span[1]]}],
                        "failed": [], "how": "teacher"})
    # regroup per section
    by_sec = {}
    for r in out:
        by_sec.setdefault(r["sec"], []).append(r["passed"][0])
    return [{"sec": s, "doc": r[0]["doc"] if False else s.split("#")[0],
             "content": None, "passed": r, "failed": [], "how": "teacher"}
            for s, r in sorted(by_sec.items())]


def file_graph_op(nodes, edges, op, doc, sec, span, merge_at_write):
    s, p, o = subj_of(op), pred_of(op), val_of(op)
    key_s = C.norm(s) if merge_at_write else s
    if op["target"] == "graph":
        for key, name in ((key_s, s),):
            n = nodes.setdefault(key, {"names": [], "docs": [], "types": []})
            if name not in n["names"]:
                n["names"].append(name)
            if doc not in n["docs"]:
                n["docs"].append(doc)
        edges.append({"s": key_s, "p": p, "o": o, "doc": doc, "sec": sec,
                      "span": span, "o_type": op.get("o_type", ""),
                      "s_type": op.get("s_type", "")})


def file_sql_op(rows, op, doc, sec, span):
    if op["target"] == "sql":
        rows.append({"subject": subj_of(op), "attribute": pred_of(op),
                     "value": val_of(op), "value_type": op["value_type"],
                     "quote": op["quote"], "doc": doc, "sec": sec,
                     "span_start": span[0], "span_end": span[1]})


def build_variant(sections, write_mode, merge_at_write, log_fh, label):
    """sections: list of {sec, doc, content, passed}. Returns stores."""
    nodes, edges, rows = {}, [], []
    t0 = time.perf_counter()
    if write_mode == "streamed":
        for r in sections:
            for op in r["passed"]:
                file_graph_op(nodes, edges, op, r["doc"], r["sec"],
                              op["_span"], merge_at_write)
                file_sql_op(rows, op, r["doc"], r["sec"], op["_span"])
    else:  # batched: per-section buffer, file at section end
        for r in sections:
            buf = list(r["passed"])
            for op in buf:
                file_graph_op(nodes, edges, op, r["doc"], r["sec"],
                              op["_span"], merge_at_write)
                file_sql_op(rows, op, r["doc"], r["sec"], op["_span"])
    wall = time.perf_counter() - t0
    merged = 0
    if not merge_at_write:
        # revise pass: merge raw keys whose norm collides, rewire edges
        groups = {}
        for k in list(nodes):
            groups.setdefault(C.norm(k), []).append(k)
        remap = {}
        for nk, ks in groups.items():
            if len(ks) > 1:
                merged += len(ks) - 1
                keep = sorted(ks)[0]
                for k in ks:
                    remap[k] = keep
                nk_node = {"names": [], "docs": [], "types": []}
                for k in ks:
                    for nm in nodes[k]["names"]:
                        if nm not in nk_node["names"]:
                            nk_node["names"].append(nm)
                    for d in nodes[k]["docs"]:
                        if d not in nk_node["docs"]:
                            nk_node["docs"].append(d)
                for k in ks:
                    del nodes[k]
                nodes[keep] = nk_node
        for e in edges:
            if e["s"] in remap:
                e["s"] = remap[e["s"]]
    C.emit(log_fh, "stores_built", label=label, write_mode=write_mode,
           merge="write" if merge_at_write else "revise",
           wall_s=round(wall, 4), nodes=len(nodes), edges=len(edges),
           sql_rows=len(rows), merged_aliases=merged)
    return {"nodes": nodes, "edges": edges, "sql": rows,
            "merged_aliases": merged, "wall_s": wall}


def checksum(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def write_sqlite(path, rows):
    p = Path(path)
    if p.exists():
        p.unlink()
    con = sqlite3.connect(str(p))
    con.execute("CREATE TABLE facts(subject, attribute, value, value_type,"
                " quote, doc, section, span_start, span_end)")
    con.executemany(
        "INSERT INTO facts VALUES (?,?,?,?,?,?,?,?,?)",
        [(r["subject"], r["attribute"], r["value"], r["value_type"],
          r["quote"], r["doc"], r["sec"], r["span_start"], r["span_end"])
         for r in rows])
    con.commit()
    con.close()


def build_faiss(vecs_by_id, index_path, ids_path):
    import numpy as np
    import faiss

    ids = sorted(vecs_by_id)
    mat = np.array([vecs_by_id[i] for i in ids], dtype=np.float32)
    faiss.normalize_L2(mat)
    idx = faiss.IndexFlatIP(mat.shape[1])
    idx.add(mat)
    faiss.write_index(idx, str(index_path))
    Path(ids_path).write_text(json.dumps(ids) + "\n")
    return len(ids), mat.shape[1]


def main() -> None:
    import datetime

    res_dir = C.HERE / "results"
    log_dir = C.HERE / "logs"
    res_dir.mkdir(exist_ok=True)
    log_dir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_fh = open(log_dir / f"stores-{stamp}.jsonl", "w")

    vec_dir = C.HERE / "vectors"
    onepass_whole = sorted(vec_dir.glob("*_onepass.json"))
    assert onepass_whole, "run gpu_ingest onepass first"
    whole_path = [p for p in onepass_whole if "whole" in p.name][0]
    split_paths = [p for p in onepass_whole if "split" in p.name]
    split_path = split_paths[0] if split_paths else None

    stu = load_student_ops(str(whole_path))
    variants = {"STU": stu}
    if split_path:
        variants["SPL"] = load_student_ops(str(split_path))
    variants["TEA"] = load_teacher_ops()

    n_passed = {k: sum(len(r["passed"]) for r in v) for k, v in variants.items()}
    n_failed = {k: sum(len(r["failed"]) for r in v) for k, v in variants.items()}
    C.emit(log_fh, "proof_summary", passed=n_passed, failed=n_failed)
    print("proof passed/failed:", n_passed, n_failed)

    report = {"proof": {"passed": n_passed, "failed": n_failed}, "stores": {}}
    for vname, sections in variants.items():
        for wmode in ("streamed", "batched"):
            for mname, at_write in (("write", True), ("revise", False)):
                label = f"{vname}-{wmode}-{mname}"
                st = build_variant(sections, wmode, at_write, log_fh, label)
                cs = checksum({"nodes": st["nodes"], "edges": st["edges"],
                               "sql": st["sql"]})
                report["stores"][label] = {
                    "nodes": len(st["nodes"]), "edges": len(st["edges"]),
                    "sql_rows": len(st["sql"]),
                    "merged_aliases": st["merged_aliases"],
                    "wall_s": round(st["wall_s"], 4), "checksum": cs}
                if wmode == "batched":
                    (res_dir / f"graph_{vname}-{mname}.json").write_text(
                        json.dumps({"nodes": st["nodes"], "edges": st["edges"]},
                                   ensure_ascii=False) + "\n")
                    write_sqlite(res_dir / f"facts_{vname}-{mname}.sqlite",
                                 st["sql"])

    # faiss indexes from the embedding arms (identical inputs for every arm)
    rec_w = json.loads(whole_path.read_text())
    vecs_whole_2b = {s: e["emb"] for s, e in rec_w["sections"].items()
                     if "emb" in e}
    doc_of = {s: e["doc"] for s, e in rec_w["sections"].items() if "emb" in e}
    emb06 = json.loads(next(vec_dir.glob("*_embed06.json")).read_text())
    v06 = {i: v for i, v in zip(emb06["ids"], emb06["vecs"])}
    vecs_whole_06 = {i[4:]: v06[i] for i in v06 if i.startswith("sec|")
                     and i[4:].endswith("#s1")}
    n, d = build_faiss(vecs_whole_2b, res_dir / "faiss_2b_whole.index",
                       res_dir / "faiss_2b_whole_ids.json")
    C.emit(log_fh, "faiss", index="2b_whole", n=n, dim=d)
    n, d = build_faiss(vecs_whole_06, res_dir / "faiss_06_whole.index",
                       res_dir / "faiss_06_whole_ids.json")
    C.emit(log_fh, "faiss", index="06_whole", n=n, dim=d)
    if split_path:
        rec_s = json.loads(split_path.read_text())
        vecs_split_2b = {s: e["emb"] for s, e in rec_s["sections"].items()
                         if "emb" in e}
        doc_of_s = {s: e["doc"] for s, e in rec_s["sections"].items()
                    if "emb" in e}
        vecs_split_06 = {i[4:]: v06[i] for i in v06 if i.startswith("sec|")
                         and not i[4:].endswith("#s1")}
        n, d = build_faiss(vecs_split_2b, res_dir / "faiss_2b_split.index",
                           res_dir / "faiss_2b_split_ids.json")
        C.emit(log_fh, "faiss", index="2b_split", n=n, dim=d)
        n, d = build_faiss(vecs_split_06, res_dir / "faiss_06_split.index",
                           res_dir / "faiss_06_split_ids.json")
        C.emit(log_fh, "faiss", index="06_split", n=n, dim=d)
        (res_dir / "split_docmap.json").write_text(json.dumps(
            {"2b": doc_of_s,
             "06": {s: s.split("#")[0] for s in vecs_split_06}}) + "\n")
    (res_dir / "whole_docmap.json").write_text(json.dumps(doc_of) + "\n")
    (res_dir / "stores_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    sys.exit(main())

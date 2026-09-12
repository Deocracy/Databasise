"""Spike 009 retrieval: embed queries with Qwen3-Embedding-0.6B, top-10 Faiss.

GPU process (under flock via run.sh). One model load, then:
  1. verify: embed([q1,q2]) batched == embed(q1), embed(q2) single (cos ~1).
  2. index: section vectors for all corpus paragraphs -> Faiss IndexFlatIP.
  3. sanity: recall@10 on shared/queries-v1.json (gold doc id in top-10).
  4. sweep: N in 1,4,16,64,256,1024 queries (cycled) at batch K in
     1,4,16,64 (K queries per embed() call); faiss top-10 per query timed
     separately. Per-query latencies + q/s + VRAM per cell.
"""
from __future__ import annotations
import datetime
import json
import math
import os
import sys
import time

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
from batchserve import emit, vram_used_mb  # noqa: E402

MODELS = os.environ["MELODYSCRIBE_MODELS"]
EMB_MODEL = os.path.join(MODELS, "Qwen3-Embedding-0.6B-Q8_0.gguf")
NS = [1, 4, 16, 64, 256, 1024]
KS = [1, 4, 16, 64]


def cos(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def load_sections() -> tuple[list[dict], str]:
    import importlib.util
    path = os.path.normpath(os.path.join(
        D, "..", "..", "..", "databasise", "parity", "corpus.py"))
    spec = importlib.util.spec_from_file_location("ms9_corpus", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ms9_corpus"] = mod
    spec.loader.exec_module(mod)
    snap = mod.load_snapshot()
    secs = []
    for d in sorted(snap.documents, key=lambda x: x.id):
        body = d.text.split("\n", 1)[1] if "\n" in d.text else d.text
        for p in [x.strip().replace("\n", " ") for x in body.split("\n\n")]:
            if len(p) >= 200:
                secs.append({"doc_id": d.id, "text": p[:800]})
    return secs, snap.corpus_hash


def load_queries() -> tuple[list[dict], list[str]]:
    with open(os.path.join(D, "..", "shared", "queries-v1.json")) as f:
        q = json.load(f)
    return q["queries"], q["test_document_ids"]


def main() -> int:
    from llama_cpp import Llama
    import numpy as np
    import faiss

    log = open(os.path.join(D, "logs", "retrieve.jsonl"), "w")
    secs, chash = load_sections()
    queries, test_docs = load_queries()
    emit(log, "inputs", corpus_hash=chash, sections=len(secs),
         queries=len(queries), test_docs=test_docs)

    t0 = time.perf_counter()
    llm = Llama(model_path=EMB_MODEL, n_gpu_layers=-1, n_ctx=2048,
                n_batch=2048, embedding=True, verbose=False)
    emit(log, "load", seconds=round(time.perf_counter() - t0, 3),
         dim=llm.n_embd(), pooling=llm.pooling_type(),
         vram_mb=vram_used_mb())

    # 1. verify batched == single
    q0, q1 = "query: Who directed the movie?", "query: Where was he born?"
    t0 = time.perf_counter()
    b = llm.embed([q0, q1])
    t_batch = time.perf_counter() - t0
    s0 = llm.embed(q0)
    s1 = llm.embed(q1)
    emit(log, "verify_batch", ok=True,
         cos0=round(cos(b[0], s0), 6), cos1=round(cos(b[1], s1), 6),
         batch_s=round(t_batch, 4))

    # 2. index sections (batched through the public API)
    t0 = time.perf_counter()
    texts = [s["text"] for s in secs]
    vecs = []
    for i in range(0, len(texts), 64):
        vecs.extend(llm.embed(texts[i:i + 64]))
    index_s = time.perf_counter() - t0
    M = np.array(vecs, dtype=np.float32)
    M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-12
    index = faiss.IndexFlatIP(M.shape[1])
    index.add(M)
    emit(log, "index", sections=len(secs), seconds=round(index_s, 3),
         vram_mb=vram_used_mb())

    # 3. recall@10 sanity (gold doc id anywhere in top-10 section hits)
    hits = 0
    tried = 0
    t0 = time.perf_counter()
    for q in queries:
        v = np.array(llm.embed("query: " + q["q"]),
                     dtype=np.float32).reshape(1, -1)
        v /= np.linalg.norm(v) + 1e-12
        _, I = index.search(v, 10)
        docs = {secs[i]["doc_id"] for i in I[0]}
        tried += 1
        hits += q["doc"] in docs
    sanity_s = time.perf_counter() - t0
    emit(log, "recall_sanity", tried=tried, hits=hits,
         recall10=round(hits / tried, 4), seconds=round(sanity_s, 3))

    # 4. sweep: cycle queries to fill N, batch K per embed() call
    qtexts = ["query: " + q["q"] for q in queries]
    for N in NS:
        reqs = [qtexts[i % len(qtexts)] for i in range(N)]
        for K in [k for k in KS if k <= max(N, 1)]:
            if K > N:
                continue
            lats: list[float] = []
            t0 = time.perf_counter()
            allv = []
            for i in range(0, N, K):
                b0 = time.perf_counter()
                chunk = reqs[i:i + K]
                allv.extend(llm.embed(chunk))
                b1 = time.perf_counter() - b0
                for _ in chunk:
                    lats.append(b1 / len(chunk))
            t_emb = time.perf_counter() - t0
            t1 = time.perf_counter()
            for v in allv:
                vv = np.array(v, dtype=np.float32).reshape(1, -1)
                vv /= np.linalg.norm(vv) + 1e-12
                index.search(vv, 10)
            t_faiss = time.perf_counter() - t1
            wall = t_emb + t_faiss
            lats_sorted = sorted(lats)
            emit(log, "cell", workload="retrieval", N=N, K=K,
                 wall_s=round(wall, 3), embed_s=round(t_emb, 3),
                 faiss_s=round(t_faiss, 4),
                 q_per_s=round(N / wall, 2),
                 ttft_p50_ms=round(lats_sorted[len(lats_sorted) // 2] * 1000, 2),
                 ttft_p95_ms=round(
                     lats_sorted[min(len(lats_sorted) - 1,
                                     int(len(lats_sorted) * 0.95))] * 1000, 2),
                 vram_mb=vram_used_mb())
    log.close()
    print("RETRIEVE DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

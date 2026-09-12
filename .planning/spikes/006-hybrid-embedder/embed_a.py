"""Arm A: Qwen3-Embedding-0.6B baseline via sentence-transformers (GPU process).

Usage: embed_a.py <run_name> [--redo-docs]
Embeds the 20 corpus docs, the queries-v1 test/train queries, and the 2
HotpotQA gold queries with BARE text (no instruction prompt -- spike 004
found prefix choice insensitive, and bare matches its GGUF arm). Writes
results/vecs_A_<run_name>.json {ids, vecs, ms_per_text, ...}.

Also writes the teacher vectors for arm C distillation:
results/teacher_A_train.json (train queries + train passages, A vectors).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import HERE, REPO, load_docs, load_gold, load_queries  # noqa: E402
from common_eval import RESULTS, emit  # noqa: E402

MODEL_DIR = REPO / ".planning" / "spikes" / ".models" / "hf" / "Qwen__Qwen3-Embedding-0.6B"


def main() -> None:
    run_name = sys.argv[1]
    from sentence_transformers import SentenceTransformer

    t0 = time.perf_counter()
    st = SentenceTransformer(str(MODEL_DIR), device="cuda")
    load_s = time.perf_counter() - t0
    dim = st.get_embedding_dimension()
    emit(run_name, "model_loaded", model="Qwen3-Embedding-0.6B-safetensors",
         dim=dim, load_s=round(load_s, 2))

    docs, corpus_hash = load_docs()
    queries, test_docs, q_hash = load_queries()
    assert corpus_hash == q_hash == "ac55d19ec162cc9abf51ddf8502436109b1439c5cbaea4cf41c448c11575d5bd"
    gold = load_gold()

    doc_ids = [d for d, _ in docs]
    doc_texts = [t for _, t in docs]
    t0 = time.perf_counter()
    doc_vecs = st.encode(doc_texts, normalize_embeddings=True,
                         show_progress_bar=False)
    doc_s = time.perf_counter() - t0

    q_texts = [q["q"] for q in queries]
    t0 = time.perf_counter()
    q_vecs = st.encode(q_texts, normalize_embeddings=True, show_progress_bar=False)
    q_s = time.perf_counter() - t0

    g_texts = [g["question"] for g in gold]
    g_vecs = st.encode(g_texts, normalize_embeddings=True, show_progress_bar=False)

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = {"arm": "A", "model": "Qwen3-Embedding-0.6B-safetensors",
           "pooling": "native:last", "prompt": "bare(none)",
           "corpus_hash": corpus_hash, "dim": dim,
           "doc_ids": doc_ids, "doc_vecs": [list(map(float, v)) for v in doc_vecs],
           "query_ids": [q["id"] for q in queries],
           "query_vecs": [list(map(float, v)) for v in q_vecs],
           "query_doc": [q["doc"] for q in queries],
           "query_split": [q["split"] for q in queries],
           "gold_ids": [g["id"] for g in gold],
           "gold_vecs": [list(map(float, v)) for v in g_vecs],
           "gold_docs": [g["gold_document_ids"] for g in gold],
           "ms_per_doc": round(doc_s / len(doc_texts) * 1000, 2),
           "ms_per_query": round(q_s / len(q_texts) * 1000, 2)}
    (RESULTS / f"vecs_A_{run_name}.json").write_text(json.dumps(out) + "\n")
    emit(run_name, "embedded", n_docs=len(doc_texts),
         ms_per_doc=out["ms_per_doc"], ms_per_query=out["ms_per_query"])

    # Teacher vectors for arm C: train queries + train passages.
    train_q = [q for q in queries if q["split"] == "train"]
    train_docs = [(d, t) for d, t in docs
                  if d not in set(test_docs)]
    assert len(train_q) == 86 and len(train_docs) == 15, \
        f"train split drift: {len(train_q)}q {len(train_docs)}d"
    tq_vecs = st.encode([q["q"] for q in train_q], normalize_embeddings=True,
                        show_progress_bar=False)
    tp_vecs = st.encode([t for _, t in train_docs], normalize_embeddings=True,
                        show_progress_bar=False)
    teach = {"model": "Qwen3-Embedding-0.6B-safetensors",
             "train_query_ids": [q["id"] for q in train_q],
             "train_query_vecs": [list(map(float, v)) for v in tq_vecs],
             "train_doc_ids": [d for d, _ in train_docs],
             "train_doc_vecs": [list(map(float, v)) for v in tp_vecs]}
    (RESULTS / "teacher_A_train.json").write_text(json.dumps(teach) + "\n")
    emit(run_name, "teacher_saved", n_q=len(train_q), n_d=len(train_docs))
    print(f"A done: dim={dim} ms/doc={out['ms_per_doc']} "
          f"ms/q={out['ms_per_query']} load={load_s:.1f}s")


if __name__ == "__main__":
    sys.exit(main())

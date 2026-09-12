"""Embed eval inputs through a Qwen3-shaped dir (merged D or gen base) (GPU).

Usage: embed_qwen.py <run_name> <model_dir> <arm_label>
Bare text, manual last-token pooling of the final hidden state, L2 norm,
bf16, greedy-free (no sampling). Same eval schema as embed_a.py vecs.
GPU lock. <model_dir> may be absolute or relative to the repo root.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import REPO, load_docs, load_gold, load_queries  # noqa: E402
from common_eval import RESULTS, emit  # noqa: E402


def main() -> None:
    run_name, model_dir, label = sys.argv[1:4]
    mp = Path(model_dir)
    if not mp.is_absolute():
        mp = REPO / model_dir
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(str(mp), trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(mp), torch_dtype=torch.bfloat16,
        trust_remote_code=True).cuda().eval()
    load_s = time.perf_counter() - t0
    emit(run_name, "model_loaded", model=label, load_s=round(load_s, 2))

    docs, corpus_hash = load_docs()
    queries, _, q_hash = load_queries()
    assert corpus_hash == q_hash
    gold = load_gold()

    @torch.no_grad()
    def encode(texts):
        vecs, t0 = [], time.perf_counter()
        for t in texts:
            ids = tok(t, return_tensors="pt",
                      truncation=True, max_length=512).to("cuda")
            h = model(**ids, output_hidden_states=True).hidden_states[-1]
            v = h[0, -1, :].float()
            vecs.append((v / v.norm()).tolist())
        return vecs, (time.perf_counter() - t0) / max(len(texts), 1) * 1000

    doc_vecs, ms_doc = encode([t for _, t in docs])
    q_vecs, ms_q = encode([q["q"] for q in queries])
    g_vecs, _ = encode([g["question"] for g in gold])
    out = {"arm": label, "model": label, "pooling": "last-token",
           "prompt": "bare(none)", "corpus_hash": corpus_hash,
           "dim": len(doc_vecs[0]),
           "doc_ids": [d for d, _ in docs], "doc_vecs": doc_vecs,
           "query_ids": [q["id"] for q in queries], "query_vecs": q_vecs,
           "query_doc": [q["doc"] for q in queries],
           "query_split": [q["split"] for q in queries],
           "gold_ids": [g["id"] for g in gold], "gold_vecs": g_vecs,
           "gold_docs": [g["gold_document_ids"] for g in gold],
           "ms_per_doc": round(ms_doc, 2), "ms_per_query": round(ms_q, 2)}
    (RESULTS / f"vecs_{label}_{run_name}.json").write_text(json.dumps(out) + "\n")
    emit(run_name, "embedded", arm=label, ms_per_doc=out["ms_per_doc"])
    print(f"{label} done: dim={out['dim']} ms/doc={out['ms_per_doc']} "
          f"load={load_s:.1f}s", flush=True)


if __name__ == "__main__":
    sys.exit(main())

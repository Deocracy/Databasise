"""Arm E (control): untrained MiniCPM5-2B last-token marker state via HF (GPU).

Usage: embed_untrained.py <run_name>
Same inputs as arm A (20 docs, queries-v1 queries, gold queries), same output
schema as embed_a.py vecs (arm=E-minicpm2b). Text + literal MARKER, read the
final-position last hidden state, L2-normalise. bf16, one process, GPU lock.
This is spike 004's arm B re-measured on the queries-v1 sets through the HF
backend (also the adapter-off reference for arms B/C, which use this exact
code path plus LoRA).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import HERE, REPO, load_docs, load_gold, load_queries  # noqa: E402
from common_eval import RESULTS, emit  # noqa: E402

MARKER = "\u27e6EMB\u27e7"
MODEL_DIR = REPO / ".planning" / "spikes" / ".models" / "hf" / "openbmb__MiniCPM5-2B"


def main() -> None:
    run_name = sys.argv[1]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t0 = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR), torch_dtype=torch.bfloat16,
        trust_remote_code=True).cuda().eval()
    load_s = time.perf_counter() - t0
    peak = torch.cuda.max_memory_allocated() / 1e9
    emit(run_name, "model_loaded", model="MiniCPM5-2B-hf-bf16-untrained",
         load_s=round(load_s, 2), peak_vram_gb=round(peak, 2))

    docs, corpus_hash = load_docs()
    queries, _, q_hash = load_queries()
    assert corpus_hash == q_hash
    gold = load_gold()

    @torch.no_grad()
    def encode(texts):
        vecs, t0 = [], time.perf_counter()
        for t in texts:
            ids = tok(t + MARKER, return_tensors="pt",
                      truncation=True, max_length=512).to("cuda")
            h = model(**ids, output_hidden_states=True).hidden_states[-1]
            v = h[0, -1, :].float()
            vecs.append((v / v.norm()).tolist())
        return vecs, (time.perf_counter() - t0) / max(len(texts), 1) * 1000

    doc_vecs, ms_doc = encode([t for _, t in docs])
    q_vecs, ms_q = encode([q["q"] for q in queries])
    g_vecs, _ = encode([g["question"] for g in gold])
    out = {"arm": "E-minicpm2b", "model": "MiniCPM5-2B-hf-bf16-untrained",
           "pooling": "literal-marker/last", "prompt": "bare(none)",
           "corpus_hash": corpus_hash, "dim": len(doc_vecs[0]),
           "doc_ids": [d for d, _ in docs], "doc_vecs": doc_vecs,
           "query_ids": [q["id"] for q in queries], "query_vecs": q_vecs,
           "query_doc": [q["doc"] for q in queries],
           "query_split": [q["split"] for q in queries],
           "gold_ids": [g["id"] for g in gold], "gold_vecs": g_vecs,
           "gold_docs": [g["gold_document_ids"] for g in gold],
           "ms_per_doc": round(ms_doc, 2), "ms_per_query": round(ms_q, 2)}
    (RESULTS / f"vecs_E_{run_name}.json").write_text(json.dumps(out) + "\n")
    emit(run_name, "embedded", n_docs=len(docs), ms_per_doc=out["ms_per_doc"])
    print(f"E done: dim={out['dim']} ms/doc={out['ms_per_doc']} "
          f"load={load_s:.1f}s peak={peak:.1f}GB")


if __name__ == "__main__":
    sys.exit(main())

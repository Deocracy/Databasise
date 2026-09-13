"""Embed eval inputs through base + LoRA adapter (GPU, one process per arm).

Usage: embed_lora.py <run_name> <adapter_dir> <arm_label> [--proj]
With --proj: also load proj.pt (Linear 2048->1024) and emit projected
vectors (arm C). Same inputs/schema as embed_a.py vecs. GPU lock.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import HERE, REPO, load_docs, load_gold, load_queries  # noqa: E402
from common_eval import RESULTS, emit  # noqa: E402
from train_r import MARKER, MODEL_DIR  # noqa: E402 (011: R holds the recipe)


def main() -> None:
    run_name, adapter, label = sys.argv[1:4]
    use_proj = "--proj" in sys.argv
    import torch
    import torch.nn.functional as F
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    t0 = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
    base = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR), torch_dtype=torch.bfloat16,
        trust_remote_code=True).cuda().eval()
    model = PeftModel.from_pretrained(base, str(HERE / adapter)).cuda().eval()
    proj = None
    if use_proj:
        proj = torch.nn.Linear(2048, 1024, bias=True)
        proj.load_state_dict(torch.load(str(HERE / adapter / "proj.pt"),
                                        map_location="cpu"))
        proj.cuda().eval()
    load_s = time.perf_counter() - t0
    emit(run_name, "model_loaded", model=f"MiniCPM5-2B+{label}",
         load_s=round(load_s, 2), proj=use_proj)

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
            if proj is not None:
                v = proj(v)
            vecs.append((v / v.norm()).tolist())
        return vecs, (time.perf_counter() - t0) / max(len(texts), 1) * 1000

    doc_vecs, ms_doc = encode([t for _, t in docs])
    q_vecs, ms_q = encode([q["q"] for q in queries])
    g_vecs, _ = encode([g["question"] for g in gold])
    out = {"arm": label, "model": f"MiniCPM5-2B+{label}",
           "pooling": "literal-marker/last", "prompt": "bare(none)",
           "corpus_hash": corpus_hash,
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

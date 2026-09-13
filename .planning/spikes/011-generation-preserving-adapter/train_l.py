"""Arm L: low-capacity LoRA contrastive adapter (GPU, train venv).

Usage: train_l.py <run_name>
Same InfoNCE objective and data as arm R (train_b/train_r recipe), but:
  rank 4 (alpha 8 = 2r, same alpha/r ratio as R per the round-3 recipe),
  lr 2e-5, 2 epochs, attention projections only (q/k/v/o).
Measures how much retrieval survives when the update is small enough to
leave generation alone. Saves adapters/lora_lowcap_<run>/ + train log.
Never touches test documents.
"""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import HERE, REPO, load_docs, load_queries  # noqa: E402
from common_eval import emit  # noqa: E402
from train_r import MARKER, MODEL_DIR, sha_dir  # noqa: E402 (shared constants)


def main() -> None:
    run_name = sys.argv[1]
    epochs, tau, lr, batch, seed = 2, 0.03, 2e-5, 8, 1234

    import torch
    import torch.nn.functional as F
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model

    docs, corpus_hash = load_docs()
    queries, test_docs, _ = load_queries()
    test_set = set(test_docs)
    train_q = [q for q in queries if q["split"] == "train"]
    dmap = dict(docs)
    assert not any(q["doc"] in test_set for q in train_q), "train leaks test docs"
    train_docs = sorted({q["doc"] for q in train_q})
    assert len(train_q) == 86 and len(train_docs) == 15

    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
    t0 = time.perf_counter()
    base = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR), torch_dtype=torch.bfloat16,
        trust_remote_code=True)
    base.gradient_checkpointing_enable()
    cfg = LoraConfig(r=4, lora_alpha=8, lora_dropout=0.05,
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                     task_type="CAUSAL_LM")
    model = get_peft_model(base, cfg).cuda()
    model.train()
    load_s = time.perf_counter() - t0
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    emit(run_name, "model_loaded", model="MiniCPM5-2B+lora-r4-lowcap",
         load_s=round(load_s, 2), trainable_params=n_trainable,
         epochs=epochs, tau=tau, lr=lr, batch=batch, seed=seed)
    print(f"loaded {load_s:.1f}s trainable={n_trainable}", flush=True)

    def encode(texts, grad=True):
        ids = tok([t + MARKER for t in texts], return_tensors="pt",
                  padding=True, truncation=True,
                  max_length=512).to("cuda")
        ctx = torch.enable_grad() if grad else torch.no_grad()
        with ctx:
            h = model(input_ids=ids.input_ids,
                      attention_mask=ids.attention_mask,
                      output_hidden_states=True).hidden_states[-1]
        last = h[torch.arange(h.size(0), device="cuda"),
                 ids.attention_mask.sum(1) - 1, :].float()
        return F.normalize(last, dim=-1)

    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    p_texts = [dmap[d] for d in train_docs]
    outdir = HERE / "adapters" / f"lora_lowcap_{run_name}"
    step, t_train0 = 0, time.perf_counter()
    for ep in range(epochs):
        order = train_q[:]
        random.Random(seed + ep).shuffle(order)
        for i in range(0, len(order), batch):
            bq = order[i:i + batch]
            golds = sorted({q["doc"] for q in bq})
            g_texts = [dmap[d] for d in golds]
            qv = encode([q["q"] for q in bq], grad=True)
            gv = encode(g_texts, grad=True)
            neg_docs = [d for d in train_docs if d not in set(golds)]
            nv = encode([dmap[d] for d in neg_docs], grad=False)
            pv = torch.cat([gv, nv], dim=0)
            cand = golds + neg_docs
            sim = (qv @ pv.T) / tau
            tgt = torch.tensor([cand.index(q["doc"]) for q in bq],
                               device="cuda")
            loss = F.cross_entropy(sim, tgt)
            opt.zero_grad()
            loss.backward()
            opt.step()
            step += 1
            if step % 5 == 0 or step == 1:
                emit(run_name, "step", epoch=ep, step=step,
                     loss=round(loss.item(), 4),
                     elapsed_s=round(time.perf_counter() - t_train0, 1))
                print(f"ep={ep} step={step} loss={loss.item():.4f} "
                      f"t={time.perf_counter() - t_train0:.0f}s", flush=True)
        model.save_pretrained(str(outdir))
    train_s = time.perf_counter() - t_train0
    peak = torch.cuda.max_memory_allocated() / 1e9
    model.save_pretrained(str(outdir))
    tok.save_pretrained(str(outdir))
    emit(run_name, "train_done", steps=step, train_s=round(train_s, 1),
         peak_vram_gb=round(peak, 2), adapter=str(outdir),
         sha256=sha_dir(outdir))
    print(f"TRAIN DONE steps={step} train_s={train_s:.0f} peak={peak:.1f}GB "
          f"dir={outdir}", flush=True)


if __name__ == "__main__":
    sys.exit(main())

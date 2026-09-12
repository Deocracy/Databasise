"""Arm C: LoRA adapter distilled to arm A + InfoNCE (GPU, train venv).

Usage: train_c.py <run_name> [--epochs N] [--tau T] [--lr LR] [--batch B]
  [--lambda-nce L]
Loss per step over batch queries + their gold passages:
  mean(1 - cos(proj(h_txt), A_txt)) + LAMBDA * InfoNCE(proj states, tau)
where proj is a trainable Linear(2048 -> 1024), h the marker state, A the
frozen arm-A vector from results/teacher_A_train.json. Same data/epochs/
LoRA shape as arm B. Saves adapters/lora_distill_<run>/ (+ proj.pt inside).
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import HERE, REPO, load_docs, load_queries  # noqa: E402
from common_eval import RESULTS, emit  # noqa: E402
from train_b import MARKER, MODEL_DIR, sha_dir  # noqa: E402 (shared constants)


def main() -> None:
    run_name = sys.argv[1]
    epochs, tau, lr, batch, lam = 6, 0.03, 1e-4, 8, 1.0
    for a in sys.argv[2:]:
        if a.startswith("--epochs="):
            epochs = int(a.split("=", 1)[1])
        elif a.startswith("--tau="):
            tau = float(a.split("=", 1)[1])
        elif a.startswith("--lr="):
            lr = float(a.split("=", 1)[1])
        elif a.startswith("--batch="):
            batch = int(a.split("=", 1)[1])
        elif a.startswith("--lambda-nce="):
            lam = float(a.split("=", 1)[1])

    import torch
    import torch.nn.functional as F
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model

    docs, corpus_hash = load_docs()
    queries, test_docs, _ = load_queries()
    test_set = set(test_docs)
    train_q = [q for q in queries if q["split"] == "train"]
    dmap = dict(docs)
    assert not any(q["doc"] in test_set for q in train_q)
    teach = json.loads((RESULTS / "teacher_A_train.json").read_text())
    tq = dict(zip(teach["train_query_ids"],
                  [torch.tensor(v) for v in teach["train_query_vecs"]]))
    td = dict(zip(teach["train_doc_ids"],
                  [torch.tensor(v) for v in teach["train_doc_vecs"]]))
    assert set(tq) == {q["id"] for q in train_q}, "teacher/query drift"
    train_docs = sorted(td)

    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
    t0 = time.perf_counter()
    base = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR), torch_dtype=torch.bfloat16, trust_remote_code=True)
    base.gradient_checkpointing_enable()
    cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                     "gate_proj", "up_proj", "down_proj"],
                     task_type="CAUSAL_LM")
    model = get_peft_model(base, cfg).cuda()
    proj = torch.nn.Linear(2048, 1024, bias=True).cuda().to(torch.float32)
    model.train()
    proj.train()
    load_s = time.perf_counter() - t0
    n_tr = (sum(p.numel() for p in model.parameters() if p.requires_grad)
            + sum(p.numel() for p in proj.parameters()))
    emit(run_name, "model_loaded", model="MiniCPM5-2B+lora-r16-distill",
         load_s=round(load_s, 2), trainable_params=n_tr,
         epochs=epochs, tau=tau, lr=lr, batch=batch, lambda_nce=lam, seed=1234)
    print(f"loaded {load_s:.1f}s trainable={n_tr}", flush=True)

    def states(texts, grad=True):
        ids = tok([t + MARKER for t in texts], return_tensors="pt",
                  padding=True, truncation=True, max_length=512).to("cuda")
        ctx = torch.enable_grad() if grad else torch.no_grad()
        with ctx:
            h = model(input_ids=ids.input_ids,
                      attention_mask=ids.attention_mask,
                      output_hidden_states=True).hidden_states[-1]
        last = h[torch.arange(h.size(0), device="cuda"),
                 ids.attention_mask.sum(1) - 1, :]
        return proj(last.float())

    opt = torch.optim.AdamW(list(model.parameters()) + list(proj.parameters()),
                            lr=lr)
    outdir = HERE / "adapters" / f"lora_distill_{run_name}"
    step, t_train0 = 0, time.perf_counter()
    for ep in range(epochs):
        order = train_q[:]
        random.Random(1234 + ep).shuffle(order)
        for i in range(0, len(order), batch):
            bq = order[i:i + batch]
            golds = sorted({q["doc"] for q in bq})
            g_texts = [dmap[d] for d in golds]
            qh = states([q["q"] for q in bq], grad=True)
            gh = states(g_texts, grad=True)
            neg_docs = [d for d in train_docs if d not in set(golds)]
            nh = states([dmap[d] for d in neg_docs], grad=False)
            aq = torch.stack([tq[q["id"]] for q in bq]).cuda()
            ag = torch.stack([td[d] for d in golds]).cuda()
            l_dist = ((1 - F.cosine_similarity(qh, aq)).mean()
                      + (1 - F.cosine_similarity(gh, ag)).mean()) / 2
            pv = torch.cat([gh, nh], dim=0)
            cand = golds + neg_docs
            sim = (F.normalize(qh, dim=-1) @ F.normalize(pv, dim=-1).T) / tau
            tgt = torch.tensor([cand.index(q["doc"]) for q in bq],
                               device="cuda")
            l_nce = F.cross_entropy(sim, tgt)
            loss = l_dist + lam * l_nce
            opt.zero_grad()
            loss.backward()
            opt.step()
            step += 1
            if step % 5 == 0 or step == 1:
                emit(run_name, "step", epoch=ep, step=step,
                     loss=round(loss.item(), 4),
                     dist=round(l_dist.item(), 4), nce=round(l_nce.item(), 4),
                     elapsed_s=round(time.perf_counter() - t_train0, 1))
                print(f"ep={ep} step={step} loss={loss.item():.4f} "
                      f"(d={l_dist.item():.4f} n={l_nce.item():.4f}) "
                      f"t={time.perf_counter() - t_train0:.0f}s", flush=True)
        model.save_pretrained(str(outdir))  # per-epoch ckpt (overwritten)
        torch.save(proj.state_dict(), outdir / "proj.pt")
    train_s = time.perf_counter() - t_train0
    peak = torch.cuda.max_memory_allocated() / 1e9
    model.save_pretrained(str(outdir))
    torch.save(proj.state_dict(), outdir / "proj.pt")
    tok.save_pretrained(str(outdir))
    emit(run_name, "train_done", steps=step, train_s=round(train_s, 1),
         peak_vram_gb=round(peak, 2), adapter=str(outdir),
         sha256=sha_dir(outdir))
    print(f"TRAIN DONE steps={step} train_s={train_s:.0f} peak={peak:.1f}GB",
          flush=True)


if __name__ == "__main__":
    sys.exit(main())

"""Arm B: LoRA contrastive adapter on MiniCPM5-2B [EMB] state (GPU, train venv).

Usage: train_b.py <run_name> [--epochs N] [--tau T] [--lr LR] [--batch B]
InfoNCE query -> passage over the 86 train queries; negatives are in-batch
plus all other train-doc passages (15 train docs total). Pooling: last-token
state at the literal MARKER, causal attention kept (one-pass design needs
it). LoRA r16 on attention+MLP projections, bf16, grad checkpointing,
seq <= 512. Saves adapters/lora_contrastive_<run>/ + train log JSONL.
Never touches test documents.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import HERE, REPO, load_docs, load_queries  # noqa: E402
from common_eval import LOGS, emit  # noqa: E402

MARKER = "\u27e6EMB\u27e7"
MODEL_DIR = REPO / ".planning" / "spikes" / ".models" / "hf" / "openbmb__MiniCPM5-2B"


def sha_dir(d: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(d.rglob("*")):
        if p.is_file():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def main() -> None:
    run_name = sys.argv[1]
    epochs, tau, lr, batch, seed = 6, 0.03, 1e-4, 8, 1234
    for a in sys.argv[2:]:
        if a.startswith("--epochs="):
            epochs = int(a.split("=", 1)[1])
        elif a.startswith("--tau="):
            tau = float(a.split("=", 1)[1])
        elif a.startswith("--lr="):
            lr = float(a.split("=", 1)[1])
        elif a.startswith("--batch="):
            batch = int(a.split("=", 1)[1])
        elif a.startswith("--seed="):
            seed = int(a.split("=", 1)[1])

    import torch
    import torch.nn.functional as F
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training  # noqa

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
    cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                     "gate_proj", "up_proj", "down_proj"],
                     task_type="CAUSAL_LM")
    model = get_peft_model(base, cfg).cuda()
    model.train()
    load_s = time.perf_counter() - t0
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    emit(run_name, "model_loaded", model="MiniCPM5-2B+lora-r16-contrastive",
         load_s=round(load_s, 2), trainable_params=n_trainable,
         epochs=epochs, tau=tau, lr=lr, batch=batch, seed=seed)
    print(f"loaded {load_s:.1f}s trainable={n_trainable}", flush=True)

    random.seed(seed)

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
    outdir = HERE / "adapters" / f"lora_contrastive_{run_name}"
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
            # hard negatives: other train passages, fresh states, no backward
            # (keeps step cost down; query+gold towers carry the gradient).
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
        model.save_pretrained(str(outdir))  # per-epoch ckpt (overwritten)
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

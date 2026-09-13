"""Arm J: joint contrastive + op-emission LM loss (GPU, train venv).

Usage: train_j.py <run_name> [--lam-lm=L]
The MelodyScribe-2B-v0.1 candidate. Per step:

  loss = InfoNCE(marker state, same data/shape as arm R)
       + lam * causal-LM loss on the one-shot op-emission prompt
         (spike 008 D1 format with the train-doc example from opdata.py)
         with the teacher ops JSON as the target (train docs only)

LM labels: -100 over the prompt, target ids over the teacher JSON, so only
the op tokens supervise. Capacity identical to R (r16, alpha 32, all seven
modules, lr 1e-4, 6 epochs) so R-vs-J isolates the objective. lam=0.5
pre-registered (keeps both terms O(1) after warmup).

DEVIATION (recorded): the LM forward is capped at 2048 tokens, not 768.
The 768 cap cannot hold even the target JSON alone for 5/15 train docs
(charles_craft target = 858 tokens; doctor_strange 897), and truncating
targets would train on invalid JSON. With 2048 only one train doc
(charles_craft, 2070 total) loses 22 prompt-head tokens to left
truncation; the target is always intact. Contrastive side stays at 512.
Saves adapters/lora_joint_<run>/ + train log. Never touches test docs.
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
from opdata import (load_teacher, oneshot_prompt, pick_example_doc,  # noqa: E402
                    target_json, train_doc_ids)

LM_CAP = 2048


def main() -> None:
    run_name = sys.argv[1]
    lam_lm = 0.5
    for a in sys.argv[2:]:
        if a.startswith("--lam-lm="):
            lam_lm = float(a.split("=", 1)[1])
    epochs, tau, lr, batch, seed = 6, 0.03, 1e-4, 8, 1234

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

    teacher, contents, _ = load_teacher()
    example_doc = pick_example_doc(teacher)
    assert example_doc not in test_set, "example doc must be a train doc"
    lm_pool = [d for d in train_docs if d != example_doc]
    print(f"example_doc={example_doc} lm_pool={len(lm_pool)}", flush=True)

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
    emit(run_name, "model_loaded", model="MiniCPM5-2B+lora-r16-joint",
         load_s=round(load_s, 2), trainable_params=n_trainable,
         epochs=epochs, tau=tau, lr=lr, batch=batch, seed=seed,
         lam_lm=lam_lm, example_doc=example_doc, lm_cap=LM_CAP)
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
    outdir = HERE / "adapters" / f"lora_joint_{run_name}"
    rng = random.Random(seed)
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
            l_nce = F.cross_entropy(sim, tgt)

            # Op-emission LM loss on one sampled train doc.
            lm_doc = rng.choice(lm_pool)
            prompt = oneshot_prompt(contents[lm_doc], contents, example_doc)
            target = target_json(lm_doc)
            p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
            t_ids = tok(target, add_special_tokens=False)["input_ids"]
            keep_p = LM_CAP - len(t_ids)
            assert keep_p > 0, f"target alone exceeds cap: {lm_doc}"
            p_ids = p_ids[-keep_p:]  # left-truncate prompt only
            in_ids = torch.tensor([p_ids + t_ids], device="cuda")
            labels = torch.tensor([[-100] * len(p_ids) + t_ids], device="cuda")
            lm_out = model(input_ids=in_ids, attention_mask=torch.ones_like(in_ids))
            l_lm = F.cross_entropy(
                lm_out.logits.float().view(-1, lm_out.logits.size(-1)),
                labels.view(-1), ignore_index=-100)

            loss = l_nce + lam_lm * l_lm
            opt.zero_grad()
            loss.backward()
            opt.step()
            step += 1
            if step % 5 == 0 or step == 1:
                emit(run_name, "step", epoch=ep, step=step,
                     loss=round(loss.item(), 4),
                     nce=round(l_nce.item(), 4), lm=round(l_lm.item(), 4),
                     lm_doc=lm_doc,
                     elapsed_s=round(time.perf_counter() - t_train0, 1))
                print(f"ep={ep} step={step} loss={loss.item():.4f} "
                      f"(n={l_nce.item():.4f} lm={l_lm.item():.4f} {lm_doc}) "
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

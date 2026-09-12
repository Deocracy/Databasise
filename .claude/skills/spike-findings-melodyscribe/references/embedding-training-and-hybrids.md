# Embedding Training and Hybrids

## Requirements

From the `melodyscribe` idea in `.planning/spikes/MANIFEST.md`, the six that this area owns:

- Model size is a rig variable; report the size-versus-accuracy curve before choosing (D-MS-05)
- No vendor benchmark settles anything; every verdict comes from a local measurement on the 20-document parity corpus
- Every measurement run holds the GPU lock so numbers are never taken under contention
- Labelled data is teacher-generated with provenance and a fixed train/test split by document (`.planning/spikes/shared/`); nothing is hand-labelled and no spike trains on test documents
- Any adapter or merge reports generation retained: op emission Proof-pass rate and routing with the change on versus off
- Training and merging run in `.planning/spikes/.venv-train` on safetensors under `.models/hf/`; GGUF stays inference-only

## How to Build It

Round 1 (spikes 003 and 004) is recorded in `.claude/skills/spike-findings-melodyscribe/references/model-size-and-training.md`: untrained 2B last-token states are anisotropic (pairwise cosine 0.91), a ridge head lowers recall, and Qwen3-Embedding-0.6B is the baseline. This file starts where that one ends: the trained arms of spike 006 and the prompt designs of spike 007. Steps follow the order each spike's `run.sh` executes.

### Step 1. The shared query set and its split (both spikes)

`.planning/spikes/shared/queries-v1.json` (`version` `queries-v1`, created 2026-09-12): 116 teacher-generated queries over the 20 corpus documents, 4 dropped, `teacher` recorded as "v1/.env.parity LLM_MODEL (id not recorded), temperature 0, reasoning disabled". `split_rule`: "documents sorted by id; every fourth starting at index 3 is test". `test_document_ids`: `conrad_brooks`, `ed_wood_film`, `meet_corliss_archer`, `shirley_temple`, `woodson_arkansas`. `counts`: 86 train, 30 test. The file carries `corpus_hash` `ac55d19e...` and `queries_hash` `ddfb9401...`; every loader asserts both (`006/data.py`, `007/build_inputs.py`). The 2 HotpotQA gold queries come from the corpus `MANIFEST.json` and are never training inputs. Query ids ending in `#5` are the 20 keyword-style queries; the other 96 are natural language.

Passages are whole documents (title plus one paragraph), one unit per document as in spike 003. Both trainers assert `not any(q["doc"] in test_set for q in train_q)` and `len(train_q) == 86 and len(train_docs) == 15`.

### Step 2. Training environment

`.planning/spikes/setup-train-env.sh` builds `.planning/spikes/.venv-train` with `uv pip install torch transformers peft accelerate safetensors huggingface_hub sentence-transformers numpy faiss-cpu httpx jsonschema datasets`, then `mergekit` as an optional second install. Safetensors weights live under `.planning/spikes/.models/hf/` (`openbmb__MiniCPM5-2B`, `Qwen__Qwen3-Embedding-0.6B`, `Qwen__Qwen3-0.6B`), fetched by `fetch-hf-weights.py`. GGUF under `.models/` stays inference-only through `.venv` and llama-cpp. From `006/run.sh`:

```bash
source "$ROOT/.planning/spikes/env.sh"
# triton hardcodes /sbin/ldconfig (absent on NixOS); the knob bypasses it.
export TRITON_LIBCUDA_PATH=/run/opengl-driver/lib
export HF_HUB_OFFLINE=1
TPY="$ROOT/.planning/spikes/.venv-train/bin/python"
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/train_b.py" "$RUN" || exit 1
```

Without `TRITON_LIBCUDA_PATH` the first CUDA encode through sentence-transformers dies in `triton/backends/nvidia/driver.py:libcuda_dirs` (006 trail item 2). Every GPU step is a foreground `flock` process, one model per process; merges and scoring run on CPU without the lock. Detached `setsid` GPU jobs died with their tool calls; per-epoch adapter checkpoints and a resume-aware scorer turned two machine reboots into zero lost training (006 trail items 3, 12, 14).

Baselines measured before training, same inputs: arm A (`embed_a.py`, sentence-transformers, bare text, native last-token pooling) test MRR 0.801, gold 1.00, anisotropy 0.279, 99.6 ms per document, 2.45 ms per query; arm E (`embed_untrained.py`, HF backend, untrained MiniCPM5-2B marker state) test MRR 0.316, gold 0.125, anisotropy 0.903, reproducing spike 004's arm B (0.31 / 0.914) through a different backend. The gap to close is 0.316 to 0.801.

### Step 3. Arm B: contrastive LoRA on MiniCPM5-2B (`006/train_b.py`)

Objective: InfoNCE query to passage, temperature 0.03, negatives are the in-batch gold passages plus every other train-document passage (15 train docs minus the batch's golds) as hard negatives, pooled at the literal `⟦EMB⟧` marker (6 MiniCPM tokens) as the last-token state, causal attention kept because the one-pass design needs it. LoRA rank 16, alpha 32, dropout 0.05 on `q_proj k_proj v_proj o_proj gate_proj up_proj down_proj`; bf16, gradient checkpointing, sequence length at most 512, AdamW lr 1e-4, batch 8, 6 epochs of 11 steps (66 steps), seed 1234. Measured: 147 s wall, peak VRAM 7.1 GB, loss 0.9 to 0.02 (`logs/run1.jsonl`).

```python
cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                 target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                 "gate_proj", "up_proj", "down_proj"],
                 task_type="CAUSAL_LM")
model = get_peft_model(base, cfg).cuda()

def encode(texts, grad=True):
    ids = tok([t + MARKER for t in texts], return_tensors="pt",
              padding=True, truncation=True, max_length=512).to("cuda")
    ctx = torch.enable_grad() if grad else torch.no_grad()
    with ctx:
        h = model(input_ids=ids.input_ids, attention_mask=ids.attention_mask,
                  output_hidden_states=True).hidden_states[-1]
    last = h[torch.arange(h.size(0), device="cuda"),
             ids.attention_mask.sum(1) - 1, :].float()
    return F.normalize(last, dim=-1)
...
qv = encode([q["q"] for q in bq], grad=True)
gv = encode(g_texts, grad=True)
neg_docs = [d for d in train_docs if d not in set(golds)]
nv = encode([dmap[d] for d in neg_docs], grad=False)   # hard negatives, no backward
pv = torch.cat([gv, nv], dim=0)
sim = (qv @ pv.T) / tau
tgt = torch.tensor([cand.index(q["doc"]) for q in bq], device="cuda")
loss = F.cross_entropy(sim, tgt)
```

Hard negatives are encoded without gradient so only the query and gold towers pay for backward. The adapter is saved after every epoch (overwritten) and the directory SHA-256 is logged at `train_done`. `--seed=999` reruns the recipe for the robustness check. Eval vectors come from `embed_lora.py`: base plus `PeftModel.from_pretrained`, bare text plus marker, `hidden_states[-1][0, -1, :]`, L2 normalised, one process per arm under the lock.

Result: test MRR 0.748 (seed 1234) and 0.740 (seed 999) against A 0.801; the 0.05 parity bar is missed by 0.053 and 0.061 on both seeds, so the miss is stable rather than seed noise. Train MRR 0.956 / 0.949 is a memorisation gap on 15 documents. Anisotropy drops from 0.903 (untrained) to 0.679 / 0.581.

### Step 4. Arm C: distillation to the embedder, and why it lost (`006/train_c.py`)

Same data, LoRA shape, epochs, lr and tau as B, plus a trainable `Linear(2048, 1024)` projection from the marker state into arm A's space and a distillation term against frozen A vectors for the same texts (`results/teacher_A_train.json`, train queries and train passages only):

```python
proj = torch.nn.Linear(2048, 1024, bias=True).cuda().to(torch.float32)
...
l_dist = ((1 - F.cosine_similarity(qh, aq)).mean()
          + (1 - F.cosine_similarity(gh, ag)).mean()) / 2
sim = (F.normalize(qh, dim=-1) @ F.normalize(pv, dim=-1).T) / tau
l_nce = F.cross_entropy(sim, tgt)
loss = l_dist + lam * l_nce        # lam = 1.0
```

Measured: 66 steps, 145 s, peak 7.1 GB. The distillation term stalled near 0.55 while the InfoNCE term fell. Test MRR 0.638 against B's 0.748 with train MRR 0.966: the projection bottleneck plus the dual objective fits A's vectors on train texts and ranks worse on held-out ones. Recorded as INVALIDATED and against interest; the "embedding model mixed into the small model" direction fails at this scale. Eval with `embed_lora.py ... --proj` loads `proj.pt` and emits the projected 1024-dim vectors.

### Step 5. Arm D: linear merge of Qwen3-Embedding-0.6B into Qwen3-0.6B (`006/merge_d.py`, CPU)

Both are `Qwen3Config` hidden 1024, 28 layers, but the embedder keys are bare `layers.*` with no `lm_head` and the generative base keys are `model.*` plus `lm_head`; vocab rows differ, 151669 (embedder) versus 151936 (generative), and the added tokens are byte-identical at ids 151643 to 151668 with the generative tail from 151669 reserved. Merge rule: strip `model.` from generative keys, interpolate the 309 shared tensors at embed fraction w in {0.25, 0.5, 0.75}, interpolate the shared embed rows, keep the generative base's 267 extra rows and its `lm_head` verbatim.

```python
gen_aligned = {k[len("model."):] if k.startswith("model.") else k: v
               for k, v in gen.items()}
shared = [k for k in emb if k in gen_aligned
          and emb[k].shape == gen_aligned[k].shape]
assert not only_emb, f"unmapped embedder tensors: {only_emb}"
n_emb_rows = emb["embed_tokens.weight"].shape[0]
for w in RATIOS:                                  # (0.25, 0.5, 0.75)
    out = {}
    for k in shared:
        if k == "embed_tokens.weight":
            m = w * emb[k] + (1 - w) * gen_aligned[k][:n_emb_rows]
            out["model." + k] = torch.cat([m, gen_aligned[k][n_emb_rows:]], dim=0)
        else:
            out["model." + k] = w * emb[k] + (1 - w) * gen_aligned[k]
    out["lm_head.weight"] = gen["lm_head.weight"]
    save_file(out, str(d / "model.safetensors"))
```

Output directories are generative-shaped (config, tokenizer, generation_config copied from the base), so `embed_qwen.py` and `gen_eval.py` load them exactly like the base. Two merge runs (m1, m2) produced byte-identical SHAs. Embedding uses bare text and manual last-token pooling of `hidden_states[-1]`, L2 normalised, max length 512.

Result: test MRR climbs monotonically with embed weight, 0.384 (base) to 0.538 to 0.617 to 0.660; w0.75 is 0.82 times A and passes the 0.8 merge bar with gold MRR 1.00. Anisotropy falls 0.846 to 0.479 along the same axis.

### Step 6. Recall evaluation (`006/eval_recall.py`, CPU)

All arms share one document order (asserted). Per arm: test split (30 queries over 5 held-out documents, ranked against all 20), train split diagnostic (86), gold (2), recall@1/3/10 and MRR by cosine, anisotropy as mean pairwise document cosine, ms per document and per query carried from the embed run. Output `results/recall_<run>.json` plus one `arm_scored` log line per arm.

### Step 7. Generation-retained evaluation (`006/gen_eval.py`) and its deviation

The adapters and merged weights are HF-native with no GGUF path, so the v0.2 GBNF grammar from spike 003 cannot be applied. Both sides of every comparison (change on versus change off) therefore run the same unconstrained greedy HF decoder over spike 003's exact student prompt bytes, and Proof scores the difference:

```python
prompt = student_prompt(content)                      # 003 INSTRUCTION bytes
ids = tok(prompt, return_tensors="pt", truncation=True, max_length=3072).to("cuda")
gen = model.generate(**ids, do_sample=False, max_new_tokens=1024,
                     pad_token_id=tok.eos_token_id)
...
res = v02.validate_v02(obj, FILE_SET, content, ops_validate)   # spike 001 Proof
if {x.get("target") for x in s} == {x.get("target") for x in t_pass[doc_id]}:
    route_hit += 1
```

Metrics are 003's: `routing_exact`, `parse_rate`, `proof_pass_rate` (passing over emitted, 1.0 when nothing is emitted), tokens and seconds per paragraph, against 003's `teacher.json` (schema `ops.v0.2`, corpus hash asserted). The scorer writes partial results after every decode and resumes from them; greedy decoding is deterministic, so a reboot at 7/20 completed exactly. Absolute routing is far below 003's grammar-constrained numbers; the on-versus-off deltas are the evidence, not the levels.

### Step 8. Head-to-head tables (spike 006)

Retrieval, identical inputs, 30 test queries over 5 held-out docs ranked against all 20 (`006/results/recall_final.json`):

| arm | test r@1 / r@3 / r@10 / MRR | train MRR | gold MRR | aniso |
|---|---|---|---|---|
| A dedicated 0.6B | 0.700 / 0.867 / 1.000 / 0.801 | 0.788 | 1.000 | 0.279 |
| E 2B untrained | 0.233 / 0.267 / 0.633 / 0.316 | 0.315 | 0.125 | 0.903 |
| B 2B + LoRA contrastive | 0.567 / 0.933 / 1.000 / 0.748 | 0.956 | 0.750 | 0.679 |
| B seed 999 | 0.633 / 0.800 / 1.000 / 0.740 | 0.949 | 0.500 | 0.581 |
| C 2B + LoRA distill | 0.433 / 0.767 / 1.000 / 0.638 | 0.966 | 0.750 | 0.680 |
| D0 Qwen3-0.6B base | 0.233 / 0.433 / 0.667 / 0.384 | 0.480 | 0.600 | 0.846 |
| D w0.25 | 0.367 / 0.633 / 0.967 / 0.538 | 0.584 | 0.750 | 0.762 |
| D w0.5 | 0.433 / 0.700 / 1.000 / 0.617 | 0.644 | 1.000 | 0.625 |
| D w0.75 | 0.467 / 0.800 / 1.000 / 0.660 | 0.664 | 1.000 | 0.479 |

Generation retained, grammar-free greedy decode (`006/results/gen_*.json`):

| arm | routing_exact | parse_rate | Proof-pass | tok/para | s/para |
|---|---|---|---|---|---|
| minicpm base | 0.100 | 0.150 | 1.000 (9/9) | 856.6 | 17.57 |
| minicpm +B | 0.000 | 0.000 | 1.000 (0/0) | 1020.5 | 49.37 |
| minicpm +C | 0.000 | 0.000 | 1.000 (0/0) | 989.3 | 49.54 |
| qwen06 base | 0.000 | 0.000 | 1.000 (0/0) | 1023.0 | 19.40 |
| qwen06 +w0.25/0.5/0.75 | 0.000 | 0.000 | 1.000 (0/0) | about 1024 | about 18 |

The +B/+C seconds include GPU contention from an unlocked orphan run; the comparison, not the absolute timing, is the evidence. Verdict PARTIAL: B is a stable near-miss on retrieval and a collapse on generation (20/20 cap-looping repetition); C is INVALIDATED; D passes its retrieval bar with a vacuous generation hold (the raw 0.6B base parses 0/20 unconstrained, so there is nothing to retain); TIES/DARE is INVALIDATED on tooling only.

### Step 9. Prompt designs (spike 007, VALIDATED)

Question: does the prompt around a text change its embedding enough to matter, and what should the Score's `doc_prefix` and query prefix be. Pre-registered bar, written in the README before any run: a full-set MRR move of at least 0.05 is material; anything under it is reported as not material, never as a small win. Inputs: 532 embedder texts and 238 generative texts rendered by `build_inputs.py` (empty renders refused, longest render 1321 chars against `n_ctx` 4096, zero `⟦EMB⟧` collisions in the corpus), embedded 3 times each on GGUF through `.venv` (Q8 embedder with native pooling, Q8 MiniCPM5-2B with LAST pooling), one model per process under the lock. Evaluation on rep1 with a rep1-versus-rep2 determinism check: max abs diff 0.0 on both models.

Designs, from `007/designs.py`. Instructions go on the query side only for the embedder, in the Qwen3-Embedding documented format; documents stay bare except in the two document-side arms (E05, E06):

```python
def instruct_query(instr: str, q: str) -> str:
    return f"Instruct: {instr}\nQuery: {q}"
VENDOR_INSTR = "Given a web search query, retrieve relevant passages that answer the query"
TASK_INSTR = ("Given a question about films and the people who made them, "
              "retrieve the passage that answers the question")
WRONG_INSTR = ("Given a code search query, retrieve relevant code snippets "
               "that implement the required functionality")
def instr_doc(text): return f"Instruct: {TASK_INSTR}\nDocument: {text}"   # E05
def titled_doc(title, text): return f"Title: {title}\n{text}"             # E06
SYSTEM_INSTR = "Represent the passage that follows for retrieval."
SYS_PREFIX = "<s><|im_start|>system\n" + SYSTEM_INSTR + "<|im_end|>\n"    # G07, v0.1 doc_prefix default
def gen_bare(text): return text + MARKER
def gen_eol(text): return f'This sentence: "{text}" means in one word:'  # G08, no marker
def gen_about(text): return text + " The passage is about"               # G08
```

Full 116-query set, rep1 (`007/results/head2head_report.json`):

| design | r@1 | r@3 | r@10 | MRR | aniso | gap | ms/text |
|---|---|---|---|---|---|---|---|
| E01 none (baseline) | 0.681 | 0.879 | 0.991 | 0.792 | 0.2775 | 0.2130 | 5.3 to 8.0 |
| E02 vendor-q | 0.716 | 0.888 | 1.000 | 0.814 (+0.022) | 0.2775 | 0.2607 | same |
| E03 task-q | 0.733 | 0.879 | 0.991 | 0.813 (+0.021) | 0.2775 | 0.2586 | same |
| E04 wrong-domain-q | 0.664 | 0.853 | 0.991 | 0.774 (-0.018) | 0.2775 | 0.2139 | same |
| E05 instruction both sides | 0.672 | 0.905 | 0.991 | 0.789 (-0.003) | 0.2584 | 0.2569 | same |
| E06 title prefix | 0.724 | 0.897 | 0.991 | 0.820 (+0.028) | 0.2800 | 0.2143 | same |
| G01 none (baseline) | 0.181 | 0.362 | 0.664 | 0.322 | 0.9134 | 0.0145 | 16 to 21 |
| G07 system-turn prefix (v0.1 default) | 0.198 | 0.440 | 0.690 | 0.367 (+0.045) | 0.9273 | 0.0137 | same |
| G07 plain task prefix | 0.155 | 0.362 | 0.767 | 0.327 (+0.005) | 0.9275 | 0.0141 | same |
| G08 PromptEOL suffix | 0.095 | 0.293 | 0.681 | 0.274 (-0.048) | 0.7749 | 0.0207 | same |
| G08 "about" suffix | 0.138 | 0.241 | 0.716 | 0.271 (-0.051) | 0.7600 | 0.0218 | same |
| G06 title prefix | 0.181 | 0.310 | 0.655 | 0.314 (-0.008) | 0.9142 | 0.0146 | same |

`gap` is mean gold cosine minus mean non-gold cosine per query. ms/text is per model, not per design (one process embeds every design of that model): embedder reps 5.43 / 5.27 / 8.04, generative reps 20.63 / 18.87 / 16.47.

What this settles:

- No design is material on either model. The largest embedder move is E06 +0.028; the largest generative move is G07 system turn +0.045 with noisy flips (32 queries up by 5 or more ranks, 20 down). Documents stay bare; a `Title:` prefix is optional; the v0.1 `doc_prefix` system-turn default holds by default, not by proof.
- The wrong-domain instruction does not hurt (-0.018, gap unchanged 0.2139 versus 0.2130): the embedder ignores the instruction for ranking on this corpus. Matching-domain instructions widen the query-document gap by about 0.05 without reordering documents.
- No generative prompt closes the deficit: best G07sys 0.367 against embedder baseline 0.792; anisotropy stays 0.76 to 0.93 against 0.28. PromptEOL and "about" suffixes lower anisotropy to about 0.77 and lower MRR at the same time, so anisotropy alone does not predict recall.
- Exploratory only: E02 vendor instruction lifts keyword-query MRR 0.729 to 0.870 (r@1 0.55 to 0.80, n=20, 6 queries improve, 2 worsen). Re-test on a keyword-heavy stream before adopting.
- Owner re-run 2026-09-12: all 122 ranking, anisotropy and gap numbers equal; only per-text timings differ. NL split (n=96) mirrors full-set ordering on both models; gold-2 RR is 1.00 on every embedder design.

### Step 10. Next steps from the research recipe, not yet run

`reference/micro-harnesses/deep-research-2/REPORT.md` section 5A is the sourced order of work; the spikes ran parts of its steps 3, 5 and 6 only. Remaining, in recipe order:

1. Unsupervised linear controls before any more training: whiten the MiniCPM5 last-token states on a large unlabelled sample (2103.15316), all-but-the-top and mean centering (1702.01417), subtract the marker-only template bias (PromptBERT 2201.04337). Spike 004's ridge result does not contradict these controls. Track alignment/uniformity (2005.10242) and IsoScore (2108.07344) next to MRR so n=30 MRR cannot mislead.
2. Unsupervised special-token compression as the no-pairs arm (LLM2Vec-Gen 2603.10913), the direct answer to the missing-pairs blocker from spike 004.
3. A generation-preserving adapter recipe, the open item from 006's INVALIDATED sub-claim: lower rank and learning rate, a KL anchor to the frozen base, or a joint LM loss. GritLM (2402.09906) is the existence proof at 7B with full joint training; Hydra (2603.28554) toggles a retrieval LoRA at inference and reports base tensors byte-identical with it off, so diff tensors to verify recovery. Report routing and Proof-pass on versus off at every setting (Embedder's Dilemma protocol 2608.12875).
4. Synthetic data engine: exemplar-seeded query generation (Promptagator 2209.11755), consistency filtering (InPars 2202.05144), LLM relabelling of positives and hard negatives (Gecko 2403.20327), instruction negatives that share the query but violate the instruction (Promptriever 2409.11136), n-gram decontamination of every eval split. The dominant budget is generation plus relabelling, not GPU hours.
5. Two-stage training: weak or synthetic contrastive pretraining, then supervised fine-tuning on high-quality triplets (E5 2212.03533; Qwen3-Embedding 2506.05176), with in-batch plus mined hard negatives, false-negative masking, ANN-refreshed negatives (ANCE 2007.00808), cross-batch negatives for the 16 GB batch ceiling (RocketQA 2010.08191), and a merge-home step. E5-Mistral-class runs finish the contrastive phase under 1k steps (vendor-reported).
6. Latent-attention pooling instead of last-token readout (NV-Embed 2405.17428), with instruction tokens masked out of the pooled output while still shaping states through attention: the rule to copy for the `[EMB]` marker. Pin and version the instruction strings (2605.22544) and keep the no-instruction control (Promptriever, FollowIR 2403.15246).
7. Matryoshka nested dims from the start (2205.13147) for query-time truncation.
8. A TIES/DARE merge sweep with a Model Soups floor and LM-Cocktail rebalancing, generation benchmarks at every coefficient (2306.01708; 2311.03099; 2203.05482; 2311.13534), once a mergekit that validates under pydantic v2 is installed.

## What to Avoid

- **Distillation to the embedder's vectors through a projection.** Arm C (`Linear(2048, 1024)`, one minus cosine to A plus InfoNCE at lambda 1) scored test MRR 0.638 against plain contrastive 0.748, with the distillation term stalled near 0.55. Worse than the objective it was meant to improve.
- **A retrieval LoRA at rank 16, lr 1e-4, 6 epochs on the generative model.** Both adapters collapsed unconstrained op emission to 0/20 parses (cap-looping repetition, 1020.5 and 989.3 tokens per paragraph) against a base at parse rate 0.15 and route 0.10. The adapter and the generative pass do not coexist at this setting; a generation-preserving recipe is untested.
- **mergekit under pydantic v2.** Both the `run_merge` API (`MergeRunner` absent in the installed version) and the CLI fail at config validation with `ConfiguredModuleArchitecture is not fully defined` before any tensor is touched. Plain safetensors arithmetic (`merge_d.py`) works; the padded aligned copy left in `merged/` is ready for a fixed mergekit.
- **Claiming the chat-template `doc_prefix` helps.** G07 system turn is +0.045 MRR, under the 0.05 bar, with 32 up and 20 down flips of 5 or more ranks. Keep it because it costs nothing, not because it is proven.
- **Adopting instruction designs from n=20 keyword queries.** E02's keyword lift (+0.141) is exploratory and was not pre-registered; rank>3-to-<=3 flips are 2 versus 2.
- **Reading train MRR 0.95 as success.** Arm B trains to 0.956 and tests at 0.748 on 5 held-out documents; the 15-document train set memorises. Only the test split and the gold queries count.
- **PromptEOL and "about" suffixes on the generative path.** Anisotropy drops from 0.913 to 0.775 / 0.760 while MRR drops from 0.322 to 0.274 / 0.271. Lower anisotropy is not higher recall.
- **Detached GPU jobs and unlocked orphans.** `setsid` launches died with their tool calls, and an unlocked orphan inflated +B/+C seconds per paragraph to about 49 against 17.57 lock-held. Foreground `flock`, one model per process, resume-aware scorers.
- **Using `$MELODYSCRIBE_PY` for training scripts.** It is `.venv` (no sentence-transformers, no torch); training and merging use `.venv-train/bin/python` (`$TPY` in `run.sh`).

## Constraints

- **Pass bars, pre-registered in the 006 README:** B or C reaches test MRR within 0.05 of A with routing_exact and Proof-pass within 0.05 of the untouched 2B; D keeps at least 90 percent of the base's Proof-pass rate while reaching at least 0.8 of A's MRR. 007 bar: full-set MRR move of at least 0.05.
- **Data:** 116 queries, 86 train / 30 test, 4 dropped; 15 train documents, 5 test documents; test set n=30 over 5 documents; 2 HotpotQA gold queries (2 gold documents each); 20 keyword (`#5`) and 96 NL queries; documents are short paragraphs (title plus one paragraph, longest render 1321 chars). `corpus_hash` `ac55d19ec162cc9abf51ddf8502436109b1439c5cbaea4cf41c448c11575d5bd`, `queries_hash` `ddfb9401a7498894bb60cddc2a98ad46930311438b9055129e42d4c2ba73e548`.
- **Arm A backend in 006:** sentence-transformers over safetensors, bare text, native last-token pooling, dim 1024, 99.6 ms per document, 2.45 ms per query; test MRR 0.801, gold 1.00, anisotropy 0.279, matching spike 004's GGUF profile. In 007 the embedder is the Q8 GGUF through llama-cpp at 5.43 ms per text.
- **Arm B/C training:** MiniCPM5-2B bf16 5.0 GB, hidden 2048, 42 layers; marker `⟦EMB⟧` is 6 tokens; 66 steps; 147 s (B), 145 s (C); peak VRAM 7.1 GB of 16 GB; the 30-minute budget has 10 times headroom. Adapters under `006/adapters/` (git-ignored).
- **Arm D merge:** 309 shared tensors; vocab 151669 versus 151936; 267 extra generative rows; two merge runs byte-identical; merged weights under `006/merged/` (git-ignored).
- **SHA-256 prefixes** (`logs/run1.jsonl`, `logs/run1seed999.jsonl`, `merged/manifest_run1.json`): adapter B `aa761ddc`, B seed 999 `72d4140c`, C `4d93a229`; merged w0.25 `4a8ce74b`, w0.5 `b556e72f`, w0.75 `71fae1a3`.
- **Generation-retained decode:** greedy HF, `max_new_tokens` 1024, prompt truncation 3072, 003's `INSTRUCTION` bytes, Proof v0.2 against 003's `teacher.json`; no grammar; base MiniCPM route 0.10 / parse 0.15 / 9 of 9 passing at 856.6 tokens per paragraph.
- **Wall time:** 006 about 75 to 100 min including about 35 min of greedy generation scoring; 007 about 2 to 3 min, almost all model load.
- **Rig discipline:** every model load under `flock /tmp/melodyscribe-gpu.lock`, one model per process, GPU steps foreground; `TRITON_LIBCUDA_PATH=/run/opengl-driver/lib` and `HF_HUB_OFFLINE=1` exported by `run.sh`; no network steps exist in either spike.
- **Determinism:** 007 rep1 versus rep2 max abs diff 0.0 on both models; 006 m1/m2 merges byte-identical; greedy decode resumable.

## Origin

Synthesized from spikes: 006, 007; research: deep-research-2 REPORT.md sections 1 and 5A

Source files available in: sources/006-hybrid-embedder/, sources/007-embedding-prompt-sensitivity/

# Model Size and Training

## Requirements

From the `melodyscribe` idea in `.planning/spikes/MANIFEST.md`, the four that this area owns:

- Model size is a rig variable; report the size-versus-accuracy curve before choosing (D-MS-05)
- Grammar constraints guarantee format only; accuracy comes from training and is measured on the rig
- No vendor benchmark settles anything; every verdict comes from a local measurement on the 20-document parity corpus
- Every measurement run holds the GPU lock so numbers are never taken under contention

## How to Build It

Two harnesses share one setup: `source .planning/spikes/env.sh` (exports `$MELODYSCRIBE_PY`, `$MELODYSCRIBE_MODELS`, the CUDA library path), Q8 GGUF files under `.planning/spikes/.models`, the 20-document corpus at `databasise/tests/fixtures/corpus/` (hash-verified on every load), every model load under `flock /tmp/melodyscribe-gpu.lock`, one model per process. Network and CPU steps run without the lock.

### (a) Teacher labelling and the size sweep (spike 003)

**Step 1. Fix the prompt bytes once.** `.planning/spikes/003-op-emission-size-sweep/common.py` holds one `INSTRUCTION` string. The teacher receives it as a chat user message; every student receives `INSTRUCTION + "\n\nSection:\n" + content + "\n\nJSON:\n"` as a raw completion prompt. No per-model chat template on the student side, so the input is identical across arms and Qwen3 thinking has no trigger.

**Step 2. Call the teacher with reasoning disabled.** Credentials are sourced at runtime with `set -a; source v1/.env.parity; set +a` and never printed or written. The pinned model is a reasoning model, so the request disables thinking explicitly and merges that with the project's `OPENAI_LLM_EXTRA_BODY` instead of replacing it. From `teacher.py`:

```python
body = {"model": MODEL, "messages": messages, "temperature": 0,
        "max_tokens": max_tokens,
        "reasoning": {"effort": "none", "exclude": True}}
if extra:
    merged = dict(extra)
    merged.setdefault("reasoning", {"effort": "none", "exclude": True})
    body["extra_body"] = merged
...
if not text.strip():
    raise RuntimeError(f"reasoning-only response (reasoning_tokens={rt})")
```

`MAX_TOKENS = 4096`, one retry at `MAX_TOKENS_RETRY = 8192` on a reasoning-only reply, `TIMEOUT_S = 180`. Result on the full run: 47/47 rounds returned content with 0 reasoning tokens.

**Step 3. Proof-repair loop, best round wins.** Each reply is parsed (strict JSON, then brace extraction), quotes are resolved to offsets by `resolve.py`, and spike 001's Proof runs unchanged. Up to `MAX_ROUNDS = 3`. The repair message feeds Proof reasons back and pins the passing ops; the accepted label is the round with the most passing ops, not the last round. From `teacher.py`:

```python
res = v02.validate_v02(obj, FILE_SET, content, ops_validate)
if best is None or len(res["passed"]) > len(best["passed"]):
    best = res
...
{"role": "user", "content":
 "Proof rejected some ops. Keep every PASSING op "
 "byte-identical; change only the rejected ones. "
 "Each quote must be ONE contiguous substring copied "
 "character-for-character from the section -- never "
 "join spans with '...' and never paraphrase. ..."}
...
final = best if best is not None else verdict
```

A document is accepted when at least one op passes; failing ops are dropped from the label and kept in the log with reasons. Best-round fired on 9/20 documents.

**Step 4. `teacher.json` shape.** Written by `teacher.py`, read by `evaluate.py` (which asserts `corpus_hash` and `schema`):

```json
{"corpus_hash": "ac55d19e...", "file_set": ["graph", "sql"], "schema": "ops.v0.2",
 "labels": {"ed_wood": {"ops": [{"target": "graph", "s": "...", "p": "...", "o": "...", "quote": "..."},
                               {"target": "sql", "subject": "...", "attribute": "...", "value": "...",
                                "value_type": "date", "quote": "..."}],
                       "spans": [[start, end], ...], "_rounds": 2, "_dropped": 0}}}
```

**Step 5. Student runner, one process per arm.** `student.py <arm>` loads the arm's GGUF with full GPU offload (`n_gpu_layers=-1`, `n_ctx=4096`), builds the v0.2 GBNF grammar once, and decodes all 20 units greedily. From `student.py`:

```python
ARMS = {"minicpm1b": "MiniCPM5-1B-Q8_0.gguf", "minicpm2b": "MiniCPM5-2B-Q8_0.gguf",
        "qwen1p7b": "Qwen3-1.7B-Q8_0.gguf", "qwen4b": "Qwen3-4B-Q8_0.gguf",
        "qwen8b": "Qwen3-8B-Q8_0.gguf"}
MAX_TOKENS = 1024
TEMPERATURE = 0.0
SEED = 1234
...
res = llm.create_completion(prompt, grammar=grammar,
                            max_tokens=max_tokens,
                            temperature=TEMPERATURE, seed=SEED)
text = res["choices"][0]["text"]
...
think = "<think" in text.lower() or "<thinking" in text.lower()
```

Every output records raw text, prompt and completion tokens from llama.cpp usage, wall seconds, and the think-tag flag. `run.sh` wraps each arm as `flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$S/student.py" "$arm"`. Flags: `--units=i,j` (subset), `--repeat=N` (determinism), `--chat` (model template, output `<arm>_chat.json`), `--max-tokens=N`, `--out=NAME`.

**Step 6. Score.** `evaluate.py` is stdlib only, no GPU, no network. Per arm, macro-averaged over the 20 documents:

- `routing_exact`: fraction of documents where the student's Proof-passing target set equals the teacher's. Alias-free, the head-to-head comparator.
- `subjval_recall`: mean over documents of matched teacher ops / teacher ops, matched when a passing student op shares target, normalised subject, and normalised value. Strict lower bound.
- `op_f1`: micro F1 over normalised (target, subject, predicate/attribute, value) tuples. Strict lower bound.
- `parse_rate`: outputs that strict-parse as `{"ops":[...]}` / 20.
- `proof_pass_rate`: passing student ops / emitted student ops.
- `tokens_per_para`, `secs_per_para`: mean completion tokens and wall seconds per document.
- `fail_reasons`: count per Proof category (`evidence`, `value-type`, `schema`, `unparseable-output`), from the same code that gates dispatch.

The routing metric, from `evaluate.py`:

```python
def norm(s: str) -> str:
    return " ".join(str(s).lower().split())
...
if {x.get("target") for x in s} == {x.get("target") for x in t}:
    route_hit += 1
```

**Step 7. Results, primary table (`results.json`, identical 1024-token cap, from the spike README):**

| arm (Q8) | route_exact | subj/val recall | op F1 | parse | Proof-pass | tok/para | s/para |
|---|---|---|---|---|---|---|---|
| minicpm1b (1B) | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 (vacuous, 0 ops) | 4.0 | 0.09 |
| minicpm2b (2B) | 0.450 | 0.024 | 0.000 | 0.950 | 0.714 | 269.9 | 7.68 |
| qwen1p7b (1.7B) | 0.300 | 0.034 | 0.018 | 1.000 | 0.600 | 79.0 | 1.99 |
| qwen4b (4B) | 0.350 | 0.126 | 0.023 | 1.000 | 0.500 | 313.6 | 10.55 |
| qwen8b (8B) | 0.450 | 0.180 | 0.058 | 0.750 | 0.836 | 556.3 | 24.59 |

Emitted/passed ops: 1B 0/0; 2B 98/70; 1.7B 25/15; 4B 110/55; 8B 128/107. Failure reasons by Proof category (`results.json`): 2B evidence 28, unparseable 1; 1.7B evidence 8, schema 1, value-type 1; 4B evidence 51, value-type 4; 8B evidence 15, value-type 6, unparseable 5 (all five cut at exactly 1024 tokens). Token counts and every accuracy metric are byte-identical between the agent run and the owner re-run; only the seconds column drifts (owner re-run in `results.json`: 0.10, 7.93, 2.09, 10.52, 23.42).

**Secondary table (`results_cap2048.json`, six truncated pairs re-decoded at 2048 and merged):** qwen8b route 0.450 to 0.500, recall 0.180 to 0.208, op F1 0.058 to 0.068, parse 0.75 to 0.95, Proof-pass 0.836 to 0.749, tok/para 556.3 to 633.2, s/para 26.42; minicpm2b unchanged at route 0.450 (the `a_kiss_for_corliss` loop persists at 2048, tok/para 269.9 to 321.1). Of qwen8b's five, three rescued to parsed (conrad_brooks 16/18 pass, doctor_strange 15/16, meet_corliss_archer_tv_series 9/17), village_accountant still truncated, janet_waldo parsed at 1039 tokens but 2/20 pass. Raising the cap rescues parse, not accuracy.

### (b) Embedding parity (spike 004)

**Arms.** All on identical inputs: 20 documents, 2 HotpotQA gold queries (2 gold docs each), 20 self-retrieval probes (each document's first content sentence as query, gold = itself), 75 sentence chunks for head training.

- A: Qwen3-Embedding-0.6B, native pooling (effective pooling 3 = LAST, dim 1024, about 25 ms per text).
- B: MiniCPM5-2B generative, pooling forced to LAST, dim 2048, literal `⟦EMB⟧` marker appended. B2: Qwen3-1.7B, same policy. B-plain: MiniCPM5-2B without the marker.
- C: ridge regression from frozen B states to A states on the 75 chunks (distillation, because 2 gold queries cannot supervise a 2048-dim head). Eval queries are never training inputs.

**Extraction.** From `.planning/spikes/004-self-embedding-parity/arm_embed.py`:

```python
from llama_cpp import (Llama, LLAMA_POOLING_TYPE_LAST)
...
def prep(t):
    if prefix == "passage:":
        t = "Passage: " + t
    if marker_mode == "emb":
        t = t + MARKER
    return t
...
kwargs = dict(model_path=os.path.join(models_dir, model_file), embedding=True,
              n_ctx=2048, n_gpu_layers=-1, verbose=False)
if pooling == "last":
    kwargs["pooling_type"] = LLAMA_POOLING_TYPE_LAST
m = Llama(**kwargs)
...
vecs = m.embed([prep(t) for t in texts])
```

`MARKER = "⟦EMB⟧"` in `common.py`. Each arm is one `arm_embed.py <run> <model> <pooling> <prefix> <marker_mode> <in.json> <out.json>` process under the lock; `evaluate.py` ranks by cosine (`rank_docs`, `recall_at_k` in `common.py`) and reports recall@1/3/5/10 and MRR per query set.

**Head.** From `train_head.py`, ridge with `lam` swept over 1, 100, 1e5:

```python
A = Xs.T @ Xs + lam * np.eye(d)
W = np.linalg.solve(A, Xs.T @ Ys)  # d x t
```

**Numbers (spike 004 README, `results/head2head_report.json`):**

| arm | gold r@1 / r@3 / r@10 / MRR | self r@1 / r@3 / r@10 / MRR |
|---|---|---|
| A dedicated 0.6B | 0.50 / 0.75 / 1.00 / 1.00 | 0.85 / 1.00 / 1.00 / 0.91 |
| B MiniCPM5-2B last-token + marker | 0.00 / 0.25 / 0.50 / 0.31 | 0.40 / 0.60 / 0.80 / 0.55 |
| B2 Qwen3-1.7B last-token + marker | 0.00 / 0.00 / 0.50 / 0.13 | 0.25 / 0.50 / 0.75 / 0.43 |
| B + ridge head (lam=1) | 0.00 / 0.00 / 0.25 / 0.17 | 0.30 / 0.55 / 0.85 / 0.49 |
| B-plain + ridge head (lam=1) | 0.00 / 0.00 / 0.75 / 0.15 | 0.35 / 0.70 / 0.95 / 0.56 |
| B2 centered, no training | 0.25 / 0.50 / 0.50 / n.a. | 0.55 / 0.65 / 0.90 / n.a. |

B without the marker: gold MRR 0.33, self MRR 0.56, so the marker is not the cause (0.31 vs 0.33).

**Anisotropy diagnosis** (`diagnose.py`, `logs/diag1.jsonl`): mean pairwise document cosine A 0.278, B 0.914, B2 0.949, B-plain 0.776. Untrained last-token states all point nearly the same way; cosine carries almost no ranking signal. The marker makes it worse (0.914 vs 0.776).

**Why the linear head fails.** Train cosine 0.65 at lam=1 (0.74 on plain states), yet query-to-document recall falls: gold MRR 0.31 to 0.17, self 0.55 to 0.49; larger lam degrades further (MRR 0.09). d = 2048 against n = 75 overfits, and the head is trained on declarative chunks but tested on interrogative queries. In-distribution chunk-to-chunk recall moves only slightly (plain+head r@1 0.32 to 0.37; marker+head 0.31 to 0.29). Corpus-mean centering helps B2 a lot (gold r@3 0.00 to 0.50) and barely moves B (0.25 to 0.25): B2's deficit is a shared-direction offset, B's is structural.

### The training path this implies

1. **Fine-tune targets come from 003's Proof failures.** The three categories that kill 30 to 50 percent of student ops: evidence quote must contain the subject or the value verbatim (dominant category on every arm); `value_type: date` values in ISO 8601 or a bare year (rejected examples: "May 9, 1902", "1980s"); termination (minicpm2b looped one op about 66 times until the cap on `a_kiss_for_corliss`, at 1024 and again at 2048). Rationale-augmented SFT on the teacher labels first, then on-policy distillation, as LoRA or QLoRA with the base at Q8 and the adapter in bf16; then RL with verifiable rewards (Proof pass, retrieval hit, SQL execution) per `reference/micro-harnesses/efficiency-design.md` section 5.
2. **Self-embedding is an adapter experiment, not a head experiment.** The open test is a contrastive or LLM2Vec-style adapter over the generative model (OneGen joint objective: generation loss plus contrastive loss at the `[EMB]`/`[RQ]` positions, as LoRA; LLM2Vec needs bidirectional attention plus MNTP; GritLM is the same idea at 7B). Success criterion: match arm A (gold MRR 1.00, self MRR 0.91, pairwise cosine 0.28) on identical inputs. Until then Qwen3-Embedding-0.6B owns the durable index.
3. **What labelled data exists.** `teacher.json`: 204 Proof-passing ops with resolved spans over 20 documents, schema `ops.v0.2`, targets graph and sql. That is enough for the op-emission SFT stage.
4. **What is missing.** Query-to-passage pairs for contrastive training; the corpus has 2 gold queries. Produce them with the same teacher path (reasoning off, Proof-style acceptance) before the adapter spike runs.
5. **Naming and re-index.** Trained checkpoints are `MelodyScribe-{size}-v{version}` (D-MS-04). Each fine-tune of a self-embedding model is a new embedding space; the token policy string (`emb=reserved:130080;rq=reserved:130081` for MiniCPM5-2B; `emb=native:last` for Qwen3-Embedding-0.6B; `emb=literal:⟦EMB⟧/last` for the untrained generative arms) enters the space identity.
6. **Size ladder on legion.** Sweep 1B, 2B, 4B, 8B dense locally for inference and training; a 30B to 40B mixture of experts runs locally for inference only with expert weights offloaded to system RAM (about 17 GB at 4-bit for 30B-A3B, above the 16 GB card); its LoRA fine-tune rents a larger GPU and is budgeted only after the dense sweep shows the size trend is worth it. Re-run the 003 sweep after fine-tuning; the size question reopens then.

## What to Avoid

- **A reasoning teacher with the default budget returns no content.** The first probe spent the whole budget as `reasoning_tokens` with `content: None`; 7/7 documents failed. Set `"reasoning": {"effort": "none", "exclude": true}` and `max_tokens` of at least 4096, and treat an empty `content` as an error to retry, not a label.
- **Character-offset evidence (v0.1).** With `[start, end]` offsets, 8/8 and 10/10 teacher ops were Proof-rejected; frontier and small models alike cannot count characters. Evidence is a verbatim quote (3 to 256 characters) that the harness resolves to offsets after Proof's own normalisation.
- **Repair replies that rewrite passing ops.** Pilot on `ed_wood`: round 1 passed 14/16; the repair round fixed the 2 rejects and rewrote passing ops with `...`-joined quotes, 4/16. Pin passing ops byte-identical in the prompt and accept the best round's passing set.
- **Per-arm chat templates.** Templates differ per model, so the inputs stop being identical and Qwen3 gets a `<think>` trigger. Decode by raw completion with the same prompt bytes; scan every output for think tags and report the count (0 in 126 decodes).
- **Reading recall growth as accuracy growth.** Subject/value recall rises 0.02 to 0.18 from 2B to 8B while routing stays 0.30 to 0.45 and op F1 stays below 0.06; recall tracks emitted tokens (80 to 11126 total). Compare arms on `routing_exact` and cost first.
- **A 1B model under greedy grammar decoding.** MiniCPM5-1B emitted `{"ops":[]}` on 20/20 documents, raw (4 tokens, 0.09 s) and through its own chat template (`--chat`, still 20/20 empty). A 1B revisit needs sampling or training, not prompting.
- **Untrained last-token states as embeddings.** Gold MRR 0.31 and 0.13 against 1.00, pairwise cosine 0.91 to 0.95. The `⟦EMB⟧` marker moves the state (plain vs marked cosine 0.30) without improving it.
- **A ridge head as the fix for anisotropy.** It fits the chunks (cosine 0.65 to 0.74) and lowers query recall at every lambda. The corpus has 2 gold queries; d = 2048 against n = 75 overfits by construction.
- **String-match scoring without a normaliser.** Teacher writes "Edward Davis Wood Jr." and "1924-10-10"; students write "Ed Wood" and "October 10, 1924". Recall and F1 are lower bounds until a trained normaliser exists; do not rank arms on them.
- **A grammar without a token cap.** The grammar guarantees shape, only the cap guarantees termination (the 66x loop). Every decode step carries a cap, and truncation is its own Proof category.
- **Empty or over-length sections at the embedder.** Empty input: arm A returns a degenerate vector silently (norm 118 against about 1), arm B hard-errors (`llama_decode returned -1`) and poisons the process. 4201 tokens against `n_ctx` 2048: both truncate silently. Reject empties and enforce limits before the model.

## Constraints

- **Arms and files (Q8_0 GGUF, `student.py`):** minicpm1b `MiniCPM5-1B-Q8_0.gguf`, minicpm2b `MiniCPM5-2B-Q8_0.gguf`, qwen1p7b `Qwen3-1.7B-Q8_0.gguf`, qwen4b `Qwen3-4B-Q8_0.gguf`, qwen8b `Qwen3-8B-Q8_0.gguf`. Embedder `Qwen3-Embedding-0.6B-Q8_0.gguf`. Q8 everywhere so quantisation stays out of the size comparison.
- **Corpus:** 20 documents (title plus one paragraph, about 9.6 KB of text), 2 HotpotQA gold queries; `corpus_hash` `ac55d19ec162cc9abf51ddf8502436109b1439c5cbaea4cf41c448c11575d5bd`, asserted by `evaluate.py` against `teacher.json` and every `students/*.json`.
- **Decode settings:** raw completion, temperature 0, seed 1234, `n_ctx` 4096, cap 1024 primary (2048 secondary), grammar `score-io-v0.2-spike003 file=graph,sql`, at most 32 ops per section.
- **Teacher acceptance:** 20/20 documents accepted, 204 ops, 26 dropped, 47 rounds, 0 reasoning tokens; 4 documents accepted in round 1, 5 in round 2, 11 in round 3; best-round on 9/20. Per-document counts are the table in the spike 003 README. Teacher wall time about 7 minutes (network), students about 15 minutes (GPU), about 25 minutes end to end.
- **Cost per paragraph:** 4 to 633 completion tokens and 0.1 to 25 seconds across arms (1B floor, 8B at the 2048 cap ceiling).
- **Reproduction:** the owner re-run of `run.sh` reproduced all 126 student decodes (100 primary plus 26 follow-up) byte-identically with every metric equal; `qwen1p7b --repeat=3` on 3 documents was 3/3 identical.
- **Spike 004 facts:** arm A dim 1024, arms B/B2 dim 2048, `n_ctx` 2048, 75 training chunks; gold MRR A 1.00, B 0.31, B2 0.13, B+head 0.17, B-plain+head 0.15; self MRR A 0.91, B 0.55, B2 0.43, B+head 0.49, B-plain+head 0.56; pairwise document cosine A 0.278, B 0.914, B2 0.949, B-plain 0.776; re-embedded arm A documents max abs diff 0.0; about 15 minutes wall, about 2 minutes of it GPU. Verdict PARTIAL: the head-to-head is decisive, parity was not reached, and the trained arm is a linear proxy.
- **Rig:** RTX 3080 Laptop, 16 GB VRAM, llama-cpp-python 0.3.35 (CUDA wheel cu125); two live `Llama` instances in one process crash at exit on this rig, so one model per process.
- **Spec state:** v0.2 (quote evidence) is a spike-local deviation in `ops.v0.2.schema.json` and `v02_grammar.py`; owner review pending on whether it replaces SCORE-IO-SPEC section 5.

## Origin

Synthesized from spikes: 003, 004

Source files available in: sources/003-op-emission-size-sweep/, sources/004-self-embedding-parity/

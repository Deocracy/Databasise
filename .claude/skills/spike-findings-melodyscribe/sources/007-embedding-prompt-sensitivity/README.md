---
spike: 007
idea: melodyscribe
name: embedding-prompt-sensitivity
type: comparison
validates: "Given the corpus and the shared query set, when documents and queries are embedded under different instruction, prefix, and marker designs on the dedicated 0.6B embedder and on the 2B [EMB] state, then recall@k, MRR, and anisotropy per design on identical inputs"
verdict: VALIDATED
related: [002, 004]
tags: [embeddings, prompts, instructions, doc-prefix]
---

# Spike 007: embedding-prompt-sensitivity

## What This Validates

Does the prompt around a text change its embedding enough to matter, and which
design should the Score's `doc_prefix` and query prefix use. Spike 004 found the
`Passage:` versus bare prefix insensitive on the 0.6B embedder, on two gold queries.
This spike measures it properly on the 116 shared queries, on both the trained
embedder and the generative path. Read `.claude/skills/spike-findings-melodyscribe/references/score-io-contract.md` (token policy, `doc_prefix` default) and `model-size-and-training.md` first.

## Research

- Qwen3-Embedding documented query format: `Instruct: <instruction>\nQuery: <query>`,
  documents bare. Generic retrieval instruction used verbatim-style:
  "Given a web search query, retrieve relevant passages that answer the query".
- Task instruction (this corpus): "Given a question about films and the people who
  made them, retrieve the passage that answers the question". Wrong-domain control:
  "Given a code search query, retrieve relevant code snippets that implement the
  required functionality".
- MiniCPM5-2B chat template read from `.models/hf/openbmb__MiniCPM5-2B/chat_template.jinja`:
  a system turn renders as `<s><|im_start|>system\n{content}<|im_end|>\n` (bos `<s>`
  from `special_tokens_map.json`). That rendered turn is the v0.1 `doc_prefix`
  default arm (G07 sys-prefix).
- PromptEOL style (`This sentence: "<text>" means in one word:`) as one suffix arm;
  `" The passage is about"` trailing-phrase arm per plan item 8.
- Settled results reused, not re-measured: empty-input behaviour (A degenerate,
  B hard-errors), silent truncation past `n_ctx`, one model per process, GPU lock,
  reserved-vs-literal marker finding (spikes 002/004). Inputs here are guarded
  instead: build refuses empty renders, longest rendered text is 1321 chars
  against `n_ctx` 4096, corpus contains zero `⟦EMB⟧` collisions (grep count 0).

## How to Run

```bash
./run.sh   # from this folder; needs the prepared venv, models, corpus (CONVENTIONS.md)
```

`run.sh` builds inputs (CPU), embeds all 532 embedder texts x3 reps and all 238
generative texts x3 reps (each load under `flock /tmp/melodyscribe-gpu.lock`, one
model per process), evaluates rep1 with a rep1-vs-rep2 determinism check (CPU),
and prints a timing summary. About 2--3 minutes, almost all of it model load.

## What to Expect

- `results/head2head_report.json`: recall@1/@3/@10, MRR (full/nl/keyword splits),
  gold-2 RR, anisotropy, query-doc gap per design, determinism diffs.
- `results/vecs_*.json`: raw vectors (git-ignored, ~11 MB each for the embedder).
- `logs/*.jsonl`: build, 6 embed runs, eval event — every number below traces here.

## Investigation Trail

1. `build` — rendered 532 embedder + 238 generative texts from the hash-verified
   corpus and `queries-v1.json` (hash asserted). 116 queries, 20 keyword-style
   (`#5` ids), 96 NL. Log: `logs/build.jsonl`.
2. `emb_rep1` — Qwen3-Embedding-0.6B, native pooling (effective 3), n_embd 1024,
   532 texts in 2.9 s (5.43 ms/text). Reboot killed the follow-up batch mid-run;
   rep1/rep2 files survived intact (see 7).
3. Recovery: verified rep1/rep2 logs complete and vecs valid (532 ids), then ran
   `emb_rep3` + `gen_rep1..3` under the lock. MiniCPM5-2B LAST pooling,
   238 texts in 3.9--4.9 s (16--21 ms/text). `llama_init_from_model` pooling
   notice (`[-1]` vs `[3]`) is informational, same as spike 004.
4. `head2head` — full table (Results). Determinism rep1-vs-rep2 max abs diff
   **0.0 on both models**: re-runs are byte-identical.
5. Surprise follow-up A (keyword split): E02 vendor-q lifts keyword MRR
   0.729 -> 0.870 (+0.141, n=20). Paired flips: 6 keyword queries improve rank,
   2 worsen (`tyler_bates#5` 2->7, `janet_waldo#5` 3->4); rank>3-to-<=3 flips are
   2-vs-2. Real direction, noisy base: exploratory, below the pre-registered bar.
6. Surprise follow-up B (generative sys-prefix): G07sys +0.045 MRR, with 32 queries
   improving >=5 ranks vs 20 worsening >=5. Net positive, noisy, below the 0.05 bar.
7. Edge probes (CPU): no empty renders (build asserts); max rendered length 1321
   chars << n_ctx 4096 (no truncation); zero `⟦EMB⟧` in corpus content; all 532/238
   ids unique. Empty/overlong model behaviour cited from 004, not re-measured.

## Results

Verdict: **VALIDATED**. All 9 plan designs measured on identical inputs per model,
embeddings byte-identical across reps, pre-registered materiality bar (full-set
MRR move >= 0.05) applied as stated: **no design is material on either model**.

Head-to-head, full 116-query set (rep1; `results/head2head_report.json`):

| design | r@1 | r@3 | r@10 | MRR | aniso | gap | ms/text |
|---|---|---|---|---|---|---|---|
| E01 none (baseline) | 0.681 | 0.879 | 0.991 | 0.792 | 0.2775 | 0.2130 | 5.3--8.0 |
| E02 vendor-q | 0.716 | 0.888 | 1.000 | 0.814 (+0.022) | 0.2775 | 0.2607 | — |
| E03 task-q | 0.733 | 0.879 | 0.991 | 0.813 (+0.021) | 0.2775 | 0.2586 | — |
| E04 wrong-domain-q | 0.664 | 0.853 | 0.991 | 0.774 (-0.018) | 0.2775 | 0.2139 | — |
| E05 instruction both sides | 0.672 | 0.905 | 0.991 | 0.789 (-0.003) | 0.2584 | 0.2569 | — |
| E06 title prefix | 0.724 | 0.897 | 0.991 | 0.820 (+0.028) | 0.2800 | 0.2143 | — |
| G01 none (baseline) | 0.181 | 0.362 | 0.664 | 0.322 | 0.9134 | 0.0145 | 16--21 |
| G07 system-turn prefix (v0.1 default) | 0.198 | 0.440 | 0.690 | 0.367 (+0.045) | 0.9273 | 0.0137 | — |
| G07 plain task prefix | 0.155 | 0.362 | 0.767 | 0.327 (+0.005) | 0.9275 | 0.0141 | — |
| G08 PromptEOL suffix | 0.095 | 0.293 | 0.681 | 0.274 (-0.048) | 0.7749 | 0.0207 | — |
| G08 "about" suffix | 0.138 | 0.241 | 0.716 | 0.271 (-0.051) | 0.7600 | 0.0218 | — |
| G06 title prefix | 0.181 | 0.310 | 0.655 | 0.314 (-0.008) | 0.9142 | 0.0146 | — |

(ms/text is per model, not per design: one process embeds all texts of that model.
Embedder reps: 5.43/5.27/8.04 ms/text. Generative reps: 20.63/18.87/16.47 ms/text.)

Sub-claims:

- **Embedder is prompt-insensitive for ranking on this corpus.** Largest move is
  E06 +0.028, under the bar; E02/E03 +0.02 despite widening the query-doc gap
  (+0.05), so matching-domain instructions shift queries toward the doc cluster
  without reordering it. Extends 004's two-query `Passage:` finding to 116 queries.
- **The wrong-domain control does not hurt** (-0.018, under the bar; gap unchanged
  0.2139 vs 0.2130). The embedder ignores the instruction for ranking here — stated
  as measured, against interest.
- **Best embedder design: E06 title prefix** (MRR 0.820), but not material (+0.028).
  Recommendation: keep bare documents; an explicit `Title:` prefix is optional.
- **No generative prompt design fixes the deficit.** Best arm G07sys MRR 0.367 vs
  embedder baseline 0.792; anisotropy persists in every arm (0.76--0.93 vs 0.28);
  gap stays ~0.015. Suffix tricks (EOL/about) lower anisotropy to ~0.77 while
  *lowering* MRR — anisotropy alone does not predict recall.
- **v0.1 `doc_prefix` default (system turn) holds by default, not by proof.**
  G07sys +0.045 trends positive but misses the bar with noisy flips (32 up / 20
  down >=5 ranks). Keeping the template prefix costs nothing; claiming it helps
  would overstate the evidence.
- **Exploratory (not pre-registered):** vendor/task instructions help keyword-style
  queries (E02 keyword MRR +0.141, r@1 0.55->0.80, n=20) with mixed flips. If a
  later query stream is keyword-heavy, re-test E02 on that stream; do not adopt
  from n=20.
- Splits: NL (n=96) mirrors full-set ordering on both models; gold-2 queries are
  RR 1.00 on every embedder design and noisy on generative (0.07--1.00, n=2).
  Determinism: max abs diff 0.0 both models (`head2head_report.json`).

Owner re-run (2026-09-12): `run.sh` re-run end to end under the GPU lock; all 122 ranking, anisotropy, and gap numbers in `results/head2head_report.json` equal; only per-text timings differ.

Deviation: none from the plan's 9 designs. Recovery note: a machine reboot killed
the first embed batch after `emb_rep2`; surviving files were verified (complete
logs, 532 valid vecs) before continuing — no rework, no data loss.

---
spike: 008
idea: melodyscribe
name: graph-prompt-design
type: comparison
validates: "Given spike 003's teacher labels, when MiniCPM5-2B and Qwen3-4B emit ops under the v0.2 grammar with different prompt designs, then routing_exact, Proof-pass rate, recall and F1 against the teacher, and tokens per paragraph per design"
verdict: VALIDATED
related: [001, 003]
tags: [prompts, graph, extraction, few-shot]
---

# Spike 008: graph-prompt-design

## What This Validates

Which prompt gets the most correct graph and SQL ops out of a small model
before any fine-tuning, and what the cache-friendly placement of the
instruction costs. Spike 003 used one schema-only zero-shot instruction; this
spike varies it on identical inputs. Read
`.claude/skills/spike-findings-melodyscribe/references/model-size-and-training.md`
and `score-io-contract.md` first; reuses
`.planning/spikes/003-op-emission-size-sweep/student.py`, `evaluate.py`,
`common.py`, `resolve.py`, `v02_grammar.py`, and `teacher.json` read-only
through `sys.path` (copied what it had to change into this folder; never
edited spike 003).

## Plan

Models: MiniCPM5-2B Q8 and Qwen3-4B Q8 (GGUF), raw completion, temperature 0,
seed fixed, 1024-token cap, think tags scanned, exactly as spike 003.

Held-out rule: few-shot examples come only from documents that are not
scored. The 4 example documents are the 4 middle entries of the
teacher-labelled docs sorted by (op count, doc id):
`shirley_temple` (9 ops), `adam_collis`, `deliver_us_from_evil_2014_film`,
`scott_derrickson` (10 ops each). The other 16 are scored for every design,
including the zero-shot baseline, so all designs share one scored set.

Designs:

- D0: spike 003's schema-only zero-shot instruction (baseline, must reproduce 003's numbers on the 16-document subset).
- D1: one-shot, one held-out example (section plus its teacher ops).
- D2: three-shot.
- D3: two-step: first emit the entity list under a grammar, then emit ops with that list in context; report the combined tokens.
- D4: a LightRAG-style extraction instruction adapted to the schema (entity types named, relation descriptions, "extract all").
- D5: predicate vocabulary hint: the most frequent predicates and attributes from the example documents' teacher ops listed in the instruction (14 distinct: occupation (13), starring (5), role (4), down to singletons).
- D6: D0 with the instruction placed after the section instead of before it (the placement the one-pass design prefers so the section prefix is shared across tasks).
- D7: D0 with a one-line plan prefix ("List the entities, then the facts with dates, then the relations.") and thinking still disabled.

Metrics from `evaluate.py`: routing_exact, subject/value recall, op
precision, recall, F1, parse rate, Proof-pass rate with failure categories,
tokens and seconds per paragraph. Report each design on both models in one
table.

Pass conditions, stated before the run: the best design must beat D0 by at
least 0.10 routing_exact or 0.10 Proof-pass rate on a model to be
recommended; D6's penalty relative to D0 is reported as the cost of
cache-friendly placement; the recommended instruction text is written to
`results/best-prompt.md` with its numbers.

Environment: `.venv`, `env.sh`, GPU lock on every model load, one model per
process; the 003 harness already handles this when called per arm.

## Research

- Spike 003 (`model-size-and-training.md`): 003's INSTRUCTION bytes, teacher
  labels (`teacher.json`, 204 Proof-passing v0.2 ops over 20 docs), student
  decode settings (raw completion, temp 0, seed 1234, cap 1024, Q8 GGUF), and
  the metric definitions (`routing_exact` alias-free comparator,
  `subjval_recall` / `op_f1` strict lower bounds, Proof failure categories).
  D0 reuses the INSTRUCTION string by import, so the baseline is
  byte-identical by construction (verified on all 16 scored docs).
- Spec v0.2 (`score-io-contract.md` step 9): quote evidence resolved
  harness-side by `resolve.py`; the v0.2 GBNF grammar and `validate_v02`
  imported read-only. New: a second GBNF grammar for D3 step 1,
  `{"entities": [...]}` (`prompts.entity_grammar()`), format-only like the
  ops grammar.
- LightRAG extraction prompt (`v1/lightrag/prompt.py`,
  `entity_extraction_system_prompt`): the source D4 adapts — named entity
  types (Person/Organization/Location/Event/Content/Concept/Artifact/Other),
  "extract ALL entities first, then ALL binary relations", consistent naming,
  no pronouns, output content only. Adapted to emit v0.2 JSON under the same
  grammar instead of LightRAG tuple rows, so the comparison measures prompt
  wording, not output format.
- Prior finding reused without re-measuring: greedy seed-fixed decodes are
  the comparator (003 verified 3/3 identical on qwen1p7b); this spike
  re-checks determinism per arm and finds it does NOT always hold (see
  Investigation Trail, Surprise 1) — the spike's main methodological result.

## How to Run

From the repo root:

```bash
./.planning/spikes/008-graph-prompt-design/run.sh
```

`run.sh` runs: module/grammar self-check; `student8.py minicpm2b` (full 16
docs x 8 designs, one model load); `student8.py qwen4b` in two halves
(`--units=0..7 --suffix=_h1`, `--units=8..15 --suffix=_h2`, rejoined by
`merge8.py`); `probe_repeat.py` per arm (re-decodes D0 on diverged docs, the
noise-floor probe); `evaluate8.py` (16-doc head-to-head plus the D0-vs-003
byte-reproduction check). Every model load runs under
`flock /tmp/melodyscribe-gpu.lock`, one model per process; merge/score hold
no lock (stdlib only). `make_best_prompt.py` writes
`results/best-prompt.md` from the winning prompt bytes (no GPU).

Wall time on legion (RTX 3080 Laptop): minicpm2b ~17 min for 128 decodes +
16 step-1s + 2 determinism checks; qwen4b ~33 min for 144 decodes (~13.9 s
mean); probes ~5 min. About 55 min end to end, all GPU steps lock-held.

## What to Expect

- `students/D<0-7>_<minicpm2b|qwen4b>.json`: 16 files, same shape as spike-003
  student files plus `design`/`example_docs` metadata (D3 carries
  `step1_text`, `step1_entities`, and combined usage). Split halves
  `D*_qwen4b_h1/h2.json` remain on disk; the merged files are authoritative.
- `students/D0_<arm>_rep2.json`: repeat-probe outputs (3 docs 2B, 7 docs 4B).
- `results.json`: head-to-head table, per-doc rows, fail reasons, think-tag
  counts, and `d0_reproduction_vs_003`.
- `results/best-prompt.md`: the recommended D1 prompt with its numbers.
- `logs/`: one JSONL file per run (ISO timestamps): `student8-<arm>-<utc>`,
  `probe-repeat-<arm>-<utc>`, `score-<utc>` (score events only; merge/score
  reruns are deterministic modulo the `ts` field).

## Investigation Trail

1. **Setup + dry-run validation (no GPU).** Wrote `prompts.py` (8 designs,
   median split, vocab hint, entity grammar), `student8.py` (one process per
   arm, D3 two-step, D0 double-decode determinism self-check), `evaluate8.py`
   (003-identical metrics over the 16 scored docs + D0 byte-reproduction
   check), `run.sh`. Verified: D0 prompt bytes identical to 003 on all 16
   docs; both GBNF grammars construct via `LlamaGrammar.from_string`; D2
   prompt 8132 chars (~2.3k prompt tokens, inside n_ctx 4096); scoring the
   003 files on the 16-doc subset gives the D0 targets (2B route 0.438,
   proof 0.658; 4B route 0.312, proof 0.433). No log (CPU-only checks).
2. **Smoke test (GPU, 2 docs x 8 designs, minicpm2b).**
   `logs/student8-minicpm2b-20260912T153303Z.jsonl`. D0 byte-reproduced 003
   on both docs; D3 step-1 entities sane
   (`{"entities": ["Secretary of State for Constitutional Affairs", ...]}`);
   D4 emitted `{"ops":[]}` (5 completion tokens) on both docs; 0 think tags.
3. **Full minicpm2b run killed by machine reboot.**
   `logs/student8-minicpm2b-20260912T153444Z.jsonl` stops after 22 decodes;
   no students files written (they flush at process end). Re-ran from
   scratch after reboot: `logs/student8-minicpm2b-20260912T161001Z.jsonl`,
   all 8 designs x 16 docs, think_hits=0.
4. **qwen4b full run killed mid-arm (tool timeout, ~11 min, 46 decodes).**
   `logs/student8-qwen4b-20260912T163036Z.jsonl` ends at D5/a_kiss_for_corliss.
   Added `--suffix` to `student8.py` (plumbing only, no method change) and
   ran qwen4b in halves: `logs/student8-qwen4b-20260912T164434Z.jsonl`
   (units 0-7) and `...T170447Z.jsonl` (units 8-15), think_hits=0 both;
   `run.sh` encodes the halves+merge so a kill loses at most half the arm.
   Merged with `merge8.py` (asserts disjoint halves covering the scored set,
   one corpus hash). Dead log `...T163036Z.jsonl` kept as evidence.
5. **Surprise 1: greedy decoding is not run-stable.** D0-vs-003 agreement is
   13/16 (2B) and 9/16 (4B), and the in-process determinism self-checks
   failed (2B 0/3 identical back-to-back; 4B 1/2). Follow-up probe
   (`probe_repeat.py`,
   `logs/probe-repeat-minicpm2b-20260912T173349Z.jsonl`,
   `logs/probe-repeat-qwen4b-20260912T173433Z.jsonl`): of 10 re-decodes, 3
   match this run and 3 match 003 — three runs give ~3 distinct outputs on
   unstable docs, diverging mid-string (first-divergence offsets 55-1055),
   i.e. near-tie flips cascading under GPU nondeterminism. Metric-level
   swing on identical prompts: 2B route 0.438 (003) to 0.500 (rerun), proof
   0.658 to 0.754; 4B route 0.312 to 0.375, proof 0.433 to 0.360. Noise
   floor: ~0.06 routing_exact, ~0.10 Proof-pass. Design deltas below that
   are not trusted; D1/D3/D6 wins on qwen4b clear it (see Results).
   Per-doc routing across the three samples (analysis, no log): unstable
   docs flip target sets run to run (e.g. 4B meet_corliss [graph,sql] ->
   [sql,sql] -> [graph x3]; conrad_brooks once UNPARSED at the 1024 cap,
   once 15 passing ops).
6. **Surprise 2: D4 fails opposite ways on the two models.** 2B emitted
   `{"ops":[]}` on 16/16 docs (Counter shows one unique text; parse 1.0,
   Proof-pass vacuous 1.0 on 0 ops). 4B exploded: 8/16 truncated at the
   1024 cap (UNPARSED), invented predicates (`is a`, `is`, `type`, `born`),
   `...`-joined non-verbatim quotes (evidence fails 34). The LightRAG-style
   wording is anti-adapted to the v0.2 schema on both sizes.
7. **Surprise 3: D6 placement is model-dependent, not a flat cost.** 2B:
   evidence failures double 17 -> 32, proof 0.754 -> 0.448, route 0.500 ->
   0.250. 4B: proof 0.360 -> 0.677 (+0.317), route 0.375 -> 0.500 (+0.125),
   value-type failures rise 3 -> 6 (dates). Instruction-after-section breaks
   2B quote grounding and improves 4B's.
8. **Edge cases closed (all from `results.json` / students files, no extra
   runs):** think tags 0 on all 272 decodes + 10 probe decodes; D3 step-1
   parsed as a JSON entity list on 32/32 runs (no fallback path taken);
   truncation at the 1024 cap hits every design (2B: 1-3 docs each; 4B D4:
   8/16, D7: 5/16); D5's "top-30" list has only 14 distinct predicates in
   the example docs (occupation x13 down to singletons) — listed in full,
   no padding; merge+score reruns are byte-identical modulo `ts`.

## Results

Verdict: **VALIDATED** — one-shot (D1) and two-step (D3) beat the zero-shot
baseline past the pre-registered 0.10 bar on Qwen3-4B, the placement cost
(D6) is measured per model, and the recommendation is written to
`results/best-prompt.md`. The LightRAG-style prompt (D4) is invalidated on
both models. Sub-claims:

| design | arm | route | sv_rec | op_F1 | parse | proof | tok/para | s/para |
|---|---|---|---|---|---|---|---|---|
| D0 | minicpm2b | 0.500 | 0.018 | 0.000 | 0.938 | 0.754 | 285.1 | 8.58 |
| D1 | minicpm2b | 0.562 | 0.073 | 0.058 | 0.875 | 0.830 | 433.0 | 11.69 |
| D2 | minicpm2b | 0.312 | 0.243 | 0.107 | 0.875 | 0.812 | 471.6 | 13.62 |
| D3 | minicpm2b | 0.250 | 0.099 | 0.028 | 1.000 | 0.736 | 261.3 | 7.70 |
| D4 | minicpm2b | 0.000 | 0.000 | 0.000 | 1.000 | 1.000* | 5.0 | 0.19 |
| D5 | minicpm2b | 0.375 | 0.022 | 0.000 | 0.812 | 0.738 | 366.6 | 10.11 |
| D6 | minicpm2b | 0.250 | 0.052 | 0.021 | 0.875 | 0.448 | 259.9 | 7.14 |
| D7 | minicpm2b | 0.562 | 0.024 | 0.000 | 0.938 | 0.810 | 215.7 | 5.96 |
| D0 | qwen4b | 0.375 | 0.137 | 0.030 | 0.938 | 0.360 | 353.6 | 12.80 |
| D1 | qwen4b | 0.500 | 0.213 | 0.082 | 0.812 | 0.780 | 523.9 | 18.81 |
| D2 | qwen4b | 0.250 | 0.218 | 0.172 | 0.875 | 0.728 | 456.4 | 16.20 |
| D3 | qwen4b | 0.562 | 0.265 | 0.032 | 0.875 | 0.936 | 459.9 | 16.49 |
| D4 | qwen4b | 0.188 | 0.182 | 0.056 | 0.500 | 0.595 | 790.0 | 28.39 |
| D5 | qwen4b | 0.375 | 0.070 | 0.019 | 0.812 | 0.618 | 411.7 | 19.48 |
| D6 | qwen4b | 0.500 | 0.181 | 0.035 | 0.812 | 0.677 | 593.7 | 21.22 |
| D7 | qwen4b | 0.375 | 0.105 | 0.010 | 0.688 | 0.516 | 528.5 | 19.48 |

\* D4-2B Proof-pass 1.000 is vacuous (0 ops emitted on 16/16 docs).

- **Best design: D1 one-shot, then D3 two-step (qwen4b).** D1 clears the bar
  (route +0.125, proof +0.420; evidence failures 54 -> 22) and keeps the
  one-pass property (single decode). D3 scores highest (route +0.187, proof
  +0.576; evidence failures 54 -> 5) but needs two decodes and breaks the
  one-pass design — adopt only if accuracy outweighs the extra pass. Stable
 -doc decomposition (9 run-stable docs): D1 wins 6/9 vs D0 4/9, D3 5/9,
  D6 6/9 — the wins are not just unstable-doc flips. Recommended text in
  `results/best-prompt.md`.
- **D6 placement cost is model-dependent.** 2B: route -0.250, proof -0.306
  (evidence failures 17 -> 32) — cache-friendly placement is expensive
  here. 4B: route +0.125, proof +0.317 — it helps. There is no single
  placement-cost number; prefix-sharing must be re-measured per model.
- **D4 invalidated.** 2B: total extraction collapse (16/16 empty). 4B:
  verbosity explosion (8/16 truncated, invented predicates, `...` quotes).
  LightRAG's entity-first wording does not transfer to grammar-constrained
  v0.2 op emission at 2-4B.
- **No design helps 2B past the bar.** D1 (+0.062 route / +0.076 proof) and
  D7 (+0.062 / +0.056) sit inside the ~0.06/0.10 noise floor on headline
  numbers; D1 is +3 on the 13 run-stable docs (exploratory, not a
  recommendation). D2 triples 2B recall (0.024 -> 0.243) while hurting
  routing; D2-4B has the best op_F1 (0.172) with the worst routing (0.250)
  — more examples buy teacher-likeness, not routing.
- **Mechanism.** Few-shot examples teach verbatim quoting: the gains come
  almost entirely from collapsing evidence failures (4B: 54 -> 22 (D1) ->
  5 (D3)). 2B's evidence failures barely move with examples (17 -> 16),
  which is why prompting helps 4B more than 2B. D5's vocab hint changes
  nothing on either model (route +/-0.0-0.125, proof within noise).
- **Caveat (against-interest).** Greedy seed-fixed decoding is run-unstable
  on long docs (3/16 docs on 2B, 7/16 on 4B give different outputs across
  three identical runs), so every delta in the table carries run noise of
  ~0.06 routing / ~0.10 proof. Only D1/D3/D6-on-4B clear it. The owner
  re-run of `run.sh` will re-sample, not reproduce byte-identically; stable
  docs (13/16 2B, 9/16 4B agreed across runs) should reproduce, unstable
  ones may flip.
- **Owner re-run (2026-09-12).** `run.sh` re-run end to end under the GPU lock: all 274 student decodes (16 design-arm files plus both repeat probes) byte-identical to this run, every metric in `results.json` equal. Two runs of `run.sh` therefore reproduce each other exactly; the divergence the caveat above describes is between this spike's D0 decodes and spike 003's (13/16 and 9/16 identical) and between the repeat probe and the main run within one `run.sh`, not between separate runs.
- **Cost.** Prompt tokens/para (means over scored docs): D0 340/353,
  D1 874/919, D2 2308/2442, D3 564/610 combined, D4 465/476, D5 441/453,
  D6 = D0, D7 +16. Few-shot roughly triples prompt tokens; D7's plan line
  is nearly free and mildly helps 2B only.

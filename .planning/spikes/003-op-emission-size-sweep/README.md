---
spike: 003
idea: melodyscribe
name: op-emission-size-sweep
type: comparison
validates: "Given frontier-labelled ops for the corpus, when each model size emits ops under grammar with thinking off, then routing accuracy and tokens per paragraph per size"
verdict: VALIDATED
related: [001]
tags: [size-sweep, accuracy, teacher]
---

# Spike 003: op-emission-size-sweep

## What This Validates

Given frontier-labelled ops for the corpus, when each model size emits ops
under grammar with thinking off, then routing accuracy and tokens per
paragraph per size. Five arms (MiniCPM5-1B, MiniCPM5-2B, Qwen3-1.7B/4B/8B,
all Q8) ran on identical inputs: same 20 corpus units, same prompt bytes,
same v0.2 grammar, temperature 0, fixed seed, one decode cap.

## Research

Docs read, in order: `.planning/spikes/MANIFEST.md`, spike-001
`SCORE-IO-SPEC.md` + `ops.schema.json`, `reference/micro-harnesses/README.md`,
this spike's stub README. Spike-001 artefacts (`ops_validate.py`,
grammar construction, `ops_instruction` wording, `corpus.py` loader) are
reused read-only via `sys.path`; spike 001 itself was not edited.

Approaches compared:

1. **Offset evidence (v0.1) vs quote evidence (v0.2, chosen).** The first
   attempt used the spec's `[start, end]` offsets: 7/7 teacher docs failed
   (reasoning-only responses), and whenever teacher content arrived, 8/8
   and 10/10 ops were Proof-rejected -- small and frontier models alike
   cannot count character offsets reliably. Switched to a verbatim
   `quote` substring (3..256 chars); the harness resolves it to offsets by
   first occurrence after Proof-identical normalisation, then runs
   spike-001 Proof unchanged. Recorded as a spec-v0.2 deviation (local
   `ops.v0.2.schema.json` + `v02_grammar.py`); grammar still enforces
   format only, quote length lives in the harness, exactly the spec's
   format-vs-accuracy split.
2. **Chat template vs raw completion (raw completion chosen for the
   primary).** Per-model chat templates would differ per arm, breaking
   "identical inputs". Raw completion keeps prompt bytes identical and
   disables Qwen3 thinking by construction (no template, no `<think>`
   priming). Verified empirically: 0 think tags in 100 primary decodes +
   26 follow-up decodes. A chat-template confound check on MiniCPM-1B
   (item 7 of the trail) shows the collapse is not a prompt-format
   artifact.
3. **Teacher reasoning disable.** The pinned OpenRouter model is a
   reasoning model; with the default budget all tokens went to thinking
   (`content: None`, `reasoning_tokens` = full budget). Fix:
   `"reasoning": {"effort": "none", "exclude": true}` top-level, merged
   with (not replacing) the project's `OPENAI_LLM_EXTRA_BODY`, max_tokens
   4096, temperature 0. Result: 0 reasoning tokens in all 47 rounds.
4. **Metrics.** Strict string-match scoring (target-set exact match,
   subject/value recall, full-tuple micro-F1) is alias-brittle by design
   (teacher writes "Edward Davis Wood Jr." / "1924-10-10", students write
   "Ed Wood" / "October 10, 1924"), so `routing_exact` (target sets only,
   alias-free) is the robust head-to-head comparator; recall/F1 are
   reported as strict lower bounds. Failure reasons per arm come from the
   same Proof code that gates dispatch.

## How to Run

```
# from the repo root; teacher needs the OpenRouter credentials (never printed, never written):
set -a; source v1/.env.parity; set +a
.planning/spikes/003-op-emission-size-sweep/run.sh
```

Steps: v0.2 module self-check → `teacher.py` (network only, no GPU lock;
disables reasoning, Proof-repair loop, best-round-wins, writes
`teacher.json`) → `student.py` once per arm (each load under
`flock /tmp/melodyscribe-gpu.lock`, writes `students/<arm>.json`) →
chat-template confound check (`students/minicpm1b_chat.json`) → 2048-cap
sensitivity re-decodes of the six truncated pairs → `evaluate.py` twice
(`results.json` primary; `results_cap2048.json` merged secondary). Every
attempt is a JSON line with an ISO timestamp in `logs/`
(`teacher-<utc>.jsonl`, `student-<arm>-<utc>.jsonl`, `score-<utc>.jsonl`).
Wall time observed: teacher ~7 min (network), students ~15 min (GPU),
scoring seconds. GPU steps need an idle GPU; nothing holds the lock while
waiting on the network.

`student.py` flags: `--units=i,j` (subset by sorted-corpus index),
`--repeat=N` (determinism check), `--chat` (model chat template,
output `*_chat.json`), `--max-tokens=N`, `--out=NAME`.
`evaluate.py` flags: `--merge=arm:file` (override docs),
`--out=FILE`. `SPIKE003_DOCS=id,...` restricts the teacher to a subset
(pilot use).

## What to Expect

- `teacher.json`: 20/20 docs accepted, 204 Proof-passing ops, per-doc
  rounds/dropped counts; 0 reasoning tokens.
- `students/*.json`: 5 primary arms x 20 identical units + 3 follow-up
  files; every output scanned for think tags (0 hits); one arm
  deterministic 3/3 on re-run.
- `results.json` head-to-head table (below); `results_cap2048.json`
  secondary table with the six truncated decodes rescued where rescuable.
- Runtime: ~25 min end to end (network + GPU).

## Investigation Trail

1. **v0.1 offsets failed outright.** First teacher attempt (spec offsets,
   max_tokens 2048, thinking enabled): 7/7 docs errored
   (`logs/teacher-20260912T080514Z.jsonl`: "reasoning-only response
   (budget exhausted before content)"); when content arrived, 8/8 and
   10/10 ops were Proof-rejected ("evidence span contains neither
   subject nor value"). Frontier and small models alike cannot emit exact
   character offsets. Switched to v0.2 quote evidence per the mandated
   change; resolver self-test on `ed_wood` confirmed: verbatim quote
   resolves and passes, paraphrase is "not found", wrong-span quote fails
   the span check, 2-char quote fails shape.
2. **Teacher reasoning disabled.** Probe showed `content: None` with the
   full 64-token budget spent as `reasoning_tokens`. After
   `reasoning: {effort: none, exclude: true}` + max_tokens 4096: 47/47
   rounds returned content with 0 reasoning tokens, ~307 s total decode.
3. **Repair loop degrades; best-round-wins.** Pilot (`ed_wood`): round 1
   passed 14/16; the repair reply "fixed" the 2 rejects but rewrote
   passing ops with `...`-joined non-verbatim quotes → 4/16. Fix: keep
   passing ops byte-identical (prompt), accept the best round's passing
   set. Best-round fired on 9/20 docs in the full run.
4. **Pilot student + determinism.** `qwen1p7b` x 3 docs (short/medium/long):
   valid grammar-shaped JSON, 0 think tags, ~3 s/decode. Re-run byte
   comparison: 3/3 identical at temperature 0 + seed 1234.
5. **Full teacher run** (`logs/teacher-20260912T082951Z.jsonl`): 20/20
   accepted, 204 ops, 26 dropped; 4 docs accepted round 1, 5 round 2, 11
   round 3. Per-doc acceptance is the table in Results.
6. **Full sweep, 5 arms x 20** (one process per arm, all under the GPU
   lock): MiniCPM-1B emitted `{"ops":[]}` on 20/20 (4 tokens, 0.09 s);
   six decodes hit the 1024 cap mid-JSON (1 minicpm2b, 5 qwen8b);
   minicpm2b looped one op ~66x on `a_kiss_for_corliss` (grammar assures
   shape, only the cap assures termination -- spec I4 made mechanical).
7. **Confound check: chat template.** `minicpm1b --chat` (own template):
   still 20/20 empty. The 1B collapse is the model under greedy grammar
   decoding, not the prompt format.
8. **Cap sensitivity (2048).** qwen8b: 3/5 rescued to parsed
   (conrad_brooks 16/18 Proof-pass, doctor_strange 15/16,
   meet_corliss_archer_tv_series 9/17); village_accountant still
   truncated at 2048; janet_waldo parsed (1039 tok) but only 2/20 pass --
   quotes verbatim yet missing subject/value, plus non-ISO dates, i.e.
   accuracy failure, not truncation. minicpm2b a_kiss still loops at 2048.
   Verdict: the 1024 cap binds verbose arms, but raising it rescues parse,
   not accuracy.

## Results

**Verdict: VALIDATED.** Every arm ran on identical inputs; the
size-versus-accuracy curve was measured head-to-head with edge cases
probed (empty outputs, truncation, repetition loop, template confound,
cap sensitivity, determinism). The headline is a non-result for
scale-alone: routing accuracy does not rise cleanly with size
pre-fine-tune.

Primary table (`results.json`, via `run.sh`; identical 1024-token cap):
Accuracy, token, and count columns are byte-identical between the agent run
and the owner re-run (2026-09-12, all 126 student decodes identical); the
s/para column is from the agent run and the owner re-run's `results.json`
differs by under 5 percent (for example qwen8b 24.59 vs 23.42).

| arm (Q8) | route_exact | subj/val recall | op F1 | parse | Proof-pass | tok/para | s/para |
|---|---|---|---|---|---|---|---|
| minicpm1b (1B) | 0.000 | 0.000 | 0.000 | 1.000 | 1.000* | 4.0 | 0.09 |
| minicpm2b (2B) | 0.450 | 0.024 | 0.000 | 0.950 | 0.714 | 269.9 | 7.68 |
| qwen1p7b (1.7B) | 0.300 | 0.034 | 0.018 | 1.000 | 0.600 | 79.0 | 1.99 |
| qwen4b (4B) | 0.350 | 0.126 | 0.023 | 1.000 | 0.500 | 313.6 | 10.55 |
| qwen8b (8B) | 0.450 | 0.180 | 0.058 | 0.750 | 0.836 | 556.3 | 24.59 |

\* vacuous: 0 ops emitted, nothing to reject. Emitted/passed counts:
1b 0/0; 2b 98/70; 1.7b 25/15; 4b 110/55; 8b 128/107. Failure reasons are
Proof categories: evidence dominates (2b: 28, 1.7b: 8, 4b: 51, 8b: 15),
then value-type (non-ISO dates like "May 9, 1902", "1980s"), then
truncation (8b: 5 outputs cut at exactly 1024 tokens).

Secondary (`results_cap2048.json`, six truncated pairs re-decoded at
2048): qwen8b route 0.450 -> 0.500, recall 0.180 -> 0.208, parse 0.75 ->
0.95, tok/para 556 -> 633; minicpm2b unchanged (loop, not cap). Recall
grows with verbosity (emitted tokens), not with per-op accuracy.

Teacher acceptance (`teacher.json`, 204 ops, 0 reasoning tokens):

| doc | ops | rounds | dropped | doc | ops | rounds | dropped |
|---|---|---|---|---|---|---|---|
| a_kiss_for_corliss | 6 | 3 | 1 | lord_high_treasurer | 3 | 1 | 0 |
| adam_collis | 10 | 3 | 8 | meet_corliss_archer | 5 | 3 | 1 |
| charles_craft | 16 | 3 | 1 | meet_corliss_archer_tv_series | 3 | 3 | 2 |
| conrad_brooks | 11 | 3 | 3 | scott_derrickson | 10 | 2 | 0 |
| deliver_us_from_evil | 10 | 3 | 1 | secretary_of_state | 2 | 2 | 0 |
| doctor_strange | 18 | 3 | 0 | shirley_temple | 9 | 3 | 2 |
| ed_wood | 16 | 2 | 0 | sinister_film | 4 | 1 | 0 |
| ed_wood_film | 22 | 1 | 0 | tyler_bates | 15 | 2 | 0 |
| janet_waldo | 8 | 3 | 0 | village_accountant | 18 | 2 | 5 |
| kiss_and_tell | 7 | 1 | 0 | woodson_arkansas | 11 | 3 | 1 |

Surprises and handoffs:

- **1B is unusable for op emission in this harness** (raw and templated
  prompts alike collapse to `{"ops":[]}`); the rig's D-MS-05 size choice
  starts at 2B-class, and any 1B revisit needs sampling or training, not
  prompting.
- **Routing (which stores) is flat across 2B-8B (0.30-0.45); only
  verbosity-linked recall rises with size.** A size choice on accuracy
  alone is not supported pre-fine-tune; cost (4 -> 633 tok/para,
  0.1 -> 25 s/para) is the differentiator today. Recall/F1 are strict
  lower bounds (alias brittleness: "Ed Wood" vs "Edward Davis Wood Jr.",
  "October 10, 1924" vs "1924-10-10") -- a trained normaliser would move
  all arms together.
- **Quote evidence works but is lossy:** 30-50% of student ops die in
  Proof, almost all on evidence (quote missing subject/value) or date
  formats. Fine-tuning targets: quote-must-contain-subject discipline
  and ISO dates.
- **Grammar needs the token cap as terminator** (minicpm2b's 66x loop);
  keep I4 caps in every decode step of the runtime (spike 002/005).
- **Spec v0.2 deviation** (quote replaces offsets; `ops.v0.2.schema.json`
  + `v02_grammar.py` local to this folder): offsets failed for frontier
  and small models alike. Owner review pending on whether v0.2 replaces
  §5 or stays a spike-local deviation.

# Parity Evidence

Rendered from the committed result files under `databasise/evidence/parity_results/` by `databasise/evidence/parity_report.py`, following `FALSIFIER-2-EVIDENCE.md`'s committed, re-runnable, human-readable precedent.

## What was compared

- **Corpus**: `databasise/tests/fixtures/corpus/` — 20 documents, 2 queries (HotpotQA distractor setting, D-06). Corpus hash and per-arm query set are recorded per-arm below from each committed comparison result's own `corpus_hash` field.

- **One index**: built exactly once by a real v1 OpenRouter ingest run over the pinned corpus (plan 03-02, `v1/scripts/run_parity_ingest.py`), imported into the v2 namespace layout by a verified read-and-reinsert import (`databasise/parity/import_index.py`), and gated on every comparison run by plan 03-02's index-identity verifier (`databasise.parity.import_index.verify_import`) — the same precondition this run passed.

- **Determinism / concurrency**: `cache-bypassed` / `sequential` (`databasise.parity.run_arm`'s own pinned settings).

- **Rerank**: disabled (`RERANK_BINDING=null`, D-09's unchanged half; `v1/README-PARITY.md`). A number recorded with rerank off does not transfer to a run with it on — this evidence never claims otherwise.

- **Pinned model identities**: `qwen/qwen3.7-flash` (generator + keyword extraction, provider-pinned to Alibaba, D-07/D-08) and `qwen/qwen3-embedding-8b` (embedder, amended D-09) — see `v1/README-PARITY.md`. The completed run resolved these identities live from each provider's response, never the requested id (Phase 1 D-12) — recorded per-comparison in each committed record's own `resolved_model_identities` field: `decomposed_generate='qwen/qwen3.7-flash'`, `original_arm_llm_model='qwen/qwen3.7-flash'`, `original_arm_embedding_model='qwen/qwen3-embedding-8b'` (`bypass`, `global`, `hybrid`, `local`, `naive`, the arm(s) whose `generate` node ran). Every arm's `generate` node ran and recorded a resolved identity — none halted before reaching it.

- **Run state (this render)**: all five arms' comparison runs and storage audits completed, against corpus hash `ac55d19ec162cc9abf51ddf8502436109b1439c5cbaea4cf41c448c11575d5bd`. `v1/.venv`, `v1/.parity_working_dir`, `v1/.parity_v2_store`, and `v1/.env.parity` were all present for this run — this is a completed comparison, not D-02's failed-precondition refusal (`inconclusive`) path. That refusal path is proven separately, against a monkeypatched fixture, in `tests/parity/test_parity_evidence.py`, so it stays covered even though the real committed data no longer exercises it.

## The trace asymmetry

Stated before the numbers, not after them. The decomposed arm's run comes back as a full RIG §TR.1 run record (`databasise.runner.trace.RunRecord`) — one entry per node, its own token accounting, its own effects. The original (pre-decomposition) arm comes back as `databasise.parity.v1_arm.V1ArmResult`, instrumented from the outside only (wall clock, exit status, captured stderr) — its `instrumentation` field is always `"harness-external"`. This is not a defect to fix; v1 was never built to emit a RIG §TR.1 record and never will be. Wherever a number below appears next to the original arm, it is read against this asymmetry, not against a claim of matching instrumentation (D-05, `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md`).

## Per-arm retrieval-level comparison

### `naive`

| query_id | status | chunk sym_diff | ranking agreement | first disagreement | entity sym_diff | relation sym_diff | reason |
|---|---|---|---|---|---|---|---|
| q1 | completed | 2 | 1.000 | 10 | — | — |  |
| q2 | completed | 4 | 1.000 | 10 | — | — |  |

`naive` resolves to `embedder-index`/`embedder-query`/`chunk-vector`/`heading-backfill`/`rerank`/`assemble`/`generate` — no entity or relation lookup node at all. Its entity/relation columns above read `"—"` because the arm's wiring has no entity/relation lookup to measure, not because a measurement was skipped.

### `bypass`

| query_id | status | chunk sym_diff | ranking agreement | first disagreement | entity sym_diff | relation sym_diff | reason |
|---|---|---|---|---|---|---|---|
| q1 | completed | no retrieval to compare | no retrieval to compare | no retrieval to compare | — | — |  |
| q2 | completed | no retrieval to compare | no retrieval to compare | no retrieval to compare | — | — |  |

`bypass` resolves to a single `generate` node with no retrieval at all (`databasise.wirings.resolve.resolve_arm("bypass")` has no chunk-source node). Its chunk/entity/relation columns above read `"no retrieval to compare"` once a run completes, distinct from a computed zero symmetric difference — see `databasise/parity/run_comparison.py`'s own `_no_retrieval_to_compare_note`.

### `hybrid`

| query_id | status | chunk sym_diff | ranking agreement | first disagreement | entity sym_diff | relation sym_diff | reason |
|---|---|---|---|---|---|---|---|
| q1 | completed | 2 | 0.628 | 0 | 58 | 60 |  |
| q2 | completed | 5 | 0.731 | 0 | 46 | 44 |  |

### `local`

| query_id | status | chunk sym_diff | ranking agreement | first disagreement | entity sym_diff | relation sym_diff | reason |
|---|---|---|---|---|---|---|---|
| q1 | completed | 4 | 0.500 | 0 | 20 | 33 |  |
| q2 | completed | 4 | 0.673 | 0 | 22 | 30 |  |

### `global`

| query_id | status | chunk sym_diff | ranking agreement | first disagreement | entity sym_diff | relation sym_diff | reason |
|---|---|---|---|---|---|---|---|
| q1 | completed | 8 | 0.533 | 1 | 76 | 78 |  |
| q2 | completed | 8 | 0.857 | 0 | 68 | 68 |  |

## Human spot-check of answer substance

Criterion 6's substitute-gate half this document's retrieval-level comparison does not cover: an LLM-generated answer's *substance* is not mechanically checkable — `generate` is stochastic and no A/A floor is calibrated yet (MACH-02/MACH-03 deferred to Phase 6, `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md`) — so only a human judgment call substitutes for it. Recorded per query in `human_findings.json`'s `answer_spotchecks` list; run instructions are `.planning/phases/03-lightrag-query-side/03-VALIDATION.md`'s Manual-Only Verifications row for this behavior.

Each completed comparison record already carries the original (v1) arm's answer text under `original_arm_result.answer` (see the raw `parity_results/` files); the decomposed arm's answer text is not recorded in the run record, so the side-by-side read this section names is a live re-run, not a document comparison.

All five arms completed without a decomposed-run degradation, so this read is available against any of them.

### `q1`

**Not yet recorded.** A human is required — answer substance is not mechanically checkable and no A/A floor is calibrated (MACH-02/MACH-03 deferred to Phase 6). To record it, add an entry to `human_findings.json`'s `answer_spotchecks` list naming `query_id='q1'`, the `arm` compared, a `judgment` (one of the three values this module's own `InvalidJudgmentError` enforces), `notes`, `recorded_by`, and `recorded_at`. Run instructions: `.planning/phases/03-lightrag-query-side/03-VALIDATION.md`'s Manual-Only Verifications table, "Human spot-check of answer substance" row.

### `q2`

**Not yet recorded.** A human is required — answer substance is not mechanically checkable and no A/A floor is calibrated (MACH-02/MACH-03 deferred to Phase 6). To record it, add an entry to `human_findings.json`'s `answer_spotchecks` list naming `query_id='q2'`, the `arm` compared, a `judgment` (one of the three values this module's own `InvalidJudgmentError` enforces), `notes`, `recorded_by`, and `recorded_at`. Run instructions: `.planning/phases/03-lightrag-query-side/03-VALIDATION.md`'s Manual-Only Verifications table, "Human spot-check of answer substance" row.

## The `keywords` variance band

**N = 5 runs** (`databasise.parity.run_comparison._DEFAULT_KEYWORD_VARIANCE_RUNS`). Chosen (reasoning recorded in full in 03-09-SUMMARY.md's Decisions Made section): large enough to show repeats in the per-keyword frequency table for a typical HotpotQA question (2-4 keywords per level), small enough that 5 extra live `keywords` calls per query stays well within a rung-2 comparison's affordability, and `compute_keyword_variance_band` itself accepts any N ≥ 2 — raising N on a future real run needs no code change, only a different `keyword_variance_runs=` argument.

| arm | query_id | run count (N) | hl size mean | hl size stdev | ll size mean | ll size stdev | any cache served |
|---|---|---|---|---|---|---|---|
| naive | q1 | not applicable — naive's wiring has no `keywords` node | — | — | — | — | — |
| naive | q2 | not applicable — naive's wiring has no `keywords` node | — | — | — | — | — |
| bypass | q1 | not applicable — bypass's wiring has no `keywords` node | — | — | — | — | — |
| bypass | q2 | not applicable — bypass's wiring has no `keywords` node | — | — | — | — | — |
| hybrid | q1 | 5 | 2.00 | 0.00 | 2.00 | 0.00 | True |
| hybrid | q2 | 5 | 2.80 | 0.45 | 2.00 | 0.00 | True |
| local | q1 | 5 | 2.20 | 0.45 | 2.00 | 0.00 | True |
| local | q2 | 5 | 2.60 | 0.55 | 2.20 | 0.45 | True |
| global | q1 | 5 | 2.20 | 0.45 | 2.00 | 0.00 | True |
| global | q2 | 5 | 2.40 | 0.55 | 2.20 | 0.45 | True |

## The per-node storage-ownership audit

Criterion 3 requires this to ship as part of the parity evidence, which is why it is a section here and not a separate file. `matched`/`no-touch`/`over-declared` are `databasise.parity.storage_audit`'s own three legitimate per-node states — never a pass/fail bit — counted separately below, per arm.

| arm | matched | no-touch | over-declared | outcome |
|---|---|---|---|---|
| naive | 5 | 2 | 0 | completed |
| bypass | 1 | 0 | 0 | completed |
| hybrid | 14 | 2 | 1 | completed |
| local | 12 | 2 | 1 | completed |
| global | 12 | 2 | 1 | completed |

`naive`, `bypass`, `hybrid`, `local`, `global` ran to completion clean — the comparison run reports no `decomposed_run_record.degraded=true` for these arms, so every dispatched node had the chance to touch what it declared: `naive`: matched=5 no-touch=2 over-declared=0; `bypass`: matched=1 no-touch=0 over-declared=0; `hybrid`: matched=14 no-touch=2 over-declared=1; `local`: matched=12 no-touch=2 over-declared=1; `global`: matched=12 no-touch=2 over-declared=1. `matched`/`no-touch`/`over-declared` remain three distinct states throughout, and an `over-declared` count of `0` on these arms is a real measured zero, not an assumed one (D-15).

## What is not measured

The A/A floor (MACH-02's eval bundle, MACH-03's bootstrap-resampled p95 calibration) is deferred to Phase 6's side-by-side run, per `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md` — this is the **second** deferral of the same pair of requirements (first Phase 2 to Phase 3, recorded in `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md`; now Phase 3 to Phase 6). Residual risk, in D-11's own words, not softened: **answer-level drift originating in `keywords` and `generate` stays unmeasured until a floor exists.** GATE-01's standing condition continues to hold regardless of this document's own findings: no promotion decision and no parity claim rides on an unmeasured comparison.

Separately, and specific to this render: the retrieval-level comparison **has** run — all five arms are `completed` (see "What was compared" and "Per-arm retrieval-level comparison") — but the human answer-substance spot-check for q1/q2 has not yet been recorded (see "Human spot-check of answer substance" above), and `hybrid`/`local`/`global` completed without a decomposed-run degradation, so their measured retrieval-level agreement is not an artifact of a halted run. Neither gap is measured by this document; both are named here rather than left implicit.

## Verdict

**All five arms completed.** `naive` and `bypass` ran their full pipelines end to end and their retrieval-level comparisons are informative: `bypass` has no retrieval to compare; `naive` measured exact chunk-set agreement past `ranking_agreement=1.000` with two named tail-length excursions per query, both carried as declared deviations in `DECLARED-DEVIATIONS.md` with a grounded cause (top_k cutoff vs v1's token-budget truncation) rather than folded into a silent pass.

`hybrid` completed with no decomposed-run degradation, but **this is not read as exact retrieval-level agreement either.** Both sides retrieved real, non-trivial content, and the two disagree: `q1`: chunk_diff=2, entity_diff=58, relation_diff=60; `q2`: chunk_diff=5, entity_diff=46, relation_diff=44. A completed run with a real disagreement is a genuine excursion, not a crash and not a match — each one needs a CONTRACT §5 human-authored cause before it can be read as accepted, and none is recorded yet for this arm; see `DECLARED-DEVIATIONS.md`'s "Outstanding" section and `.planning/phases/03-lightrag-query-side/03-UAT.md` for the exact owner action.

`local` completed with no decomposed-run degradation, but **this is not read as exact retrieval-level agreement either.** Both sides retrieved real, non-trivial content, and the two disagree: `q1`: chunk_diff=4, entity_diff=20, relation_diff=33; `q2`: chunk_diff=4, entity_diff=22, relation_diff=30. A completed run with a real disagreement is a genuine excursion, not a crash and not a match — each one needs a CONTRACT §5 human-authored cause before it can be read as accepted, and none is recorded yet for this arm; see `DECLARED-DEVIATIONS.md`'s "Outstanding" section and `.planning/phases/03-lightrag-query-side/03-UAT.md` for the exact owner action.

`global` completed with no decomposed-run degradation, but **this is not read as exact retrieval-level agreement either.** Both sides retrieved real, non-trivial content, and the two disagree: `q1`: chunk_diff=8, entity_diff=76, relation_diff=78; `q2`: chunk_diff=8, entity_diff=68, relation_diff=68. A completed run with a real disagreement is a genuine excursion, not a crash and not a match — each one needs a CONTRACT §5 human-authored cause before it can be read as accepted, and none is recorded yet for this arm; see `DECLARED-DEVIATIONS.md`'s "Outstanding" section and `.planning/phases/03-lightrag-query-side/03-UAT.md` for the exact owner action.

**What this verdict does not cover.** D-10's gate is the deterministic retrieval level only — this document makes no answer-level parity claim. The human answer-substance spot-check for q1/q2 is not yet recorded (see "Human spot-check of answer substance" above). GATE-01's standing condition continues to hold: no promotion decision and no parity claim rides on an unmeasured comparison.

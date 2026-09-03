# Parity Evidence

Rendered from the committed result files under `databasise/evidence/parity_results/` by `databasise/evidence/parity_report.py`, following `FALSIFIER-2-EVIDENCE.md`'s committed, re-runnable, human-readable precedent.

## What was compared

- **Corpus**: `databasise/tests/fixtures/corpus/` — 20 documents, 2 queries (HotpotQA distractor setting, D-06). Corpus hash and per-arm query set are recorded per-arm below from each committed comparison result's own `corpus_hash` field.

- **One index**: built exactly once by a real v1 OpenRouter ingest run over the pinned corpus (plan 03-02, `v1/scripts/run_parity_ingest.py`), imported into the v2 namespace layout by a verified read-and-reinsert import (`databasise/parity/import_index.py`), and gated on every comparison run by plan 03-02's index-identity verifier (`databasise.parity.import_index.verify_import`) — the same precondition this run passed.

- **Determinism / concurrency**: `cache-bypassed` / `sequential` (`databasise.parity.run_arm`'s own pinned settings).

- **Rerank**: disabled (`RERANK_BINDING=null`, D-09's unchanged half; `v1/README-PARITY.md`). A number recorded with rerank off does not transfer to a run with it on — this evidence never claims otherwise.

- **Pinned model identities**: `qwen/qwen3.7-flash` (generator + keyword extraction, provider-pinned to Alibaba, D-07/D-08) and `qwen/qwen3-embedding-8b` (embedder, amended D-09) — see `v1/README-PARITY.md`. The completed run resolved these identities live from each provider's response, never the requested id (Phase 1 D-12) — recorded per-comparison in each committed record's own `resolved_model_identities` field: `decomposed_generate='qwen/qwen3.7-flash'`, `original_arm_llm_model='qwen/qwen3.7-flash'`, `original_arm_embedding_model='qwen/qwen3-embedding-8b'` (naive/bypass, the two arms whose `generate` node ran). `hybrid`/`local`/`global` recorded `decomposed_generate=""` because their `generate` node never ran — see the per-arm degradation note in "Per-arm retrieval-level comparison" below.

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
| q1 | completed | 0 | 1.000 | None | 0 | 0 |  |
| q2 | completed | 0 | 1.000 | None | 0 | 0 |  |

**Degraded run — read the zero diffs above with this in mind.** `hybrid`'s decomposed run halted before completing retrieval on q1, q2 (MACH-09's `degraded`/`degradation_reason` labelling, RIG §TR): node 'entity-hydrate-expand': NodeExecutionError: 'entity_name'. The original arm's own answer for the same query/arm pairs also carries zero chunk/entity/relation ids (`original_arm_result` — see the raw `parity_results/` record). The `0` symmetric_difference reported above is therefore both sides retrieving nothing, not a validated matched retrieval — a live defect this comparison surfaced, out of this plan's scope to repair. See the Verdict section for how this bounds what the comparison actually shows.

### `local`

| query_id | status | chunk sym_diff | ranking agreement | first disagreement | entity sym_diff | relation sym_diff | reason |
|---|---|---|---|---|---|---|---|
| q1 | completed | 0 | 1.000 | None | 0 | 0 |  |
| q2 | completed | 0 | 1.000 | None | 0 | 0 |  |

**Degraded run — read the zero diffs above with this in mind.** `local`'s decomposed run halted before completing retrieval on q1, q2 (MACH-09's `degraded`/`degradation_reason` labelling, RIG §TR): node 'entity-hydrate-expand': NodeExecutionError: 'entity_name'. The original arm's own answer for the same query/arm pairs also carries zero chunk/entity/relation ids (`original_arm_result` — see the raw `parity_results/` record). The `0` symmetric_difference reported above is therefore both sides retrieving nothing, not a validated matched retrieval — a live defect this comparison surfaced, out of this plan's scope to repair. See the Verdict section for how this bounds what the comparison actually shows.

### `global`

| query_id | status | chunk sym_diff | ranking agreement | first disagreement | entity sym_diff | relation sym_diff | reason |
|---|---|---|---|---|---|---|---|
| q1 | completed | 0 | 1.000 | None | 0 | 0 |  |
| q2 | completed | 0 | 1.000 | None | 0 | 0 |  |

**Degraded run — read the zero diffs above with this in mind.** `global`'s decomposed run halted before completing retrieval on q1, q2 (MACH-09's `degraded`/`degradation_reason` labelling, RIG §TR): node 'relation-hydrate-expand': NodeExecutionError: 'src_id'. The original arm's own answer for the same query/arm pairs also carries zero chunk/entity/relation ids (`original_arm_result` — see the raw `parity_results/` record). The `0` symmetric_difference reported above is therefore both sides retrieving nothing, not a validated matched retrieval — a live defect this comparison surfaced, out of this plan's scope to repair. See the Verdict section for how this bounds what the comparison actually shows.

## Human spot-check of answer substance

Criterion 6's substitute-gate half this document's retrieval-level comparison does not cover: an LLM-generated answer's *substance* is not mechanically checkable — `generate` is stochastic and no A/A floor is calibrated yet (MACH-02/MACH-03 deferred to Phase 6, `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md`) — so only a human judgment call substitutes for it. Recorded per query in `human_findings.json`'s `answer_spotchecks` list; run instructions are `.planning/phases/03-lightrag-query-side/03-VALIDATION.md`'s Manual-Only Verifications row for this behavior.

Each completed comparison record already carries the original (v1) arm's answer text under `original_arm_result.answer` (see the raw `parity_results/` files); the decomposed arm's answer text is not recorded in the run record, so the side-by-side read this section names is a live re-run, not a document comparison.

`hybrid`, `local`, `global` cannot host this read today: each one's decomposed run degrades before reaching `generate` (see the per-arm degradation notes above), so there is no decomposed-side answer to compare — v1's own answer for those query/arm pairs is also `"…[no-context]"` (see `original_arm_result.answer` in the raw `parity_results/` files). Run this spot-check against `naive` instead, whose pipeline completed end to end on both sides; the graph arms become available for this read once their crash is repaired (out of this plan's scope).

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
| hybrid | q1 | 5 | 2.00 | 0.00 | 2.20 | 0.45 | False |
| hybrid | q2 | 5 | 3.00 | 0.71 | 2.20 | 0.45 | False |
| local | q1 | 5 | 2.00 | 0.00 | 2.00 | 0.00 | False |
| local | q2 | 5 | 3.00 | 0.71 | 2.00 | 0.00 | False |
| global | q1 | 5 | 1.80 | 0.45 | 2.00 | 0.00 | False |
| global | q2 | 5 | 3.00 | 0.71 | 2.00 | 0.00 | False |

## The per-node storage-ownership audit

Criterion 3 requires this to ship as part of the parity evidence, which is why it is a section here and not a separate file. `matched`/`no-touch`/`over-declared` are `databasise.parity.storage_audit`'s own three legitimate per-node states — never a pass/fail bit — counted separately below, per arm.

| arm | matched | no-touch | over-declared | outcome |
|---|---|---|---|---|
| naive | 5 | 2 | 0 | completed |
| bypass | 1 | 0 | 0 | completed |
| hybrid | 12 | 5 | 0 | completed |
| local | 10 | 5 | 0 | completed |
| global | 10 | 5 | 0 | completed |

`naive`, `bypass` ran to completion clean — the comparison run reports no `decomposed_run_record.degraded=true` for these arms, so every dispatched node had the chance to touch what it declared: `naive`: matched=5 no-touch=2 over-declared=0; `bypass`: matched=1 no-touch=0 over-declared=0. `matched`/`no-touch`/`over-declared` remain three distinct states throughout, and an `over-declared` count of `0` on these arms is a real measured zero, not an assumed one (D-15).

**`hybrid`'s audit is crash-truncated, not clean.** The comparison run's own `decomposed_run_record` reports `degraded=true` (node 'entity-hydrate-expand': NodeExecutionError: 'entity_name'), and `databasise/runner/scheduler.py` halts the whole scheduling loop on that `NodeExecutionError` without dispatching any node downstream of it — a node that never executed is a fundamentally different state from a node that ran and legitimately touched nothing. Cross-referencing this audit's own rows against the node ids the comparison run's `decomposed_run_record` actually dispatched: `assemble`, `budget-entities`, `budget-relations`, `chunk-sel-kg`, `generate`, `heading-backfill`, `join-chunks`, `join-entities`, `join-relations`, `rerank` never executed in the run this audit reflects. Some report `no-touch` above (a node that never touched its own declared handle); some report `matched` vacuously (a node with no declared effect at all — a join or budget node — counted `matched` regardless of whether it was ever dispatched, per `storage_audit.py`'s own no-declared-effects rule). A node that never ran cannot be shown not to have over-declared — `hybrid`'s audit counts (matched=12 no-touch=5 over-declared=0) are coverage of a halted run, not proof every node touches only what it declares.

**`local`'s audit is crash-truncated, not clean.** The comparison run's own `decomposed_run_record` reports `degraded=true` (node 'entity-hydrate-expand': NodeExecutionError: 'entity_name'), and `databasise/runner/scheduler.py` halts the whole scheduling loop on that `NodeExecutionError` without dispatching any node downstream of it — a node that never executed is a fundamentally different state from a node that ran and legitimately touched nothing. Cross-referencing this audit's own rows against the node ids the comparison run's `decomposed_run_record` actually dispatched: `assemble`, `budget-entities`, `budget-relations`, `chunk-sel-kg`, `generate`, `heading-backfill`, `join-chunks`, `join-entities`, `join-relations`, `rerank` never executed in the run this audit reflects. Some report `no-touch` above (a node that never touched its own declared handle); some report `matched` vacuously (a node with no declared effect at all — a join or budget node — counted `matched` regardless of whether it was ever dispatched, per `storage_audit.py`'s own no-declared-effects rule). A node that never ran cannot be shown not to have over-declared — `local`'s audit counts (matched=10 no-touch=5 over-declared=0) are coverage of a halted run, not proof every node touches only what it declares.

**`global`'s audit is crash-truncated, not clean.** The comparison run's own `decomposed_run_record` reports `degraded=true` (node 'relation-hydrate-expand': NodeExecutionError: 'src_id'), and `databasise/runner/scheduler.py` halts the whole scheduling loop on that `NodeExecutionError` without dispatching any node downstream of it — a node that never executed is a fundamentally different state from a node that ran and legitimately touched nothing. Cross-referencing this audit's own rows against the node ids the comparison run's `decomposed_run_record` actually dispatched: `assemble`, `budget-entities`, `budget-relations`, `chunk-sel-kg`, `generate`, `heading-backfill`, `join-chunks`, `join-entities`, `join-relations`, `rerank` never executed in the run this audit reflects. Some report `no-touch` above (a node that never touched its own declared handle); some report `matched` vacuously (a node with no declared effect at all — a join or budget node — counted `matched` regardless of whether it was ever dispatched, per `storage_audit.py`'s own no-declared-effects rule). A node that never ran cannot be shown not to have over-declared — `global`'s audit counts (matched=10 no-touch=5 over-declared=0) are coverage of a halted run, not proof every node touches only what it declares.

## What is not measured

The A/A floor (MACH-02's eval bundle, MACH-03's bootstrap-resampled p95 calibration) is deferred to Phase 6's side-by-side run, per `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md` — this is the **second** deferral of the same pair of requirements (first Phase 2 to Phase 3, recorded in `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md`; now Phase 3 to Phase 6). Residual risk, in D-11's own words, not softened: **answer-level drift originating in `keywords` and `generate` stays unmeasured until a floor exists.** GATE-01's standing condition continues to hold regardless of this document's own findings: no promotion decision and no parity claim rides on an unmeasured comparison.

Separately, and specific to this render: the retrieval-level comparison **has** run — all five arms are `completed` (see "What was compared" and "Per-arm retrieval-level comparison") — but the human answer-substance spot-check for q1/q2 has not yet been recorded (see "Human spot-check of answer substance" above), and `hybrid`/`local`/`global`'s decomposed runs degraded before completing a real retrieval (see the per-arm degradation notes above), so their measured zero diffs are not a validated agreement over non-trivial content. Neither gap is measured by this document; both are named here rather than left implicit.

## Verdict

**All five arms completed.** `naive` and `bypass` ran their full pipelines end to end and their retrieval-level comparisons are informative: `bypass` has no retrieval to compare; `naive` measured exact chunk-set agreement past `ranking_agreement=1.000` with two named tail-length excursions per query, both carried as declared deviations in `DECLARED-DEVIATIONS.md` with a grounded cause (top_k cutoff vs v1's token-budget truncation) rather than folded into a silent pass.

`hybrid` also completed and measured `chunk_diff`/`entity_diff`/`relation_diff` `symmetric_difference=[]` on both corpus queries — but **this is not read as exact retrieval-level agreement.** `hybrid`'s decomposed run degraded before completing a real retrieval (node 'entity-hydrate-expand': NodeExecutionError: 'entity_name' — see the per-arm degradation note in "Per-arm retrieval-level comparison"), and the original (v1) arm's own answer for the same query/arm pairs also carries zero chunk/entity/relation ids. The measured zero is both sides retrieving nothing, not a validated match over non-trivial content — a live defect this comparison surfaced, not evidence of parity. Fixing that defect is out of this plan's scope; recorded here so the verdict does not overstate what this arm actually showed.

`local` also completed and measured `chunk_diff`/`entity_diff`/`relation_diff` `symmetric_difference=[]` on both corpus queries — but **this is not read as exact retrieval-level agreement.** `local`'s decomposed run degraded before completing a real retrieval (node 'entity-hydrate-expand': NodeExecutionError: 'entity_name' — see the per-arm degradation note in "Per-arm retrieval-level comparison"), and the original (v1) arm's own answer for the same query/arm pairs also carries zero chunk/entity/relation ids. The measured zero is both sides retrieving nothing, not a validated match over non-trivial content — a live defect this comparison surfaced, not evidence of parity. Fixing that defect is out of this plan's scope; recorded here so the verdict does not overstate what this arm actually showed.

`global` also completed and measured `chunk_diff`/`entity_diff`/`relation_diff` `symmetric_difference=[]` on both corpus queries — but **this is not read as exact retrieval-level agreement.** `global`'s decomposed run degraded before completing a real retrieval (node 'relation-hydrate-expand': NodeExecutionError: 'src_id' — see the per-arm degradation note in "Per-arm retrieval-level comparison"), and the original (v1) arm's own answer for the same query/arm pairs also carries zero chunk/entity/relation ids. The measured zero is both sides retrieving nothing, not a validated match over non-trivial content — a live defect this comparison surfaced, not evidence of parity. Fixing that defect is out of this plan's scope; recorded here so the verdict does not overstate what this arm actually showed.

**What this verdict does not cover.** D-10's gate is the deterministic retrieval level only — this document makes no answer-level parity claim. The human answer-substance spot-check for q1/q2 is not yet recorded (see "Human spot-check of answer substance" above). GATE-01's standing condition continues to hold: no promotion decision and no parity claim rides on an unmeasured comparison, and the hybrid/local/global degradation above means the retrieval-level comparison itself is not yet clean for those arms either.

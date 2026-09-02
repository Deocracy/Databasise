# Parity Evidence

Rendered from the committed result files under `databasise/evidence/parity_results/` by `databasise/evidence/parity_report.py`, following `FALSIFIER-2-EVIDENCE.md`'s committed, re-runnable, human-readable precedent.

## What was compared

- **Corpus**: `databasise/tests/fixtures/corpus/` — 20 documents, 2 queries (HotpotQA distractor setting, D-06). Corpus hash and per-arm query set are recorded per-arm below from each committed comparison result's own `corpus_hash` field.

- **One index**: built exactly once by a real v1 OpenRouter ingest run over the pinned corpus (plan 03-02, `v1/scripts/run_parity_ingest.py`), imported into the v2 namespace layout by a verified read-and-reinsert import (`databasise/parity/import_index.py`), and gated on every comparison run by plan 03-02's index-identity verifier (`databasise.parity.import_index.verify_import`) — the same precondition this document's own recorded runs failed against (see below).

- **Determinism / concurrency**: `cache-bypassed` / `sequential` (`databasise.parity.run_arm`'s own pinned settings).

- **Rerank**: disabled (`RERANK_BINDING=null`, D-09's unchanged half; `v1/README-PARITY.md`). A number recorded with rerank off does not transfer to a run with it on — this evidence never claims otherwise.

- **Pinned model identities**: `qwen/qwen3.7-flash` (generator + keyword extraction, provider-pinned to Alibaba, D-07/D-08) and `qwen/qwen3-embedding-8b` (embedder, amended D-09) — see `v1/README-PARITY.md`. No comparison run recorded in this document reached the point of resolving these identities live (see "What is not measured" and the precondition state below); the pins themselves are config, not a claim about what ran.

- **Environment precondition state on this machine (this render)**: `v1/.venv`, `v1/.parity_working_dir`, `v1/.parity_v2_store`, and `v1/.env.parity` are all absent — gitignored, worktree-local build artifacts from a different execution session (03-02's own real ingest run) that do not carry over to a freshly spawned worktree. Every arm's comparison run below therefore stopped at the index-identity precondition gate before either arm was touched, and every arm's storage-audit run stopped at client construction before the scheduler ran a single node. Both are the harness's own designed refusal behavior (D-02, this document's own governing prohibition against emitting a pass/fail verdict on a failed precondition), not a code defect. Rebuild steps and the exact re-run commands are listed in 03-09-SUMMARY.md's "Next Phase Readiness" section.

## The trace asymmetry

Stated before the numbers, not after them. The decomposed arm's run comes back as a full RIG §TR.1 run record (`databasise.runner.trace.RunRecord`) — one entry per node, its own token accounting, its own effects. The original (pre-decomposition) arm comes back as `databasise.parity.v1_arm.V1ArmResult`, instrumented from the outside only (wall clock, exit status, captured stderr) — its `instrumentation` field is always `"harness-external"`. This is not a defect to fix; v1 was never built to emit a RIG §TR.1 record and never will be. Wherever a number below appears next to the original arm, it is read against this asymmetry, not against a claim of matching instrumentation (D-05, `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md`).

## Per-arm retrieval-level comparison

### `naive`

| query_id | status | chunk sym_diff | ranking agreement | first disagreement | entity sym_diff | relation sym_diff | reason |
|---|---|---|---|---|---|---|---|
| q1 | completed | 2 | 1.000 | 10 | — | — |  |
| q2 | completed | 4 | 1.000 | 10 | — | — |  |

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

### `local`

| query_id | status | chunk sym_diff | ranking agreement | first disagreement | entity sym_diff | relation sym_diff | reason |
|---|---|---|---|---|---|---|---|
| q1 | completed | 0 | 1.000 | None | 0 | 0 |  |
| q2 | completed | 0 | 1.000 | None | 0 | 0 |  |

### `global`

| query_id | status | chunk sym_diff | ranking agreement | first disagreement | entity sym_diff | relation sym_diff | reason |
|---|---|---|---|---|---|---|---|
| q1 | completed | 0 | 1.000 | None | 0 | 0 |  |
| q2 | completed | 0 | 1.000 | None | 0 | 0 |  |

## The `keywords` variance band

**N = 5 runs** (`databasise.parity.run_comparison._DEFAULT_KEYWORD_VARIANCE_RUNS`). Chosen (reasoning recorded in full in 03-09-SUMMARY.md's Decisions Made section): large enough to show repeats in the per-keyword frequency table for a typical HotpotQA question (2-4 keywords per level), small enough that 5 extra live `keywords` calls per query stays well within a rung-2 comparison's affordability, and `compute_keyword_variance_band` itself accepts any N ≥ 2 — raising N on a future real run needs no code change, only a different `keyword_variance_runs=` argument.

| arm | query_id | run count (N) | hl size mean | hl size stdev | ll size mean | ll size stdev | any cache served |
|---|---|---|---|---|---|---|---|
| naive | q1 | not run — completed | — | — | — | — | — |
| naive | q2 | not run — completed | — | — | — | — | — |
| bypass | q1 | not run — completed | — | — | — | — | — |
| bypass | q2 | not run — completed | — | — | — | — | — |
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

Every arm above reports `matched=0 no-touch=0 over-declared=0` in this render — none of the five audits reached the scheduler: `databasise.parity.storage_audit.run_audit` builds clients from `v1/.env.parity` before dispatching a single node, and that file is absent on this machine (see "What was compared"). This is the audit's own `MissingParityEnvError` refusal, captured verbatim in each arm's committed `{arm}-storage-audit.json` under `parity_results/` — not a claim that every node correctly touched nothing.

## What is not measured

The A/A floor (MACH-02's eval bundle, MACH-03's bootstrap-resampled p95 calibration) is deferred to Phase 6's side-by-side run, per `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md` — this is the **second** deferral of the same pair of requirements (first Phase 2 to Phase 3, recorded in `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md`; now Phase 3 to Phase 6). Residual risk, in D-11's own words, not softened: **answer-level drift originating in `keywords` and `generate` stays unmeasured until a floor exists.** GATE-01's standing condition continues to hold regardless of this document's own findings: no promotion decision and no parity claim rides on an unmeasured comparison.

Separately, and specific to this render: **no comparison in this document has actually run.** Every arm's retrieval-level diff, `keywords` variance band, and storage-ownership audit are all `inconclusive` on this machine (see "What was compared"). This document is correct and complete for that inconclusive outcome, and is re-runnable to produce the real verdict once the owner rebuilds the v1 environment — see 03-09-SUMMARY.md's "Next Phase Readiness" for the exact rebuild and re-run commands.

## Verdict

**No parity verdict is recorded by this document.** Every one of the five arms' comparison runs and storage-ownership audits reports an environment-precondition refusal — never a pass, never a fail, exactly as this document's own stated prohibition requires ("the parity harness must not emit a pass or fail verdict when the index-identity preconditions failed; it must emit `inconclusive`"). The harness code itself, its provenance-checking (`--check-results`), and this rendering are proven correct against the real refusal path in this session; the clean-pass path — an actual retrieval-level comparison against the real imported index and live model endpoints — awaits the owner rebuilding the v1 environment (`v1/README-PARITY.md`) and re-running the exact commands 03-09-SUMMARY.md names.

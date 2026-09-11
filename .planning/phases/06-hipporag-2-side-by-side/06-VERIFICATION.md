---
phase: 06-hipporag-2-side-by-side
verified: 2026-09-11T02:00:00Z
status: gaps_found
score: 5/6 must-haves verified
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/ROADMAP.md"
  - ".planning/WINDOWS.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-01-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-01-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-02-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-02-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-03-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-03-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-04-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-04-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-05-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-05-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-06-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-06-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-07-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-07-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-08-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-08-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-09-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-09-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-10-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-10-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-11-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-11-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-12-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-12-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-13-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-13-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-14-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-14-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-15-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-15-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-16-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-16-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-17-PLAN.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-17-SUMMARY.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-REVIEW-FIX.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-UAT.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-VALIDATION.md"
  - ".planning/phases/06-hipporag-2-side-by-side/06-VERIFICATION.md"
  - ".planning/phases/06-hipporag-2-side-by-side/COVERAGE.md"
  - "databasise/clients/openai_compat.py"
  - "databasise/eval/aa_run.py"
  - "databasise/eval/corpus_ingest.py"
  - "databasise/eval/remint.py"
  - "databasise/evidence/CROSS-MODALITY-EVIDENCE.md"
  - "databasise/evidence/FALSIFIER-5-EVIDENCE.md"
  - "databasise/mcp/server.py"
  - "databasise/mcp/tools.py"
  - "databasise/parity/build_hipporag_index.py"
  - "databasise/parts_core/hipporag/chunk_embed.py"
  - "databasise/seam/engine.py"
  - "databasise/seam/refusals.py"
  - "databasise/seam/rest.py"
  - "databasise/tests/clients/test_openai_compat.py"
  - "databasise/tests/eval/test_aa_run.py"
  - "databasise/tests/evidence/test_falsifier5_record.py"
  - "databasise/tests/parity/test_build_hipporag_index.py"
  - "databasise/wirings/hipporag/corpus-ingest.json"
  - "databasise/wirings/lightrag/corpus-ingest.json"
  - "databasise/wirings/resolve.py"
covered_digest: "v1:sha256:82f5481f05401e489f3998b432e5a5fc3cfa9824f46c00c1cb404f88ab2479a4"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/6
  gaps_closed:
    - "SC2 / MODAL-05 — 06-14 fixed the actual root cause (build_hipporag_index was resolving HippoRAG's 13-node base wiring, dispatching three query-side nodes including fact-score with no query at index time; it now resolves the 7-node corpus-ingest wiring via load_wiring(variant=...)), plus an independent client-boundary guard (EmptyEmbeddingInputError) refusing any empty/blank embedding batch item before it reaches the provider. 06-15's real, spend-incurring run then completed end to end: build_hipporag_index exited 0 (graph_node_count=229, graph_edge_count=460, chunk/entity/fact vector counts 20/209/226, partial=False, degraded=False) and run_cross_modality exited 0 (both corpus queries compared across both arms, directories_disjoint=True, artifacts_overlap=False, no arm partial/degraded). MODAL-05 flipped to Complete. Independently confirmed: code reads (resolve.py's variant kwarg, build_hipporag_index.py's _INDEX_WIRING_VARIANT, openai_compat.py's EmptyEmbeddingInputError guard), the CROSS-MODALITY-EVIDENCE.md '## Real run — 2026-09-10' section's harness-returned values, REQUIREMENTS.md's MODAL-05 row, and a live re-run of tests/parity/test_build_hipporag_index.py + tests/clients/test_openai_compat.py (31 passed)."
    - "The raw-bytes-upload data-loss defect this round's own code review found in the prior round's write path (06-REVIEW.md CR-01, 06-VERIFICATION.md's own prior-round Anti-Pattern row 1) — closed by 5827165/2cb437a: Databasise.ingest() now raises NoRawUploadPathForModalityError before any node config is stamped when a raw-bytes document targets a corpus wiring whose consuming node cannot parse file_paths/docs_format. Independently confirmed by reading engine.py:674 and refusals.py:149-171, and by re-running the named regression test (tests/seam/test_hipporag_write_path.py -k raw_upload_against_a_hipporag_selector_refuses, 1 passed)."
  gaps_remaining:
    - "SC6/MACH-03 (Falsifier 5) — both named preconditions were closed in code at 06-12, the fact-score defect that blocked the sibling run is fixed (06-14), and the A/A run driver that did not previously exist was built and tested (06-16, databasise/eval/aa_run.py, 13 passing tests). 06-17 pre-registered the 'materially narrower' threshold in FALSIFIER-5-EVIDENCE.md before any floor existed, then asked the owner once more with a real, driver-computed call-count projection. The owner declined a third time (06-06, 06-13, 06-17). No real A/A run has ever executed; no floor exists at either target family. This is not a falsified hypothesis — no comparison ran, so Falsifier 5 stays open, not failed — but the roadmap's own SC6 text requires a real p95 floor at both tiers with T1 materially narrower than T0, and that remains unmet."
  regressions: []
gaps:
  - truth: "Owner mints an eval bundle (MACH-02) then runs one A/A calibration reading a p95 floor at both target families with T1 materially narrower than T0 (MACH-03, Falsifier 5) — roadmap Success Criterion 6"
    status: failed
    reason: >
      MACH-02 remains fully satisfied and unchanged (bundle@v1, both §EV.2 families present).
      Everything automatable that stood between MACH-03 and a real run is now genuinely built and
      tested: 06-12 closed both named preconditions (a resolved judge-identity resolver, a
      cost-bounded eval-corpus ingest path); 06-14 fixed the fact-score empty-string defect at its
      actual root cause (a wiring-dispatch bug, not a missing input guard) and independently added a
      client-boundary refusal; 06-16 built the previously-nonexistent A/A run driver
      (databasise/eval/aa_run.py) — before this plan, calibrate_aa_floor had no caller anywhere in
      the repository outside its own tests, so an approval at 06-13 would have funded a run with no
      code able to perform it; 06-17 pre-registered the "materially narrower" threshold (T1's p95 <=
      0.5x T0's) in FALSIFIER-5-EVIDENCE.md, committed before any floor existed, closing the one
      remaining discipline gap named in the prior evidence document's own Limits section. I
      independently confirmed all of this by reading resolve.py, build_hipporag_index.py,
      openai_compat.py, aa_run.py, and by re-running the relevant test files (31 passed for 06-14's
      and 06-16's own suites; full suite 962 passed, 1 skipped, exit 0, matching the reported state
      exactly). None of this is in question. But the roadmap's own SC6 text is a claim about a real,
      completed measurement — "runs one A/A calibration and reads a bootstrap-resampled p95 floor" —
      and that measurement has never been taken. The owner was asked the identically-shaped question
      three times (06-06, 06-13, 06-17) and declined every time; the third decline came after every
      precondition, the driver, and the pre-registered threshold were genuinely in place, so it
      cannot be attributed to residual engineering risk the way the first two declines could. This is
      not a falsified hypothesis: no comparison ran, so there is no adverse verdict, and
      FALSIFIER-5-EVIDENCE.md and REQUIREMENTS.md both correctly record Falsifier 5 as open and
      MACH-03 as Pending rather than rounding a repeated decline up to a verdict in either direction.
      But the observable truth itself — a real p95 floor at both target families, with T1 materially
      narrower than T0 — does not exist anywhere in this codebase, and the roadmap's own Success
      Criterion 6 requires that it does.
    artifacts:
      - path: "databasise/evidence/FALSIFIER-5-EVIDENCE.md"
        issue: "States plainly, in its '## Deferred a third time — 2026-09-11' section, that the owner declined for a third time and that no floor exists for either tier. The pre-registered threshold section above it is real and correctly ordered before any floor in git history. This is an honest record of an unmet truth, not a gap in the record itself."
      - path: "databasise/eval/aa_run.py"
        issue: "Genuine, tested, runnable driver — score_gold_passage, score_answer_level, run_one_pass, calibrate_family, main — has never been invoked with --spend in this environment. Two Warning-severity defects (06-REVIEW.md WR-01/WR-02, this round, unfixed) would surface only on a real --spend invocation: a divide-by-zero on an empty gold-document list, and unhandled confounded-run/seam-refusal exceptions escaping main's except tuple as raw tracebacks instead of the module's own clean-refusal pattern. Neither defect has manifested, because the path has never run for real."
    missing:
      - "Owner authorization of the real A/A calibration spend — the only precondition this phase does not control, now that every code precondition, the driver, and the pre-registered threshold are in place"
      - "One real A/A run producing two CalibrationResult floors (gold_passage_recall, answer_level_correctness) read against the pre-registered threshold, discharging MACH-03/Falsifier 5 either way"
      - "A fix for aa_run.py's WR-01 (divide-by-zero on empty gold-document list) and WR-02 (unhandled exceptions on the --spend path) before that real run is attempted, so a first live invocation does not fail in an untested way"
---

# Phase 6: HippoRAG 2 & Side-by-Side Verification Report

**Phase Goal:** Two modalities answer the same corpus behind the same seam and the caller sees both at once — the milestone's proof of swappability (§BP rung 4)
**Verified:** 2026-09-11
**Status:** gaps_found
**Re-verification:** Yes — after gap-closure round 2 (plans 06-14 through 06-17)

## What changed since the prior verification round

The prior round (4/6, `gaps_found`) found two FAILED roadmap truths (SC2/MODAL-05, SC6/MACH-03),
one still-open Critical defect this round's own code review had found in the prior round's write
path (raw-bytes uploads silently losing content for HippoRAG), and a concrete named blocker
(`fact-score`'s empty-string provider 400) stopping both remaining gaps from closing. Four
gap-closure plans executed:

- **06-14** fixed the `fact-score` blocker at its actual root cause — `build_hipporag_index` was
  resolving HippoRAG's thirteen-position *base* wiring for an index build, dispatching three
  query-side node positions (including `fact-score`) with no query ever injected. It now resolves
  the seven-position `corpus-ingest` wiring instead, via a new `variant` keyword on `load_wiring`.
  Independently, a named client-boundary refusal (`EmptyEmbeddingInputError`) now guards every one
  of the seven call sites that reach the embedding provider. `.planning/WINDOWS.md` entry id 3
  closed as `fixed`.
- **06-15** re-asked the owner the same spend question once, now that the blocker was fixed. The
  owner approved. Both harnesses ran for real against live `v1/.env.parity` credentials and exited
  0. MODAL-05 flipped to Complete.
- **06-16** built `databasise/eval/aa_run.py` — a driver that genuinely did not exist anywhere in
  the repository before this plan. `calibrate_aa_floor` had no caller outside its own tests, and
  nothing produced the per-question score mappings it consumes; an approval at 06-13 would have
  funded a run with no code able to perform it. This plan is spend-free by its own design and
  performed no run.
- **06-17** pre-registered the "materially narrower" threshold in `FALSIFIER-5-EVIDENCE.md`,
  committed before any floor existed, then asked the owner once more for the A/A calibration spend,
  now with every precondition, the driver, and the threshold genuinely in place. The owner declined
  a third time. Separately, this plan appended a correction note to the prior round's
  `06-VERIFICATION.md` naming which later commits closed five of its findings — an append-only note
  that does not alter that report's own `status`/`score`/gap bodies, both of which I independently
  confirmed survived byte-for-byte.

Net effect: one truth (SC2/MODAL-05) moved from FAILED to VERIFIED — a real cross-modality run now
exists and is independently confirmed, not merely claimed. The other (SC6/MACH-03) remains FAILED,
for a materially different reason than before: every code precondition is now closed, and the
remaining gap is a repeated, informed owner decision not to spend, not a defect or missing
instrument. A code review of this round (`06-REVIEW.md`, commit `183139a`) found 2 Critical + 2
Warning findings, none fixed (advisory). I independently assessed each below; none of them
contradicts the roadmap truths this report scores.

## Goal Achievement

### Observable Truths (roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | HippoRAG 2 runs as thirteen fitted node positions, no opaque core left, whole-graph PPR via §14.2 bulk-export into native igraph/prpack, index-side depth stays `opaque` until parity shown | ✓ VERIFIED | Unchanged this round — no file in scope touched `base.json`'s node inventory. Independently re-ran `tests/parts_core/hipporag/test_thirteen_positions.py tests/stores/test_graph_bulk_export.py` directly: 12 passed. |
| 2 | LightRAG and HippoRAG 2 run on one corpus, isolated stores, outputs structurally comparable | ✓ VERIFIED | 06-15's real run completed against live credentials: `IndexBuildResult` returned `graph_node_count=229`, `graph_edge_count=460`, `chunk_vector_count=20`, `entity_vector_count=209`, `fact_vector_count=226`, `partial=False`, `degraded=False`; `CrossModalityRecord` returned `directories_disjoint=True`, `artifacts_overlap=False`, identical envelope field sets on both arms for both corpus queries, no arm `partial`/`degraded`. Independently confirmed against `CROSS-MODALITY-EVIDENCE.md`'s `## Real run — 2026-09-10` section and `.planning/REQUIREMENTS.md`'s MODAL-05 row (`Complete`). The prior round's own new raw-upload data-loss defect (06-REVIEW.md CR-01 that round) is independently confirmed fixed: `databasise/seam/engine.py:674` raises `NoRawUploadPathForModalityError`; `tests/seam/test_hipporag_write_path.py -k raw_upload_against_a_hipporag_selector_refuses` re-run directly, 1 passed. |
| 3 | Caller sends one query against two or more modalities, receives per-arm results keyed by caller-supplied selectors, no verdict, single arm degenerates to a run | ✓ VERIFIED | Unchanged this round — `Databasise.compare`, `POST /compare`, MCP `compare` tool untouched by 06-14..06-17's `files_modified` lists. Independently re-ran `tests/seam/test_compare.py tests/seam/test_rest_transport.py tests/mcp/test_dual_transport_parity.py tests/seam/test_mutable_store_exclusion.py tests/evidence/test_f07_record.py` directly: 55 passed. |
| 4 | The first genuine seam call records F-14's outcome either way | ✓ VERIFIED | Unchanged this round — `git log` confirms `databasise/evidence/F-14-SEAM-INVARIANCE.md`'s only commit predates this round entirely (06-03). |
| 5 | Mutable-store components have a defined snapshot/reset protocol or are recorded as permanently excluded — F-07 discharged | ✓ VERIFIED | Unchanged this round — MACH-10 stayed Complete, `F-07-MUTABLE-STORE-DISPOSITION.md`'s only commit predates this round (06-09). Regression-checked above (`test_mutable_store_exclusion.py`, `test_f07_record.py` both in the 55-passed re-run). |
| 6 | Owner mints an eval bundle (MACH-02) then runs one A/A calibration reading a p95 floor at both target families with T1 materially narrower than T0 (MACH-03, Falsifier 5) | ✗ FAILED | MACH-02 unchanged, satisfied. Every code precondition for MACH-03 is now closed — 06-12's judge-identity resolver and cost-bounded ingest, 06-14's fact-score root-cause fix, 06-16's previously-nonexistent A/A driver (`databasise/eval/aa_run.py`, 13 tests, independently re-run: 13/13 pass), and 06-17's threshold pre-registered before any floor exists (confirmed in `git log` order: `322d46f` precedes both of 06-17's own later commits, and no commit anywhere carries a floor value). The owner declined the real spend a third time (06-06, 06-13, 06-17). No real A/A run has ever executed; no floor exists at either tier. Falsifier 5 stays open, not failed — this is not a falsified hypothesis. But SC6's own text requires a real measurement, and none exists. See Gap 1. |

**Score:** 5/6 truths verified (0 present-but-behavior-unverified) — up from 4/6 last round.

### Anti-Patterns Found (this round's code review, independently assessed)

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `databasise/tests/evidence/test_falsifier5_record.py` | `floor_value_pattern` | The `<=`-exclusion added to catch the pre-registered threshold text also admits ANY `floor <= <number>` / `p95 <= <number>` phrasing, not just the specific pre-registered formula — a future SUMMARY could phrase a fabricated floor as a bound and this guard would not catch it (06-REVIEW.md CR-01, this round, unfixed) | 🛑 Blocker (latent) | Does **not** affect this round's SC6 verdict — I independently read `FALSIFIER-5-EVIDENCE.md` in full and confirmed no floor value of any kind appears anywhere in it, for either tier, under any of its four dated sections. The risk is forward-looking: this evidence-integrity guard is weaker than intended for whichever future plan actually runs the calibration. Should be tightened before that plan lands, not before this one is scored. |
| `databasise/seam/rest.py:260-285` | selector parse at line 284 | `POST /documents/upload` returns an unhandled 500, not the documented 422, on a malformed multipart `selector` JSON field — violates the module's own "never a raw 2xx-or-500, 422 uniformly for every refusal" contract (06-REVIEW.md CR-02, this round, unfixed) | ⚠️ Warning | Does not implicate any of the six roadmap truths directly — SC3/API-08's own tested truth is `compare()`'s per-arm keying and no-verdict behavior, not `/documents/upload`'s error-shape contract. It is a real gap in the seam's stated robustness contract and should be fixed as ordinary follow-up work, not a phase-blocking finding. |
| `databasise/eval/aa_run.py` | `score_gold_passage` | Divides by zero on an empty `gold_document_ids` list (06-REVIEW.md WR-01, this round, unfixed) | ⚠️ Warning | Only reachable on a real `--spend` invocation, which has never occurred — does not affect any truth scored above. Should be fixed before the real A/A run is next attempted (see Gap 1's `missing`). |
| `databasise/eval/aa_run.py` | `main`'s `--spend` path | Does not catch a partial/degraded run or a `SeamRefusalError`, producing a raw traceback instead of the module's own clean-refusal pattern (06-REVIEW.md WR-02, this round, unfixed) | ⚠️ Warning | Same as above — only reachable on a real `--spend` invocation, never taken. |
| `databasise/tests/eval/test_aa_run.py` | module-level `pytestmark` | Blanket `pytestmark = pytest.mark.asyncio` applied over sync test functions — 6 `PytestWarning`s on every full-suite run, no behavioral effect | ℹ️ Info | Cosmetic, pre-confirmed by this round's own review and by 06-17-SUMMARY.md's own "Known follow-up" note. Observed directly in this verification's own full-suite run. |

No `TBD`/`FIXME`/`XXX` markers found in any phase-modified file this round. Debt-marker gate clear.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/wirings/resolve.py` (`load_wiring` variant kwarg) | Index-side/query-side wiring lookup generalized to any `<wiring>/<variant>.json` | ✓ VERIFIED | Confirmed by direct read: `load_wiring(wiring_name, *, variant="base")` reads `_WIRINGS_ROOT / wiring_name / f"{variant}.json"`; default preserves every existing caller |
| `databasise/parity/build_hipporag_index.py` | Resolves the 7-node `corpus-ingest` wiring, not the 13-node base wiring | ✓ VERIFIED | `_INDEX_WIRING_VARIANT = "corpus-ingest"`; `load_wiring("hipporag", variant=_INDEX_WIRING_VARIANT)`; stamping target read from `resolved["consumes_documents"][0]`, confirmed by direct read |
| `databasise/clients/openai_compat.py` (`EmptyEmbeddingInputError`) | Named refusal at the one method all embedding call sites route through | ✓ VERIFIED | Class present at line 64; `embed()` guards before `embeddings.create`; `__all__` exports it; `tests/clients/test_openai_compat.py` (15 tests) re-run directly, all pass |
| `databasise/eval/aa_run.py` | Genuine, runnable A/A calibration driver, dry-run by default | ✓ VERIFIED | `score_gold_passage`, `score_answer_level`, `run_one_pass`, `calibrate_family`, `estimate_calls`, `main` all present (25KB module); `tests/eval/test_aa_run.py` (18 tests incl. Task 1's 7 + Task 2's 6 named in plan, actually 13 total per plan's own enumeration) re-run directly, all pass |
| `databasise/evidence/CROSS-MODALITY-EVIDENCE.md` | Append-only; two prior sections intact, new dated section carrying real harness-returned values | ✓ VERIFIED | `## Real run — 2026-09-10` section present below both prior sections, carrying only `IndexBuildResult`/`CrossModalityRecord` fields; no fabricated numbers found on direct read |
| `databasise/evidence/FALSIFIER-5-EVIDENCE.md` | Append-only; three prior sections intact, threshold pre-registered before any floor, new dated deferral section | ✓ VERIFIED | `## Pre-registered threshold — 2026-09-11` and `## Deferred a third time — 2026-09-11` both present below all prior sections; no floor value anywhere in the document, confirmed by direct full read |
| `.planning/REQUIREMENTS.md` (MODAL-05 row) | Flipped Complete with dated, cited annotation | ✓ VERIFIED | `- [x] **MODAL-05**` with `[Measured 2026-09-10 (06-15-PLAN.md): ...]` annotation appended after both prior annotations, all three intact; coverage table row `Complete` |
| `.planning/REQUIREMENTS.md` (MACH-03 row) | Stays Pending with a fourth dated annotation | ✓ VERIFIED | `- [ ] **MACH-03**` with `[Deferred 2026-09-11 (06-17-PLAN.md): ...]` annotation appended after all three prior annotations, all intact; coverage table row `Pending` |
| `.planning/WINDOWS.md` | Entry id 3 closed as fixed | ✓ VERIFIED | `open_count: 0`, entry id 3 `status: fixed`, `resolved_at` stamped, both markdown row and JSON block consistent |
| `.planning/phases/06-hipporag-2-side-by-side/06-VERIFICATION.md`'s own prior version | Append-only correction note, verdict/score untouched | ✓ VERIFIED (superseded by this report) | The prior report's correction note is preserved in git history; this report is the new authoritative verdict per this task's own instructions, not an amendment to the prior file |
| `databasise/parts_core/hipporag/fact_score.py` (implied working state) | No longer reachable with an empty query at index time | ✓ VERIFIED | Structurally: `test_build_hipporag_index.py`'s Test 2/3 (disjointness, root-cause pin) re-run directly, pass; `fact-score` is absent from the corpus-ingest wiring's 7 nodes |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `build_hipporag_index.build_index` (real invocation) | `databasise.parity.run_cross_modality` (real invocation) | index-build success gate | ✓ WIRED | Both harnesses exited 0 in sequence against live credentials (06-15); confirmed via `CROSS-MODALITY-EVIDENCE.md`'s harness-returned values and `.planning/REQUIREMENTS.md`'s MODAL-05 row |
| `Databasise.ingest(document, selector=<HippoRAG>)` (raw-bytes payload) | `NoRawUploadPathForModalityError` | `engine.py:674`, before any node config is stamped | ✓ WIRED (refuses by name) | Confirmed by direct read of `engine.py`/`refusals.py`; `tests/seam/test_hipporag_write_path.py -k raw_upload_against_a_hipporag_selector_refuses` re-run directly, 1 passed |
| every `ctx.clients["embedding"].embed(...)` call site | `OpenAICompatibleClient.embed` | `EmptyEmbeddingInputError` | ✓ WIRED (refuses by name) | Confirmed by direct read; `tests/clients/test_openai_compat.py` tests 11-15 re-run directly, pass |
| `databasise.eval.aa_run.calibrate_family` | `databasise.eval.calibration.calibrate_aa_floor` | direct call, no second path to a floor | ✓ WIRED (spend-free path proven; live path never invoked) | Confirmed by direct read: `calibrate_family` does not catch `UnusableFloorError`/`StaleNullError`; Test 9 (propagation on `cache_hit`-true) re-run directly, passes |
| `databasise.eval.aa_run.main --spend` | `databasise.eval.remint` → `databasise.eval.corpus_ingest --spend` → `databasise.eval.aa_run --spend` | 06-17's checkpoint | ✗ NOT REACHED | Owner declined; no command in this chain was ever invoked with a live credential this round |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `build_hipporag_index.IndexBuildResult` (real corpus) | node/edge/vector counts, token spend, duration | 06-15's real live invocation, `IndexBuildResult.to_dict()` | Yes | ✓ FLOWING — read directly from `CROSS-MODALITY-EVIDENCE.md`'s `## Real run — 2026-09-10` section |
| `run_cross_modality.CrossModalityRecord` (real corpus) | per-query, per-arm envelope structure | 06-15's real live invocation | Yes | ✓ FLOWING |
| `chunk_embed.py` (`raw=`-payload ingest, HippoRAG-resolving selector) | `text` | `engine.py` now refuses before any node config is stamped | N/A | ✓ CLOSED BY REFUSAL — the previously `HOLLOW_PROP` path is unreachable; the guard fires first |
| `aa_run.CalibrationResult.floor` (both target families) | `floor`, `NullIdentity` fields | never constructed — owner declined the spend that would invoke `calibrate_family` for real | N/A | ✗ DISCONNECTED — no comparable output exists for either target family; this is Gap 1's own subject, not a new finding |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| SC1 regression: thirteen positions, native graph bulk-export | `pytest tests/parts_core/hipporag/test_thirteen_positions.py tests/stores/test_graph_bulk_export.py` | 12 passed | ✓ PASS |
| SC2 regression: raw-upload-against-HippoRAG refusal | `pytest tests/seam/test_hipporag_write_path.py -k raw_upload_against_a_hipporag_selector_refuses -x` | 1 passed | ✓ PASS |
| SC2/06-14/06-16 targeted: wiring-swap, empty-embedding guard, A/A driver | `pytest tests/parity/test_build_hipporag_index.py tests/clients/test_openai_compat.py tests/eval/test_aa_run.py -x` | 31 passed (6 cosmetic asyncio-mark warnings, IN-01) | ✓ PASS |
| SC3/SC5 regression: compare, REST/MCP transport parity, mutable-store exclusion, F-07 record | `pytest tests/seam/test_compare.py tests/seam/test_rest_transport.py tests/mcp/test_dual_transport_parity.py tests/seam/test_mutable_store_exclusion.py tests/evidence/test_f07_record.py -x` | 55 passed | ✓ PASS |
| Full workspace suite (independently re-run by this verifier in full, once) | `cd databasise && uv run pytest -q` | 962 passed, 1 skipped, exit 0, 165.38s | ✓ PASS — matches the reported suite state exactly |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` harness; verification relied on the
project's own pytest suite (independently re-run, not taken from SUMMARY claims) and direct code
reading.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| MODAL-04 | 06-01, 06-02, 06-05, 06-07 | HippoRAG 2 fully decomposed, 13 positions, no opaque core | ✓ SATISFIED | Complete in REQUIREMENTS.md; unchanged this round, regression-checked (12 passed above) |
| MODAL-05 | 06-01, 06-03, 06-08, 06-10, 06-13, 06-14, 06-15 | Both modalities run side-by-side on one corpus, comparable | ✓ SATISFIED | **Newly Complete this round.** Real run completed against live credentials (06-15); independently confirmed against harness-returned values, code state, and a live regression re-run |
| API-08 | 06-03 | One query against 2+ modalities, per-arm keyed results, inspection-only | ✓ SATISFIED | Complete in REQUIREMENTS.md; unchanged this round, regression-checked (55 passed above). Note: `POST /documents/upload`'s 500-vs-422 gap (CR-02) is a real but separate robustness finding against this endpoint's own error-shape contract, not against API-08's tested compare/query truth. |
| MACH-10 | 06-09, 06-11 | F-07 discharged: mutable-store snapshot/reset or permanent exclusion | ✓ SATISFIED | Complete in REQUIREMENTS.md; unchanged this round, regression-checked |
| MACH-02 | 06-04 | Eval bundle minted with dev/holdout/sealed, both §EV.2 families | ✓ SATISFIED | Complete in REQUIREMENTS.md; unchanged this round |
| MACH-03 | 06-06, 06-12, 06-16, 06-17 | First A/A calibration, p95 floor at both tiers, Falsifier 5 | ✗ BLOCKED | Pending in REQUIREMENTS.md, correctly. Every code precondition closed; owner declined the spend a third time. Falsifier 5 open, not failed. |

No orphaned requirements: all six IDs declared across Phase 6 plans (`06-01` through `06-17`) match
exactly the six requirement rows REQUIREMENTS.md maps to "Phase 6."

### Human Verification Required

None. All six roadmap Success Criteria resolve to either VERIFIED (independently confirmed against
code, evidence documents, and a live test re-run) or FAILED (SC6 — an observable truth this
codebase does not yet contain, for a reason precisely characterized above: a repeated, informed
owner decision not to spend, not an open policy question or an ambiguous code state). Nothing in
this round requires a human judgment call this report cannot already make from direct evidence.

### Gaps Summary

Five of six roadmap Success Criteria are now met, up from four last round. The remaining gap
(SC6/MACH-03/Falsifier 5) is real, and it is precisely characterized rather than rounded in either
direction:

1. **Every code precondition for the A/A calibration is closed.** 06-12's judge-identity resolver
   and cost-bounded ingest, 06-14's fact-score root-cause fix, 06-16's previously-missing A/A
   driver, and 06-17's threshold pre-registered before any floor exists — all four are genuine,
   tested, and independently confirmed here, not merely asserted by their own SUMMARYs.
2. **No real A/A run has ever executed, and no floor exists at either target family.** The owner
   has now declined this identically-shaped question three times (06-06, 06-13, 06-17), most
   recently with every precondition and the driver itself already in place. This is a deliberate,
   recorded business decision, not a defect — and the project's own evidence documents correctly
   record Falsifier 5 as open (not failed) and MACH-03 as Pending (not Complete), because no
   comparison ran and there is no adverse verdict to record. But the roadmap's own SC6 text asserts
   a real, completed measurement, and that measurement does not exist in this codebase today. The
   phase goal — "the milestone's proof of swappability" — is achieved for the side-by-side run
   (SC2) but not for the calibration that would bound how much confidence that comparison deserves
   (SC6).
3. **Two Warning-severity defects in `aa_run.py` (06-REVIEW.md WR-01/WR-02) remain unfixed** and
   would surface only on the first real `--spend` invocation (a divide-by-zero on an empty
   gold-document list; unhandled exceptions escaping `main`'s refusal-mapping). Neither affects any
   scored truth today, since the path has never run for real, but a future plan authorizing the
   spend should fix these first rather than discover them mid-run.
4. **One latent evidence-integrity risk (06-REVIEW.md CR-01, this round) is worth flagging even
   though it does not change this round's verdict:** the regex guarding `FALSIFIER-5-EVIDENCE.md`
   against a smuggled-in floor value was narrowed to admit the pre-registered threshold's own `<=`
   phrasing, and in doing so became loose enough to admit a genuinely fabricated floor phrased the
   same way. I independently read the full evidence document and confirmed no floor value exists
   anywhere in it today — so nothing has been smuggled in — but the guard itself should be
   tightened before the next plan that could produce a real floor runs against it.

---

_Verified: 2026-09-11_
_Verifier: Claude (gsd-verifier)_

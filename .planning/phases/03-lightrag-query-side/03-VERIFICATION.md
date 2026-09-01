---
phase: 03-lightrag-query-side
verified: 2026-09-01T22:34:12Z
status: human_needed
score: 4/6 must-haves verified
behavior_unverified: 2 # criteria 2 and 6 — harness/evidence machinery present and tested, but the live comparison run itself is environment-gapped on this machine
overrides_applied: 0
behavior_unverified_items:
  - truth: "Owner runs the same corpus through the decomposed query side and the pre-decomposition original and reads an N-run variance band (criterion 2), inside criterion 6's deterministic retrieval-level substitute gate."
    test: "Rebuild the v1 pinned environment (v1/README-PARITY.md), re-run v1's real ingest to produce v1/.venv, v1/.parity_working_dir, v1/.parity_v2_store, v1/.env.parity, then re-run `databasise.parity.run_comparison` for all five arms and `databasise.evidence.parity_report` to render PARITY-EVIDENCE.md."
    expected: "Each arm's comparison status flips from `inconclusive` to `completed`, with a real N=5 keyword variance band and real chunk/entity/relation sym_diff numbers recorded, or every excursion outside tolerance recorded individually in DECLARED-DEVIATIONS.md."
    why_human: "The comparison requires a real OpenRouter-backed v1 ingest run and a rebuilt parity environment that do not exist on this machine (v1/.venv, v1/.parity_working_dir, v1/.parity_v2_store, v1/.env.parity are all absent, gitignored, worktree-local artifacts). No grep or static check can produce the missing runtime data; only an owner-run comparison on a machine holding those artifacts can close this."
  - truth: "Criterion 6's human spot-checks of answers are performed and recorded alongside the deterministic retrieval-level comparison."
    test: "Once the v1 environment and imported index exist, run each of the corpus snapshot's 2 queries (q1, q2) through `databasise.parity.run_comparison --arm hybrid` and through v1 directly, then read both answers side by side and judge substance match."
    expected: "A recorded human judgment (match / no-match, with notes) for each query pair, entered into PARITY-EVIDENCE.md or a successor evidence render."
    why_human: "An LLM-generated answer's substance is not mechanically checkable, and no A/A floor exists yet (MACH-02/MACH-03 deferred to Phase 6) to make word-for-word equality the right bar — only a human judgment call substitutes for it, exactly as 03-VALIDATION.md's Manual-Only Verifications table already states."
human_verification:
  - test: "Rebuild the v1 pinned environment (v1/README-PARITY.md), re-run v1's real ingest to produce v1/.venv, v1/.parity_working_dir, v1/.parity_v2_store, v1/.env.parity, then re-run `databasise.parity.run_comparison` for all five arms and `databasise.evidence.parity_report` to render PARITY-EVIDENCE.md."
    expected: "Each arm's comparison status flips from `inconclusive` to `completed`, with a real N=5 keyword variance band and real chunk/entity/relation sym_diff numbers recorded, or every excursion outside tolerance recorded individually in DECLARED-DEVIATIONS.md."
    why_human: "Requires a real OpenRouter-backed v1 ingest run and rebuilt parity environment absent on this machine; not mechanically verifiable by grep/static check."
  - test: "Once the v1 environment and imported index exist, run each of the corpus snapshot's 2 queries (q1, q2) through `databasise.parity.run_comparison --arm hybrid` and through v1 directly, then read both answers side by side and judge substance match."
    expected: "A recorded human judgment (match / no-match, with notes) for each query pair."
    why_human: "Answer substance is not mechanically checkable; no A/A floor exists yet to set an automatic bar."
---

# Phase 3: LightRAG Query Side Verification Report

**Phase Goal:** LightRAG's query path runs as fitted primitive parts and its parity against the original is measured, not asserted (§BP rung 2)
**Verified:** 2026-09-01T22:34:12Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Seventeen of eighteen §L.1 query-side positions run as fitted primitive-part nodes; the eighteenth (`embedder-index`) is authored as the one index-recipe node | ✓ VERIFIED | `databasise.parts_core.lightrag.LIGHTRAG_PARTS` has 15 registered `@0.1.0` parts (matches 18 wiring positions minus the 3 join-* and 2 budget-* positions that share one component each). `embedder-index@0.1.0` has `structural_depth='opaque'`, `artifact_scope='quarantined'`; `wirings/lightrag/base.json`'s `recipe.embedding` names it explicitly. Base wiring parses cleanly to 18 nodes via `parse_wiring` (verified this session). |
| 2 | Owner runs the same corpus through the decomposed query side and the pre-decomposition original and reads an N-run variance band, or every excursion is a named declared deviation | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | The harness (`databasise/parity/run_comparison.py`, `parity_report.py`) is built, unit-tested (25 passed in `test_parity_evidence.py`), and its provenance check runs clean (`--check-results` → "clean (5 arms)"). But no live comparison has actually run on this machine: `PARITY-EVIDENCE.md` reports `inconclusive` for all 5 arms and both queries, because `v1/.venv`, `v1/.parity_working_dir`, `v1/.parity_v2_store`, `v1/.env.parity` are absent (gitignored, worktree-local artifacts from a different session). `DECLARED-DEVIATIONS.md` correctly reports "zero declared deviations" but flags this as "nothing has been measured yet," not a completed clean pass. |
| 3 | Every fitted node reaches storage through a machine primitive only; the per-node ownership audit ships as part of the parity evidence | ✓ VERIFIED | No ported part under `databasise/parts_core/lightrag/` imports any `v1.*` module (grep confirmed). `check_import_boundary` exits 0. `_ScopedStoresView`/`_ScopedClientsView` in `runner/scheduler.py` route every store/client access through a `TouchRecorder` at one construction site. `storage_audit.py`'s `matched`/`no-touch`/`over-declared` states are reported distinctly (never collapsed into "compliant"), and the audit table ships inside `PARITY-EVIDENCE.md`'s "per-node storage-ownership audit" section (currently `inconclusive` for the same environment-gap reason as criterion 2). |
| 4 | Eval bundle minted per RIG §EV.1/§EV.2 before decomposition work reads holdout | N/A — deferred to Phase 6 | `03-GATE-AMENDMENT.md` records the second deferral of MACH-02, citing `SELECTION.md` as governing document and naming Phase 6 as point of first need. ROADMAP.md lines 106-107 and REQUIREMENTS.md lines 16-17 both carry the amendment annotation. |
| 5 | A/A calibration read, Falsifier 5 pass criterion met | N/A — deferred to Phase 6 | Same amendment record covers MACH-03; residual risk ("answer-level drift originating in `keywords` and `generate` stays unmeasured") stated plainly in the amendment and echoed in `PARITY-EVIDENCE.md`'s "What is not measured" section. |
| 6 | Until the A/A floor exists, parity is checked at the retrieval level with deterministic, zero-token comparisons, plus human spot-checks of answers (D-05 substitute gate) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | The deterministic retrieval-level diff machinery exists and is unit-tested (`test_retrieval_parity.py`: 11 passed, 1 skipped — the skip is the real two-arm live case). The `keywords` N-run variance band (D-12) is implemented and its own conformance is tested. But the actual comparison run and the human spot-check of answer substance have not been performed on this machine for the same environment-gap reason as criterion 2 — `03-VALIDATION.md`'s own Manual-Only Verifications table documents this as an open item. |

**Score:** 4/6 truths verified (criteria 4/5 are N/A — legitimately deferred to Phase 6 via a written, cross-referenced amendment, not part of Phase 3's own obligation); 2 present-but-behavior-unverified (criteria 2 and 6).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/clients/base.py`, `openai_compat.py`, `__init__.py` | Machine-owned LLM/embedding/rerank client primitive | ✓ VERIFIED | `ClientNotWiredError` defined and raised on missing wiring; `openai_compat.py` populates real `TokenAccounting` from provider `usage`. |
| `databasise/parity/import_index.py`, `corpus.py` | v1 index import + corpus snapshot | ✓ VERIFIED | `VerificationResult.status: Literal["verified","inconclusive","refused"]` present; corpus MANIFEST.json exists (20 docs, 2 queries, hashed). |
| `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md`, `COVERAGE.md` | Deferral record + API coverage matrix | ✓ VERIFIED | Amendment cites SELECTION.md, names Phase 6, states residual risk. COVERAGE.md has 15 decision rows, 0 unreasoned opt-outs. |
| `databasise/wirings/lightrag/base.json`, `resolve.py`, `parts_core/lightrag/__init__.py`, `parity/run_arm.py` | Naive-arm tracer end to end | ✓ VERIFIED | Base parses to 18 nodes; all 5 arms (naive=7, local=15, global=15, hybrid=17, bypass=1 nodes) resolve and parse with zero violations. |
| `databasise/parts_core/lightrag/keywords.py`, `entity_hydrate_expand.py`, `relation_hydrate_expand.py` | Graph half | ✓ VERIFIED | `entity-hydrate-expand`/`relation-hydrate-expand` read only `ctx.stores["graph"]`; `entity-lookup`/`relation-lookup` read only `ctx.stores["vector"]` — confirmed by grep, no cross-reach. |
| `databasise/parts_core/lightrag/join_roundrobin.py`, `truncator_token_budget.py`, `chunk_sel_kg.py` | Transform half | ✓ VERIFIED | `join-entities`/`join-relations`/`join-chunks` all resolve to `lightrag/join-roundrobin@0.1.0` with differing config; `budget-entities`/`budget-relations` resolve to `lightrag/truncator-token-budget@0.1.0`, each self-naming its `apportioning_node`. `chunk-sel-kg` declares `reads_vector` unconditionally (confirmed in source and registered Part effects). |
| `databasise/parity/v1_arm.py`, `v1_driver_script.py`, `run_comparison.py` | Parity harness | ✓ VERIFIED (harness) / ⚠️ (live run) | Harness code present, tested, provenance-clean; live comparison inconclusive on this machine (see criteria 2/6 above). |
| `databasise/parity/storage_audit.py`, `evidence/FALSIFIER-2-EVIDENCE.md` | Ownership audit + Falsifier 2 evidence retained | ✓ VERIFIED | `matched`/`no-touch`/`over-declared` states distinct; `FALSIFIER-2-EVIDENCE.md` still names `w1-lightrag-query-side` records post-stub-retirement, and `tests/validator/test_falsifier2_evidence.py` + `test_falsifier2_probes.py` pass (24 tests). |
| `databasise/evidence/PARITY-EVIDENCE.md`, `DECLARED-DEVIATIONS.md`, `parity_report.py` | Recorded parity evidence | ✓ VERIFIED (as an honest inconclusive render) | Document states plainly that no comparison has run yet and why; `--check-results` exits 0 clean. |
| `v1/.env.parity` | v1 parity env file | ✗ MISSING (expected) | Gitignored, worktree-local build artifact from a different execution session — documented gap, not a code defect. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `NodeContext.clients` | `runner/scheduler.py` construction site | Single population point | ✓ WIRED | Confirmed at `_scoped_clients` construction alongside `_ScopedStoresView`. |
| `_ScopedStoresView.__getitem__` / `_ScopedClientsView.__getitem__` | `TouchRecorder` | Recorder call on every access | ✓ WIRED | Confirmed in `runner/scheduler.py` lines ~259, ~296-300. |
| `databasise.run_wiring` | `runner.scheduler.run_wiring` | `clients` mapping forwarded | ✓ WIRED | `databasise/__init__.py` `run_wiring()` forwards `clients=clients` unchanged. |
| `wirings/resolve.py` (RFC 6902 patch) | `validator.parse.parse_wiring` | Patch applied before parse | ✓ WIRED | All 5 arm patches apply and parse cleanly (verified this session with live resolve+parse). |
| `v1_driver_script.py` | v1 interpreter (subprocess) | Never imported by `databasise/` | ✓ WIRED (by boundary check) | `check_import_boundary` exits 0; no `import lightrag` found in `parts_core/lightrag/`. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `cd databasise && uv run pytest -q` | 415 passed, 4 skipped | ✓ PASS |
| Base wiring parses | live `parse_wiring(base, default_registry())` | 18 nodes, no exception | ✓ PASS |
| All 5 arms resolve+parse | live `resolve_arm(arm)` + `parse_wiring` for naive/local/global/hybrid/bypass | 7/15/15/17/1 nodes respectively, no violations | ✓ PASS |
| Import boundary checker | `uv run python -m databasise.tools.check_import_boundary` | exit 0 | ✓ PASS |
| Parity provenance check | `uv run python -m databasise.evidence.parity_report --check-results` | "clean (5 arms)", exit 0 | ✓ PASS |
| Frozen-bug regression suite | `pytest tests/stores/test_graph_frozen_bugs.py` | 9 passed, no skip/xfail | ✓ PASS |
| Embedder-index reproduction | `pytest tests/parity/test_embedder_index_reproduction.py` | 4 passed, 1 skipped (live sample case, `human_judgment: true`) | ✓ PASS |
| Naive arm end-to-end + validator/parts suites | `pytest tests/parity/test_naive_arm_end_to_end.py tests/validator/ tests/parts/` | 92 passed, 1 skipped | ✓ PASS |
| Import boundary unit tests | `pytest tests/test_import_boundary.py` | 10 passed | ✓ PASS |
| Live 5-arm retrieval comparison | `run_comparison` for all arms | all `inconclusive` (environment-gapped) | ? SKIP → routed to human verification |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| MODAL-01 | 03-01, 02, 04–09 | LightRAG query side re-cut into primitive-part nodes with N-run variance-banded parity or declared deviations | ✓ SATISFIED (code); ⚠️ REQUIREMENTS.md tracking stale | The decomposition and harness are real and tested; the "variance-banded parity" half is machinery-present-but-not-yet-run (see criteria 2/6). REQUIREMENTS.md line 96 still reads `MODAL-01 \| Phase 3 \| Pending` with an unchecked `[ ]` box — a documentation-tracking lag, not a code gap, but it should be updated once the live comparison closes (or explicitly left "Pending" pending that run — the phase's own evidence document already says as much). |
| MACH-02 | 03-03, 03-09 | Eval bundle (RIG §EV.1) | N/A for Phase 3 — correctly deferred to Phase 6 | `03-GATE-AMENDMENT.md`; REQUIREMENTS.md line 86 correctly maps MACH-02 → Phase 6. |
| MACH-03 | 03-03, 03-09 | A/A calibration, Falsifier 5 | N/A for Phase 3 — correctly deferred to Phase 6 | Same amendment; REQUIREMENTS.md line 87 correctly maps MACH-03 → Phase 6. |

No orphaned requirements: ROADMAP.md's own "Requirements" field for Phase 3 lists only `MODAL-01`; MACH-02/MACH-03 appear in plan frontmatter solely because those plans do the deferral-recording work, and REQUIREMENTS.md's traceability table already attributes their substance to Phase 6, consistent with the amendment.

### Anti-Patterns Found

None. Grep for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER|not yet implemented|coming soon` across all `.py`/`.md` files under `databasise/clients/`, `databasise/parity/`, `databasise/parts_core/lightrag/`, `databasise/wirings/`, `databasise/evidence/` returned zero matches (excluding JSON test-fixture data).

### Prohibitions Check (phase-wide, judgment-tier)

All 8 shared prohibitions carried in every plan's `must_haves.prohibitions` block were spot-checked against the actual code and evidence documents:

| Prohibition | Status | Evidence |
|-------------|--------|----------|
| Harness must not emit pass/fail on failed index-identity precondition — must emit `inconclusive` | ✓ HELD | `import_index.py`, `run_comparison.py` both use `Literal["...", "inconclusive", ...]`; `PARITY-EVIDENCE.md` renders `inconclusive` throughout, never a fabricated pass. |
| Variance band must carry run count and cache status, never cache-served re-runs | ✓ HELD | `PARITY-EVIDENCE.md`'s keyword variance table has `run count (N)` and `any cache served` columns (currently "not run" rather than fabricated). |
| Declared-deviation record must not use a blanket/catch-all category | ✓ HELD | `DECLARED-DEVIATIONS.md` states "the renderer refuses to render rather than silently absorbing the excursion into an unnamed category"; currently a stated, explained zero. |
| A node making a real LLM/embedding/rerank call must not report zero spend | ✓ HELD | `openai_compat.py` derives `TokenAccounting` from real provider `usage`; scheduler docstring explicitly names this as the guarantee (`runner/scheduler.py:93`). |
| v1 original arm must not be presented with a RIG §TR.1 record it didn't produce; trace asymmetry must be stated | ✓ HELD | `PARITY-EVIDENCE.md`'s "The trace asymmetry" section states this explicitly before any numbers. |
| MACH-02/MACH-03 deferral must not be silent or recorded as passed/satisfied/n-a | ✓ HELD | Amendment + REQUIREMENTS.md both explicit; REQUIREMENTS.md checkboxes remain unchecked, not marked complete. |
| Storage audit must not report a no-touch node as audited-compliant | ✓ HELD | `storage_audit.py` has three distinct states (`matched`/`no-touch`/`over-declared`); no "compliant" collapse. |
| Regenerating Falsifier 2 evidence must not silently change recorded verdicts | ✓ HELD | `test_falsifier2_evidence.py`/`test_falsifier2_probes.py` (24 tests) pass; `w1-lightrag-query-side` records remain intact post-stub-retirement. |

### Human Verification Required

1. **Live five-arm parity comparison** — Rebuild the v1 pinned environment (`v1/README-PARITY.md`), re-run v1's real OpenRouter ingest to regenerate `v1/.venv`, `v1/.parity_working_dir`, `v1/.parity_v2_store`, `v1/.env.parity` (all gitignored/worktree-local, absent on this machine), then re-run `databasise.parity.run_comparison` for all 5 arms and re-render `databasise.evidence.parity_report`.
   - Expected: comparison status flips from `inconclusive` to `completed`; a real N=5 keyword variance band and real chunk/entity/relation sym_diff numbers are recorded, or every excursion is individually named in `DECLARED-DEVIATIONS.md`.
   - Why human: requires real model-API-backed ingest and a rebuilt local environment; no static/grep check can produce the missing runtime artifacts.

2. **Human spot-check of answer substance** — Once the environment above exists, run the corpus snapshot's 2 queries (q1, q2) through the `hybrid` arm and through v1 directly, and judge whether the answers' substance matches.
   - Expected: a recorded judgment per query pair.
   - Why human: LLM-generated answer substance is not mechanically checkable, and no A/A floor exists yet (Falsifier 5 deferred to Phase 6) to make exact-match the right bar.

### Gaps Summary

No blocking gaps. The phase's own code, wiring, harness, evidence-rendering, and test suite are all real, substantive, and correctly wired — every artifact and key link declared in the nine plans' `must_haves` was independently confirmed against the live codebase this session (base/arm wiring parsing, store/client scoping with touch recording, storage-ownership audit's three-state model, import-boundary isolation, real token metering, and the MACH-02/MACH-03 deferral's cross-document consistency).

The two items left open (criteria 2 and 6 — the actual live N-run parity comparison and the human answer spot-check) are not code gaps: the harness that would produce them is built and unit-tested, and the reason they read `inconclusive` is a documented, expected environment gap (v1 build artifacts absent on this machine) rather than a defect. `03-VALIDATION.md`'s own sign-off already draws this same line and names it explicitly as the phase's one open item. These are routed to human verification, not recorded as failed truths.

One minor documentation-tracking item: `.planning/REQUIREMENTS.md`'s traceability table still lists `MODAL-01` as `Phase 3 | Pending` with its checkbox unchecked. Given the substance is otherwise verified and the parity comparison itself remains open pending the human items above, leaving MODAL-01 "Pending" until that live run closes is arguably correct — but it is worth an explicit owner decision on whether to flip it now (decomposition done, parity machinery proven) or hold it for the live run.

---

_Verified: 2026-09-01T22:34:12Z_
_Verifier: Claude (gsd-verifier)_

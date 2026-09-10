---
phase: 06-hipporag-2-side-by-side
verified: 2026-09-10T00:00:00Z
status: gaps_found
score: 3/6 truths verified
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/ROADMAP.md"
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
  - ".planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md"
  - ".planning/phases/06-hipporag-2-side-by-side/COVERAGE.md"
  - "databasise/eval/bundle.py"
  - "databasise/eval/calibration.py"
  - "databasise/evidence/CROSS-MODALITY-EVIDENCE.md"
  - "databasise/evidence/EVAL-BUNDLE-V1.md"
  - "databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md"
  - "databasise/evidence/F-14-SEAM-INVARIANCE.md"
  - "databasise/evidence/FALSIFIER-5-EVIDENCE.md"
  - "databasise/evidence/HIPPORAG-PORT-RECORD.md"
  - "databasise/mcp/server.py"
  - "databasise/mcp/tools.py"
  - "databasise/parity/build_hipporag_index.py"
  - "databasise/parity/run_arm.py"
  - "databasise/parity/run_cross_modality.py"
  - "databasise/parts_core/hipporag/__init__.py"
  - "databasise/parts_core/hipporag/assemble_result.py"
  - "databasise/parts_core/hipporag/chunk_embed.py"
  - "databasise/parts_core/hipporag/dpr_fallback.py"
  - "databasise/parts_core/hipporag/entity_fact_embed.py"
  - "databasise/parts_core/hipporag/fact_edges.py"
  - "databasise/parts_core/hipporag/fact_filter.py"
  - "databasise/parts_core/hipporag/fact_score.py"
  - "databasise/parts_core/hipporag/graph_augment_persist.py"
  - "databasise/parts_core/hipporag/openie.py"
  - "databasise/parts_core/hipporag/passage_edges.py"
  - "databasise/parts_core/hipporag/ppr.py"
  - "databasise/parts_core/hipporag/reset_vector_join.py"
  - "databasise/parts_core/hipporag/synonymy_edges.py"
  - "databasise/seam/compare.py"
  - "databasise/seam/engine.py"
  - "databasise/seam/rest.py"
  - "databasise/stores/graph.py"
  - "databasise/stores/vector.py"
  - "databasise/wirings/hipporag/base.json"
covered_digest: "v1:sha256:7f4570b00844f8bb8fbc290971c38b63b441508a8f0a26cdb489d54e319161d8"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "LightRAG and HippoRAG 2 run on one corpus under RIG §RUN, isolated stores, outputs structurally comparable (roadmap Success Criterion 2 / MODAL-05)"
    status: failed
    reason: >
      Two independent, compounding failures. (1) No real cross-modality run against the Phase 3
      parity corpus has ever executed — the owner declined the spend at 06-08's own
      gate="blocking-human" checkpoint, and this is recorded honestly as BLOCKED in
      databasise/evidence/CROSS-MODALITY-EVIDENCE.md. (2) Independent of spend authorization, the
      public seam has no path to populate HippoRAG's index at all: Databasise.ingest() and
      delete_document() (databasise/seam/engine.py:180-190, 596-729) are hardcoded to
      wirings/lightrag/corpus-ingest.json and corpus-delete.json; no
      databasise/wirings/hipporag/ equivalent exists on disk (only base.json). The only way
      HippoRAG's index side has ever been driven is databasise/parity/build_hipporag_index.py, a
      standalone harness that calls the scheduler directly and bypasses Databasise entirely — and
      that harness has never been invoked. This means even if spend were authorized today, a
      caller cannot ingest a document into HippoRAG through ingest() (in-process, REST, or MCP)
      at all. This phase's own COVERAGE.md (line ~22) states ingest/delete "remain reachable
      identically for both LightRAG and HippoRAG arms" — that claim is false as written for these
      two operations. I independently confirmed both halves of this: engine.py's hardcoded paths,
      and the absence of any hipporag/corpus-ingest.json or corpus-delete.json file.
    artifacts:
      - path: "databasise/seam/engine.py"
        issue: "ingest()/delete_document() hardcode _INGEST_WIRING_PATH/_DELETE_WIRING_PATH to the LightRAG-only wiring files with no per-modality dispatch and no named refusal when no ingest path exists for a resolved/target modality"
      - path: ".planning/phases/06-hipporag-2-side-by-side/COVERAGE.md"
        issue: "Claims ingest/delete are reachable identically for both arms; false for HippoRAG, which has no ingest/delete wiring at all"
    missing:
      - "Either a databasise/wirings/hipporag/corpus-ingest.json (and corpus-delete.json) analog with ingest()/delete_document() routed per target modality, or an explicit named refusal (mirroring UnknownDocumentError's house style) when no ingest path exists for the resolved modality — plus a corrected COVERAGE.md that states the write-surface limitation plainly instead of claiming identical reachability"
      - "Owner authorization and execution of build_hipporag_index.py and run_cross_modality.py against the Phase 3 parity corpus — MODAL-05's own real-corpus proof point"
  - truth: "One real A/A calibration has run, producing a bootstrap-resampled p95 floor at both §EV.2 target families with T1's null width materially narrower than T0's (roadmap Success Criterion 6 / MACH-03, Falsifier 5)"
    status: failed
    reason: >
      The calibration instrument (databasise/eval/calibration.py: calibrate_aa_floor,
      NullIdentity, UnusableFloorError, StaleNullError) is built and fully tested against fixture
      data (15 passing tests), but no real A/A run has ever executed — the owner declined the
      spend at 06-06's own checkpoint. Recorded honestly as BLOCKED in
      databasise/evidence/FALSIFIER-5-EVIDENCE.md: no floor value exists for either tier, and two
      concrete preconditions (a resolved, non-"unresolved" judge_instance; a cost-bounded ingest
      path for the 291-document eval-corpus) remain unmet. The eval bundle itself (MACH-02) is
      correctly minted and complete — only the calibration run named by this success criterion is
      outstanding.
    artifacts:
      - path: "databasise/evidence/FALSIFIER-5-EVIDENCE.md"
        issue: "States plainly BLOCKED, not discharged; no p95 floor reported for either tier"
    missing:
      - "A re-minted eval bundle with a resolved (non-sentinel) judge_instance"
      - "A cost-bounded ingest path for the 291-document eval-corpus (current full-ingest path reports spend as unbudgetable)"
      - "One real A/A run producing paired per-question differences and a bootstrap p95 floor at each of the two §EV.2 target families"
human_verification:
  - test: "Confirm codebase-memory-mcp's permanent-exclusion disposition (F-07 / MACH-10) matches owner intent"
    expected: "Owner explicitly affirms permanent exclusion of codebase-memory-mcp from §5 parity/determinism comparisons, or requests a snapshot/reset protocol be built for it instead of exclusion"
    why_human: "06-09-PLAN.md's own Task 1 <human-check> names this exact confirmation as the gate before MACH-10 flips from Pending to Complete in REQUIREMENTS.md. The substance is already discharged in code (F-07-MUTABLE-STORE-DISPOSITION.md, enforced by MutableStoreComparisonExcludedError) — only the owner's confirmation that the disposition matches their intent is outstanding, and that is a policy judgment, not something derivable from the codebase."
---

# Phase 6: HippoRAG 2 & Side-by-Side Verification Report

**Phase Goal:** Two modalities answer the same corpus behind the same seam and the caller sees both at once — the milestone's proof of swappability (§BP rung 4)
**Verified:** 2026-09-10
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | HippoRAG 2 runs as thirteen fitted node positions, no opaque core left, whole-graph PPR via §14.2 bulk-export into native igraph/prpack, index-side depth stays `opaque` until parity shown | ✓ VERIFIED | `databasise/wirings/hipporag/base.json` declares exactly 13 nodes; `ppr.py` calls `graph_store.export_to_igraph()` then `graph.personalized_pagerank(..., implementation="prpack")` — no per-node loop; `CozoGraphStore.export_to_igraph` builds the whole graph from exactly two Cozo queries. `test_thirteen_positions.py`, `test_graph_bulk_export.py` pass (28/28 in spot-check run). MODAL-04 recorded Complete in REQUIREMENTS.md with the parity deferral named explicitly, not left absent. |
| 2 | LightRAG and HippoRAG 2 run on one corpus, isolated stores, outputs structurally comparable | ✗ FAILED | No real cross-modality run against the Phase 3 parity corpus has occurred (`CROSS-MODALITY-EVIDENCE.md`, honest BLOCKED record). Independently and more severely: `Databasise.ingest()`/`delete_document()` are hardcoded to LightRAG-only wiring files (`databasise/seam/engine.py:180-190,596-729`); no `databasise/wirings/hipporag/corpus-ingest.json` or `corpus-delete.json` exists anywhere in the repo (verified: only `hipporag/base.json` present). There is no way to populate HippoRAG's index through the public seam at all, contradicting `COVERAGE.md`'s claim of identical reachability for `ingest`/`delete`. See Gap 1. |
| 3 | Caller sends one query against two or more modalities, receives per-arm results keyed by caller-supplied selectors, no verdict, single arm degenerates to a run | ✓ VERIFIED | `Databasise.compare` (`seam/engine.py:540`), `POST /compare` (`seam/rest.py:198`), `compare` MCP tool (`mcp/tools.py`, roster grew from five to six). `test_compare.py`, `test_rest_transport.py`, `test_dual_transport_parity.py`, `test_tool_growth_invariant.py` pass. |
| 4 | The first genuine seam call records F-14's outcome either way | ✓ VERIFIED | `databasise/evidence/F-14-SEAM-INVARIANCE.md`: a real two-arm `Databasise.compare()` call (LightRAG `naive` vs HippoRAG base wiring), all ten `ResponseEnvelope` fields present in both arms, verdict: no consumer-visible field-set change. `test_f14_record.py` passes. |
| 5 | Mutable-store components have a defined snapshot/reset protocol or are recorded as permanently excluded — F-07 discharged | ⚠️ Human verification needed | Substance is discharged: `F-07-MUTABLE-STORE-DISPOSITION.md` names all mutable-store components with a disposition each; `MutableStoreComparisonExcludedError` enforces the refusal in `compare()` (confirmed live in `seam/refusals.py`, `seam/engine.py:591`, exercised by `test_mutable_store_exclusion.py`, 2/2 relevant tests pass). MACH-10 stays Pending in REQUIREMENTS.md solely because 06-09-PLAN.md's own `<human-check>` requires owner confirmation that codebase-memory-mcp's permanent-exclusion disposition matches their intent — not yet recorded. |
| 6 | Owner mints an eval bundle (MACH-02) then runs one A/A calibration reading a p95 floor at both target families with T1 materially narrower than T0 (MACH-03, Falsifier 5) | ✗ FAILED | MACH-02 half verified: `bundle@v1` minted, committed, dev/holdout/sealed splits, both §EV.2 families present (`EVAL-BUNDLE-V1.md`). MACH-03 half not met: the calibration instrument is built and fixture-tested (`databasise/eval/calibration.py`, 15 tests), but no real A/A run occurred — owner declined spend, recorded honestly as BLOCKED in `FALSIFIER-5-EVIDENCE.md`. No p95 floor exists for either tier. See Gap 2. |

**Score:** 3/6 truths verified (0 present-but-behavior-unverified)

### CR-01 Assessment (requested independent judgment)

I independently confirmed both halves of the code-review's CR-01 finding:

- `databasise/seam/engine.py` lines 180-190 hardcode `_INGEST_WIRING_PATH` and `_DELETE_WIRING_PATH` to `wirings/lightrag/corpus-ingest.json`/`corpus-delete.json`, with `ingest()` (line 596) and `delete_document()` (line 662) reading those fixed paths unconditionally.
- `find databasise/wirings -iname '*.json'` lists only `hipporag/base.json` for the HippoRAG arm — no ingest or delete wiring exists for it.
- `.planning/phases/06-hipporag-2-side-by-side/COVERAGE.md` states `ingest`/`delete` "remain reachable identically for both LightRAG and HippoRAG arms with no operation-level change." This is false as written: HippoRAG has zero reachable ingest or delete path through `Databasise`, in-process or over either transport.

**Conclusion:** Success Criterion 2 cannot be considered met. It fails for two independent reasons — the deliberately-deferred real run (owner spend decision, honestly recorded) and this separate, undisclosed structural gap that would block the real run's own ingestion step even if spend were authorized today, since the only working HippoRAG ingestion path (`databasise/parity/build_hipporag_index.py`) bypasses the public seam entirely. The COVERAGE.md claim is not accurate as written and should be corrected to name this limitation rather than assert identical reachability. This is recorded as Gap 1 below, distinct from and more severe than the two acknowledged-BLOCKED evidence records, because it is a code/documentation gap rather than an honestly-recorded pending spend decision.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/wirings/hipporag/base.json` | 13-node HippoRAG wiring | ✓ VERIFIED | 13 keys in `nodes`, confirmed by direct JSON parse |
| `databasise/parts_core/hipporag/ppr.py` | Whole-graph PPR via bulk export + native prpack | ✓ VERIFIED | Calls `export_to_igraph()` then `personalized_pagerank(..., implementation="prpack")` |
| `databasise/stores/graph.py` (`export_to_igraph`) | §14.2 bulk-export, two Cozo queries, no per-node loop | ✓ VERIFIED | Confirmed by direct read; two `_run` calls (nodes, edges) |
| `databasise/stores/vector.py` (`self_knn`) | Batched self-KNN, search count independent of stored-vector count | ✓ VERIFIED | `test_vector_self_knn.py` passes |
| `databasise/seam/compare.py` / `Databasise.compare` | Fan-out over existing `_execute` path, no second scheduler | ✓ VERIFIED | `seam/engine.py:540`; `test_compare.py` passes |
| `databasise/evidence/F-14-SEAM-INVARIANCE.md` | Real cross-modality call, outcome recorded either way | ✓ VERIFIED | Present, dated, real call documented with full envelope field table |
| `databasise/evidence/FALSIFIER-5-EVIDENCE.md` | Honest BLOCKED record, no fabricated floor | ✓ VERIFIED | Present; explicitly states no floor computed, names both preconditions |
| `databasise/evidence/CROSS-MODALITY-EVIDENCE.md` | Honest BLOCKED record, no fabricated counts | ✓ VERIFIED | Present; explicitly states no real invocation occurred |
| `databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md` | Every `mutates_store` component given a disposition | ✓ VERIFIED | Enforced by `MutableStoreComparisonExcludedError`, exercised by passing tests |
| `databasise/wirings/hipporag/corpus-ingest.json` (implied by COVERAGE.md's claim) | A HippoRAG ingest wiring analog | ✗ MISSING | Does not exist — see Gap 1 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `Databasise.compare` | `Databasise._execute` per arm | same envelope-assembly/redaction path `query()` uses | ✓ WIRED | Confirmed by reading `seam/engine.py`, no second envelope-assembly function |
| `POST /compare` / MCP `compare` tool | `Databasise.compare` | identical method, no transport-local logic | ✓ WIRED | `seam/rest.py:198`, `mcp/tools.py` both call the one method |
| `entity-fact-embed`'s `hipporag-entities` namespace | `synonymy-edges`' `self_knn` | `graph-augment-persist` → `export_to_igraph` → `ppr` | ✓ WIRED | Confirmed by reading the chain in `parts_core/hipporag/` and passing `test_graph_construction.py`, `test_ppr.py` |
| `Databasise.ingest()` / `delete_document()` | a HippoRAG-side wiring | (none) | ✗ NOT_WIRED | No such wiring exists; both methods hardcode LightRAG paths — Gap 1 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Comparison surface, F-14 record, mutable-store exclusion, cross-modality isolation harness logic | `pytest tests/seam/test_compare.py tests/evidence/test_f14_record.py tests/parity/test_cross_modality_isolation.py tests/seam/test_mutable_store_exclusion.py` | 23 passed, 2 skipped (real-index tests, skip-guarded — no real HippoRAG index exists) | ✓ PASS |
| Thirteen-position conformance, bulk-export, self-KNN, DPR-fallback guard | `pytest tests/parts_core/hipporag/test_thirteen_positions.py tests/stores/test_graph_bulk_export.py tests/stores/test_vector_self_knn.py tests/parts_core/hipporag/test_dpr_fallback_guard.py` | 28 passed | ✓ PASS |
| Full workspace suite (reported by executor, spot-checked at the file level above rather than re-run in full here) | `uv run --extra rest --extra mcp pytest -q` | 918 passed, 3 skipped | ✓ PASS (as reported; the 3 skips are the same class of real-index skip-guards seen above) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| MODAL-04 | 06-01, 06-02, 06-05, 06-07 | HippoRAG 2 fully decomposed, 13 positions, no opaque core | ✓ SATISFIED | Complete in REQUIREMENTS.md; independently confirmed (13 nodes, bulk-export PPR) |
| MODAL-05 | 06-01, 06-03, 06-08 | Both modalities run side-by-side on one corpus, comparable | ✗ BLOCKED | Pending in REQUIREMENTS.md; no real run occurred, and CR-01 shows the write surface cannot support it today regardless of spend |
| API-08 | 06-03 | One query against 2+ modalities, per-arm keyed results, inspection-only | ✓ SATISFIED | Complete in REQUIREMENTS.md; independently confirmed via `compare()`/`POST /compare`/MCP tool and passing tests |
| MACH-10 | 06-09 | F-07 discharged: mutable-store snapshot/reset or permanent exclusion | ? NEEDS HUMAN | Pending in REQUIREMENTS.md solely on owner confirmation; substance discharged in code |
| MACH-02 | 06-04 | Eval bundle minted with dev/holdout/sealed, both §EV.2 families | ✓ SATISFIED | Complete in REQUIREMENTS.md; independently confirmed (`EVAL-BUNDLE-V1.md`) |
| MACH-03 | 06-06 | First A/A calibration, p95 floor at both tiers, Falsifier 5 | ✗ BLOCKED | Pending in REQUIREMENTS.md; instrument built and tested, no real run |

No orphaned requirements: all six IDs declared across Phase 6 plans (`06-01` through `06-09`) match exactly the six requirement rows REQUIREMENTS.md maps to "Phase 6."

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `databasise/seam/engine.py` | 180-190, 596-729 | Hardcoded LightRAG-only ingest/delete wiring paths, no per-modality dispatch or refusal | 🛑 Blocker | HippoRAG's index cannot be populated through the public seam at all — Gap 1 (CR-01, independently confirmed) |
| `.planning/phases/06-hipporag-2-side-by-side/COVERAGE.md` | ~19-22 | Claims ingest/delete "remain reachable identically for both LightRAG and HippoRAG arms" | 🛑 Blocker (documentation) | False claim in the phase's own coverage record; must be corrected alongside the code fix or refusal |
| `databasise/wirings/hipporag/base.json` | 18-24 (`entity-fact-embed` node) | Node-level `effects` under-declares `writes_kv` relative to its own registered Part and its own evidence record | ⚠️ Warning | Audit-trail gap only — not a runtime bug, since effect-union computations key off the registered Part, not the wiring node (per 06-REVIEW.md WR-01) |
| `databasise/parts_core/hipporag/entity_fact_embed.py` | 159 | Reports only the entity-embedding call's `resolved_model_identity`, drops the fact-embedding call's own | ⚠️ Warning | Harmless today (one client resolves one identity per process); latent gap if a future client resolves per-call identities (06-REVIEW.md WR-02) |
| `.planning/ROADMAP.md` | Progress table, Phase 6 row | States "7/9" plans complete while the phase's own plan checklist shows all nine `[x]`ed | ℹ️ Info | Stale bookkeeping — likely reflects that 06-06 and 06-08 executed Task 1 only (owner-deferred Tasks 2/3), not a new finding beyond Gaps 1-2 above |
| No `TBD`/`FIXME`/`XXX` markers found in any phase-modified file | — | — | — | Debt-marker gate clear |

No TODO/HACK/PLACEHOLDER instances found in phase-modified files that are not explicitly documented, intentional placeholders (e.g. `TIER_PLACEHOLDER = "T3"` in the trace-schema code, commented as deliberate).

### Human Verification Required

#### 1. Confirm codebase-memory-mcp's permanent-exclusion disposition (MACH-10)

**Test:** Review `databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md`'s recorded disposition for `codebase-memory-mcp@0.1.0` (`CA-2`) — permanent exclusion from §5 parity/determinism comparisons.
**Expected:** Owner affirms this matches their intent, or requests a snapshot/reset protocol be defined instead.
**Why human:** 06-09-PLAN.md's own `<human-check>` names this confirmation as the sole remaining gate before MACH-10 flips from Pending to Complete. It is a policy decision, not a code-derivable fact.

### Gaps Summary

Phase 6 delivered real, tested, working machinery for the parts of the goal that do not require
live LLM/embedding spend: HippoRAG's 13-position decomposition (SC1), the comparison surface across
all three transports with F-14's outcome recorded from a genuine call (SC3, SC4), and the eval
bundle (half of SC6). Those pieces hold up under independent tracing and passing tests.

Two roadmap success criteria are not met, and the phase's own record is honest about one of the two
reasons in each case:

1. **SC2 (side-by-side one corpus)** fails for two reasons. The acknowledged one — no real
   cross-modality run has been authorized — is recorded honestly as BLOCKED. The second,
   independently confirmed here, is not acknowledged in `COVERAGE.md`: the public seam's
   `ingest`/`delete` operations have no path to HippoRAG's index at all, so even an authorized real
   run could not populate HippoRAG through the product surface the milestone is supposed to prove
   swappable. `COVERAGE.md`'s claim of identical reachability is false as written.
2. **SC6 (A/A calibration)** is half-met: the eval bundle stands, but the actual calibration run
   (Falsifier 5) never executed, honestly recorded as BLOCKED pending two named preconditions.

One item (SC5 / MACH-10) is functionally complete pending a one-line owner confirmation the plan
itself flagged as deferred to end-of-phase human verification — this is not a code gap.

None of the three Pending-by-design items (MACH-03, MODAL-05, MACH-10) should be treated as
oversights — the phase's own evidence records and REQUIREMENTS.md rows are unusually candid about
what did and did not happen and why. The CR-01 finding is a different kind of item: it is a real,
previously-undisclosed gap between what the code can do and what the phase's own coverage record
claims it does, and it should be closed (or the claim corrected) independent of any future spend
authorization.

---

_Verified: 2026-09-10_
_Verifier: Claude (gsd-verifier)_

---
gsd_state_version: 1.0
milestone: v1.0
current_phase: 05
current_phase_name: Opaque-Side Admission
status: executing
stopped_at: Completed 05-01-PLAN.md
last_updated: "2026-09-08T21:56:11.881Z"
last_activity: 2026-09-08
last_activity_desc: Phase 05 execution started
state_head: fbb96c4abe0780c078a11033c1992bf8e4c9f53d
progress:
  total_phases: 7
  completed_phases: 3
  total_plans: 39
  completed_plans: 33
milestone_name: milestone
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-29)

**Core value:** Modalities are swappable without consumers noticing — LightRAG and HippoRAG 2 both live behind one unchanging §18 envelope, comparable side-by-side on the rig.
**Current focus:** Phase 05 — Opaque-Side Admission

## Current Position

Phase: 05 (Opaque-Side Admission) — EXECUTING
Plan: 2 of 7
Status: Ready to execute
Last activity: 2026-09-08 — Phase 05 execution started

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 19
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 10 | - | - |
| 02 | 4 | - | - |
| 04 | 5 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 03 P10 | 35min | 3 tasks | 6 files |
| Phase 03 P11 | ~45min (this session; continuation after prior executor cut off by rate limit at ~31min) | 2 tasks | 9 files |
| Phase 03 P12 | ~90min | 3 tasks | 12 files |
| Phase 03 P13 | 65min | 3 tasks | 16 files |
| Phase 04 P01 | 30min | 3 tasks | 13 files |
| Phase 04 P02 | 45min | 3 tasks | 8 files |
| Phase 04 P03 | 70min | 3 tasks | 9 files |
| Phase 04 P04 | 90min | 3 tasks | 7 files |
| Phase 04 P05 | 45min | 3 tasks | 7 files |
| Phase 05-opaque-side-admission P01 | 165min | 3 tasks | 24 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: 7 phases follow §BP's four rungs, with the §18 seam locked between rung 2 and rung 3 so ingest endpoints ship against a frozen envelope
- Roadmap: rung 1 split into Machine Core (Phase 1) and Falsifier Gate (Phase 2) — the gate decision is the phase boundary, not an item buried in a foundation phase
- Ratified 2026-08-29: §VD conditional go; D4 One Machine; SELECTION.md governs on disagreement
- [Phase ?]: 03-10: Disclosed hybrid/local/global's decomposed-run degradation (entity-hydrate-expand/relation-hydrate-expand NodeExecutionError) in PARITY-EVIDENCE.md's Verdict rather than rendering their 0 sym_diff as exact retrieval agreement per the plan's literal text — an overstated claim the evidence machinery exists to refuse (Rule 1).
- [Phase ?]: 03-10: MODAL-01's REQUIREMENTS.md traceability row stays Pending — the dated annotation states the measured outcome, but the answer-substance spot-check is unrecorded and the graph-arm degradation is unrepaired.
- [Phase 03]: 03-11: Repopulated v1's entity/relation knowledge graph by fixing the OPENAI_LLM_EXTRA_BODY

unquoted-assignment defect (bash quote-removal on .env.parity sourcing) and adding startup/
post-ingest guards that refuse silently-empty extraction; also fixed a pre-existing float/str
TypeError in v1/lightrag/operate.py's edge-weight merge that blocked the re-ingest outright, and
widened import_index.py's vector-hash rounding-grid tolerance (3->2 decimals) after real
188-vector entity data tripped the exact floating-point boundary case its own docstring had
already flagged as possible. — Both fixes were required for the plan's own <verify> gates to pass (test_real_v1_build_verifies_clean
depends on real, non-empty entity data reaching verify_import for the first time); both are narrowly
scoped, single-cause bug fixes rather than redesigns, and are documented as Rule 1 deviations in
03-11-SUMMARY.md.

- [Phase 03]: 03-12: Fixed the shared-vector-store bug (all four vector-reading positions served the same chunks-only FaissVectorStore) via a new MultiNamespaceVectorStore handle with per-namespace selection and a named refusal when unselected. — entity-lookup/relation-lookup were being served chunk records with no entity_name/src_id fields, producing the recorded NodeExecutionError; a wiring-level fix (one shared store instance under one capability key) needed a namespace-scoped handle, not a per-node workaround.
- [Phase 03]: 03-12: Found and fixed a second latent bug (heading-backfill hardcoded a naive-arm-only dependency name) discovered only once the namespace fix let retrieval reach that node for the first time on hybrid/local/global. — The base wiring names this node's sole dependency join-chunks; only the naive arm patch renames it to chunk-vector. Fixed by reading the dependency positionally instead of by a hardcoded name.
- [Phase 03]: 03-13: A real five-arm run (post-03-11/03-12 fixes) closed 03-VERIFICATION.md gap 3 fully — all five arms complete a real, non-degraded retrieval on both sides — but surfaced a new one: hybrid/local/global's real entity/relation retrieval disagrees substantially with the original arm (18 unreasoned excursions). — No prior real committed run had all three graph arms complete simultaneously; the crash previously masked this disagreement as a vacuous zero. CONTRACT §5 requires a human-authored cause for each excursion, which does not exist yet, so this is reported honestly rather than assumed acceptable.
- [Phase 03]: 03-13: Added render_deviations_document() to parity_report.py rather than weakening render_deviations_markdown()'s CONTRACT §5 refusal, after the real run showed the strict function would block the whole DECLARED-DEVIATIONS.md render over any one of 18 new uncaused excursions. — 03-10-PLAN.md's own must-have truth 3 tests that the strict refusal aborts the render on a completed excursion with no cause; a wrapper that renders already-caused excursions normally and lists not-yet-caused ones as an honest PENDING section keeps that tested contract untouched while still producing a real, non-stale document.
- [Phase 04]: 04-01: checkpoint answer applied verbatim — declare-upfront for the §18.2 envelope field set; resolved_model_identity excluded from the envelope (FA-02 resolved).
- [Phase 04]: 04-01: the default selector resolves unconditionally to the naive arm; alias/capability/harness raise NotImplementedError naming 04-03 as owner rather than falling through silently.
- [Phase 04]: Extracted a shared _StrictModel base into databasise/seam/_base.py to break the envelope<->evidence/tokens circular import (Pitfall 7) — envelope.py needs to import EvidenceRef/TokenBreakdownEntry from evidence.py/tokens.py to bind them into its own fields; those modules need the same strict base envelope.py's models use
- [Phase 04]: EvidenceRef carries only ref/namespace/kind/score/tier, not the full §4 ChunkRef shape — corpus_id, recipe@version, ordinal, and content_hash are not available at the retrieval position today (FA-03); declared as a named limitation rather than shipping a reference that only looks like a ChunkRef
- [Phase 04]: Checkpoint answer applied: dedicated-alias-column. Added an additive `alias TEXT` column to the ledger schema rather than overloading mutation_id, since the ledger is append-only and a Phase 7 row could never be disentangled later. Ledger.by_alias projects the active pointer keyed on alias; the seam's alias branch resolves the returned record's mutation_id as an arm name.
- [Phase 04]: Capability selector tie-break is smallest-resolved-wiring-wins, not declared-arm-order: every arm's effect set is not disjoint from its neighbours' (bypass's calls_llm is a subset of every other arm's effects), so a declared-order tie-break would make every arm but naive permanently unreachable by capability alone.
- [Phase 04]: The default selector's opaque exclusion (§8 condition 7) is scoped to the wiring's own provides node, not "contains an opaque node anywhere" — naive itself contains the dep-free embedder-index node at opaque structural depth, and a whole-wiring exclusion would have made the default selector unable to resolve naive at all.
- [Phase 04]: 04-05: rest and uvicorn go under [project.optional-dependencies] (never [dependency-groups], which a pip install cannot reach externally); httpx joins the existing dev group. — Package legitimacy for fastapi/uvicorn/httpx confirmed by the developer 2026-09-06 (04-CHECKPOINT-ANSWERS.md). A PEP 735 dependency group is not pip-installable by an external consumer, which would make EMBED-02's "optional layer anyone can opt into" false in practice.
- [Phase 04]: 04-05: query_stream() shares query()'s identical _execute() path, yielding evidence events then one final event, rather than fabricating token-level LLM streaming. — The underlying scheduler produces one completed run, not incremental LLM tokens. D-16 only requires streamed content to assemble to the same answer/evidence the non-streaming endpoint returns, which this design proves without inventing streaming the execution model does not support.
- [Phase 04]: 04-05: EMBED-02 marked complete for its REST half only (FA-10) — the MCP transport is Deferred Idea API-07, out of this phase's scope. — Per the plan's own instruction to state the qualification in the SUMMARY rather than leave it unqualified. Dual-transport conformance is proven for REST vs in-process; a later phase shipping API-07 inherits the same thin-adapter invariant rather than a fresh design question.
- [Phase 05-opaque-side-admission]: UnadmittedOpaquePartError gates on Part.kind=='opaque', not structural_depth — Gating on structural_depth (as the plan's Task 2 action text literally said) would have broken registration of the already-shipped lightrag/embedder-index@0.1.0 (structural_depth=opaque, kind=embedder, no admission record); kind is what derive_execution_mode already keys its subprocess-placement decision on.

### Pending Todos

None yet.

### Blockers/Concerns

- **Ladder halt risk (Phase 2)**: a Falsifier 2 or Falsifier 5 failure halts the ladder outright — that is a SELECTION.md-level reversal, not a repairable defect. Phases 3-7 are conditional on Phase 2 passing.
- **Storage decomposition stall (Phase 3)**: research pitfall 1 — 17 node positions can look extracted while every node still reaches v1's singleton `shared_storage.py`. Per-node storage-ownership audit is a Phase 3 success criterion, not an afterthought.
- **Cozo 0.7.6 is architecture-frozen** with four known correctness bugs and no upstream fixes expected; pin and vendor the wheel (Phase 1).
- **Open research flags**: HippoRAG 2 porting scope (Phase 6 planning), graph-aware deletion semantics for shared entities (Phase 5 planning), sealed-set sizing/MDE (Phase 2 planning).

## Deferred Verification

| Phase | State | Resume |
|-------|-------|--------|
| 03 | verification_deferred_human | /gsd-verify-work 3 |

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-09-08T21:56:05.047Z
Stopped at: Completed 05-01-PLAN.md
Resume file: None

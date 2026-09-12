---
gsd_state_version: 1.0
milestone: v1.0
current_phase: 07
current_phase_name: Promotion & Rollback
status: executing
stopped_at: Completed 07-01-PLAN.md
last_updated: "2026-09-12T04:20:33.856Z"
last_activity: 2026-09-11
last_activity_desc: Phase 07 execution started
state_head: 8c38fd4f54417e9fc3bbcbfd1b615dde71114a65
progress:
  total_phases: 7
  completed_phases: 4
  total_plans: 61
  completed_plans: 59
milestone_name: milestone
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-29)

**Core value:** Modalities are swappable without consumers noticing — LightRAG and HippoRAG 2 both live behind one unchanging §18 envelope, comparable side-by-side on the rig.
**Current focus:** Phase 07 — Promotion & Rollback

## Current Position

Phase: 07 (Promotion & Rollback) — EXECUTING
Plan: 2 of 3
  drifted before this session — corrected here from find-phase's actual plan/summary counts
  rather than the stale auto-incremented value)
Status: Ready to execute
Last activity: 2026-09-11 — Phase 07 execution started

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 28
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 10 | - | - |
| 02 | 4 | - | - |
| 04 | 5 | - | - |
| 05 | 9 | - | - |

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
| Phase 05-opaque-side-admission P02 | 16min | 2 tasks | 4 files |
| Phase 05 P03 | 95min | 3 tasks | 15 files |
| Phase 05 P04 | 40min | 3 tasks | 13 files |
| Phase 05-opaque-side-admission P06 | 105min | 3 tasks | 9 files |
| Phase 05-opaque-side-admission P05 | 45min | 2 tasks | 2 files |
| Phase 05-opaque-side-admission P07 | 130min | 3 tasks | 14 files |
| Phase 06 P01 | continuation session | 3 tasks | 29 files |
| Phase 06 P02 | ~70min | 3 tasks | 9 files |
| Phase 06 P03 | 75min | 3 tasks | 15 files |
| Phase 06 P04 | ~65min | 3 tasks | 15 files |
| Phase 06 P05 | ~80min | 3 tasks | 11 files |
| Phase 06-hipporag-2-side-by-side P06 | ~20min (continuation) | 2 tasks | 8 files |
| Phase 06 P07 | ~90 min | 3 tasks | 15 files |
| Phase 06-hipporag-2-side-by-side P08 | ~55min | 3 tasks | 5 files |
| Phase 06-hipporag-2-side-by-side P09 | ~70min | 3 tasks | 10 files |
| Phase 06 P10 | 80min | 3 tasks | 15 files |
| Phase 06-hipporag-2-side-by-side P11 | 8min | 1 tasks | 1 files |
| Phase 06 P12 | 24min | 2 tasks | 4 files |
| Phase 06-hipporag-2-side-by-side P13 | 42min | 2 tasks | 4 files |
| Phase 06-hipporag-2-side-by-side P14 | ~40min | 2 tasks | 5 files |
| Phase 06 P16 | 45min | 2 tasks | 2 files |
| Phase 06 P15 | ~55min | 1 tasks | 2 files |
| Phase 06 P17 | ~35min | 2 tasks | 4 files |
| Phase 07 P01 | ~55min | 3 tasks | 14 files |

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
- [Phase 05]: 05-02: MACH-04's five-engine survey list adopted as recommended (A2), provenance stated in the doc; DR-04/HARD-03 selected two-covering-rationale but selection_is_clean=false since covering 1's partial-coverage refusal is unimplemented and covering 2 (EvidenceRef) is missing all four ChunkRef members per FA-03.
- [Phase 05]: 05-03: widened corpus.py's document-id token regex to permit underscore (real v1 document ids contain it; no path-traversal risk) after the real-corpus delete test surfaced every real document id being refused by the prior hex-only pattern.
- [Phase 05]: 05-03: MACH-11 now distinguishes machine-observed store touches (TOUCH_KIND_OBSERVED) from node-reported ones (TOUCH_KIND_NODE_REPORTED) via NodeContext.record_store_touch, re-checked for the first time against a real (non-fixture) mutates_store part, lightrag/full-delete@0.1.0.
- [Phase 05]: 05-04: Checkpoint resolved — mcp 2.2.0 and python-multipart 0.0.32 both confirmed legitimate before either package was added to databasise/pyproject.toml (the research audit's [SUS] verdicts were download-count blind spots, not slopsquat signatures).
- [Phase 05]: 05-04: get_job_status/health/corpus_status/document_counts reach databasise.foreign.run_corpus_op directly, never through a registered Part/wiring/scheduler step — a bounded liveness/status read produces no evidence, mutates nothing, and declares no effect.
- [Phase 05]: 05-04: Fixed a real bug (Rule 1) in REST's page-cap refusal path — Page(limit=..., offset=...) constructed directly inside a route body gets its PageSizeExceededError wrapped by pydantic into a ValidationError Starlette's exception middleware cannot match against the registered SeamRefusalError handler (would have 500'd instead of 422'ing); added a small _checked_page helper that raises the refusal directly.
- [Phase 05-opaque-side-admission]: 05-06: mcp is imported lazily, function-scoped inside codebase_memory_mcp_adapter._run_with_session — never at module level, since the module is reached from default_registry() unconditionally, and a module-level import would fail nearly the entire test suite on a bare install with no extras.
- [Phase 05-opaque-side-admission]: 05-06: Every normalized item from codebase-memory-mcp is tier-capped below_T1 unconditionally, not per-call — this engine supplies neither recipe_at_version nor ordinal for any tool at all (no recipe concept anywhere in its model), so no item can ever reach full T1 ChunkRef coverage regardless of which tool or repository is used.
- [Phase 05-opaque-side-admission]: 05-06: CODEBASE_MEMORY_MCP_PART.effects gained mutates_store additively, keeping the pre-existing self_storage/fs over-declarations pinned by committed Falsifier-2 evidence — the discrepancy with PARTS.md ## §X's mutates_store-only declaration is recorded in ADMISSION-CODEBASE-MEMORY-MCP.md rather than silently resolved.
- [Phase 05]: 05-05: OPAQUE-BOUNDARY-RULE.md enumerates every across-boundary Part/AdmissionRecord field and driver-script protocol key; test_full_ingest_compat.py enforces it, pinning environment_hash structurally (not by literal digest) since that value legitimately drifts with a free v1/uv.lock bump.
- [Phase 05]: 05-07: databasise/tests/mcp/ carries no __init__.py and both new test files guard with try/import-databasise.mcp instead of pytest.importorskip("mcp") — a bare import mcp/importorskip can resolve to this project's own mcp/ package or the tests/mcp/ namespace-package shadow instead of skipping cleanly.
- [Phase 05]: 05-07: fixed a real regression this plan's own databasise/mcp/ package introduced into 05-06's pre-existing codebase_memory_mcp_adapter.py and its test files' bare importlib.util.find_spec("mcp") availability checks, via a shared shadow-safe resolver (databasise/foreign/_mcp_sdk_guard.py) that strips every sys.path entry resolving inside databasise/ (excluding the active venv) before resolving the real SDK.
- [Phase 06]: HippoRAG 2 tracer: igraph/numpy approved for core deps; ppr.py graph-store access corrected to a single namespaced store (no .select())
- [Phase 06]: 06-02: entity-fact-embed's fact vector metadata carries both chunk_ids and the fact's own entity refs (not just chunk_ids as the literal action text named) so reset-vector-join.py's existing fact.get("entities") read has something to consume. — 06-01's already-committed reset_vector_join.py reads fact.get("entities") off each scored fact item to accumulate phrase weight; omitting it from entity-fact-embed's own writes would leave that read with nothing real to consume.
- [Phase 06]: 06-02: registered wiring nodes carry no "note" field (WiringNode schema extra=forbid), unlike the illustrative docs/system-model/wirings/hipporag-base.json copy the plan's action text quotes from. — Copying the governing doc's "note" field into the registered wiring raised WiringRefusedError at parse time, cascading into two seam cross-modality tests; caught and fixed before landing.
- [Phase 06]: 06-03: capability-selector comparison-response keys join the caller's own requested values, in their own supplied order, with a module-constant separator (+) — Section 18.4 names no rendering rule for a multi-capability selector; this plan's own flagged assumption, declared as a module constant so a later change is one edit rather than a search.
- [Phase 06]: 06-03: added DuplicateComparisonKeyError so a selector-key collision refuses by name rather than silently collapsing two arms into one response entry — Required by Task 1's own action text (not covered by any of the seven named behavior tests) - a Rule 2 auto-fix for missing critical functionality, since a silent collapse is the same undistinguishable-partial-mapping failure the plan's unsatisfiable-selector rule already refuses against.
- [Phase 06]: 06-04: judge_instance recorded as an explicit 'unresolved' sentinel — no live judge call was made in this environment, and this project's own resolved-identity convention forbids substituting a plausible model string
- [Phase 06]: 06-04: eval-corpus query ids are offset-anchored (q{offset+i+1}) so the 30-question fixture shares no query id with the Phase 3 corpus's own q1/q2
- [Phase 06]: 06-05: synonymy-edges' num_new_chunks > 0 guard is read as entity-fact-embed's own entity count, not a literal chunk count — this node's sole dep carries no chunk-count field, and entity-fact-embed already short-circuits to zero entities exactly when upstream produced nothing new.
- [Phase 06]: 06-05: fact-edges/passage-edges declare effects=[] genuinely (not additively like chunk-embed/entity-fact-embed) — both bodies reach no store and no client at all; the graph write happens once, downstream, at graph-augment-persist.
- [Phase 06]: 06-05: the fact-chunk-association discrepancy between entity-fact-embed (06-02, writes chunk_ids to vector metadata) and reset-vector-join (06-01, reads a KV fact:<id> record no code writes) is explicitly left open — disposition determined (reset-vector-join's KV-read interface is authoritative; entity-fact-embed needs to also write the KV record) but not implemented, since neither file is in 06-05's own <files> scope. 06-07 is named as owner.
- [Phase 06-hipporag-2-side-by-side]: 06-06: Owner selected defer-run at Task 2's checkpoint — no real A/A calibration executes; Falsifier 5/MACH-03 recorded as BLOCKED, not passed or failed. — T0 (answer-level) blocked by bundle@v1's unresolved judge_instance; T1 (gold-passage) blocked by the unbudgetable cost of ingesting the 291-document eval-corpus through the opaque v1 full-ingest path. Two preconditions named for a future run.
- [Phase 06-hipporag-2-side-by-side]: 06-06: Task 3 adapted from a passing-verdict record to a BLOCKED record per the owner's explicit instruction — an authorized deviation, not an executor judgment call. — The plan's literal Task 3 text assumed two committed calibration results existed to compare; none exist under defer-run, so the findings table instead carries one row per blocker and the record states plainly that no floor value is reported.
- [Phase 06]: 06-07: the zero_surviving_facts_dpr_fallback guard is declared on fact-filter's own config.guards (declare_guard's real shape: name/evaluating_node/value_when_not_fired/granularity), never the illustrative doc's top-level richer-shaped guards array — runner/guards.py's own module docstring requires config.guards so config_hash covers the declaration. — The illustrative docs/system-model/wirings/hipporag-base.json's top-level guards array is evidence PARTS.md cites; it is never parsed by validator/parse.py or reached by runner/scheduler.py's per-node guard validation.
- [Phase 06]: 06-07: fact_filter.py's _GuardAwareResult (a dict subclass overriding __eq__/__ne__) lets a JSON-literal value_when_not_fired sentinel correctly express a per-query, data-dependent condition through evaluate_guards's whole-runtime-output `!=` comparison, without a second guard-evaluation mechanism. — This node's own items/tokens legitimately vary per query in both branches, so ordinary whole-dict equality could never match a static JSON value; dict's own C-level __ne__ slot does not fall back to a subclass __eq__ override, so both had to be defined explicitly.
- [Phase 06]: 06-07: entity-fact-embed now also writes a fact:<id> -> {chunk_ids} KV record (writes_kv effect added), closing the two-plan-old gap between reset-vector-join's already-committed KV read and entity-fact-embed's vector-metadata-only write. — 06-05-SUMMARY.md's own "Next Phase Readiness" section disposed this gap explicitly to 06-07 as owner, since a real end-to-end run needs the write and neither 06-01 nor 06-05's own <files> scope touched the file that needed it.
- [Phase 06-hipporag-2-side-by-side]: 06-08: Owner selected defer-and-record-blocked at Task 1's spend checkpoint — no real HippoRAG index build or cross-modality comparison executes; both build_hipporag_index.py and run_cross_modality.py are written as genuine runnable code and committed unexecuted; MODAL-05 recorded as BLOCKED in CROSS-MODALITY-EVIDENCE.md, mirroring FALSIFIER-5-EVIDENCE.md's house format. — One real invocation requires live v1/.env.parity credentials and was not authorized during this plan's execution; MODAL-05 stays Pending in REQUIREMENTS.md.
- [Phase 06-hipporag-2-side-by-side]: [Phase 06-hipporag-2-side-by-side]: 06-09: F-07/MACH-10 discharged for both real registered mutable-store components (codebase-memory-mcp@0.1.0, lightrag/full-delete@0.1.0 -- a fourth component MODEL-RED-TEAM.md's own roster never named) via permanent-exclusion, enforced as MutableStoreComparisonExcludedError in Databasise.compare(). MACH-10 stays Pending in REQUIREMENTS.md pending the owner's own confirmation of the codebase-memory-mcp disposition (Task 1's human-check) -- no requirements.mark-complete call was made.
- [Phase 06]: 06-10: ingest becomes a real two-arm wiring (all seven HippoRAG index-side positions already exist), delete becomes a named refusal (no HippoRAG delete node exists anywhere in the repo) — Matches the plan's own objective split: build only what the existing node inventory can honestly support, never a delete wiring needing new node code
- [Phase 06]: 06-10: MODAL-05 stays Pending in REQUIREMENTS.md — this plan closes the structural write-surface gap (Gap 1(a)) but explicitly does not perform the real cross-modality run (Gap 1(b)), which is 06-13's own blocking checkpoint — The plan's own objective names Gap 1(b) as explicitly out of scope; marking MODAL-05 complete here would overclaim
- [Phase 06]: 06-11: MACH-10 flipped Pending -> Complete in REQUIREMENTS.md, citing 06-UAT.md Test 1 owner confirmation and F-07-MUTABLE-STORE-DISPOSITION.md — Appended a new dated confirmation annotation rather than rewriting the existing 06-09 measurement annotation, preserving the row's full history; MACH-03 and MODAL-05 left unchanged and Pending.
- [Phase 06]: 06-12: gsd_run check tdd-red-evidence cannot classify pytest output for this Python project (TAP/Node-oriented) — RED evidence produced via the commit-broken-draft-then-restore technique 06-01/06-04 already established, verified manually against real pytest AssertionErrors.
- [Phase 06]: 06-12: corpus_ingest.py's real --spend path uses its own dedicated store root (v1/.eval_corpus_store, workspace eval-corpus-ingest), separate from the Phase 3 parity store and the Phase 6 build-harness store.
- [Phase 06]: MODAL-05: owner approved the real cross-modality run; build_hipporag_index refused before completion on a fact-score empty-string defect. Real spend incurred, no comparison produced. MODAL-05 stays Pending against the concrete defect. — The plan's own stop-on-refusal rule forbids retrying with a weakened guard; the refusal itself is the honest recorded outcome.
- [Phase 06]: MACH-03/Falsifier 5: owner declined the A/A calibration spend a second time, reasoning the fact-score failure Task 1 just hit could waste the far larger T0-leg spend if not fixed first. — 06-12 closed both named preconditions; only the spend remains, and the owner is sequencing the defect fix ahead of it.
- [Phase 06]: 06-14: root cause was the harness calling load_wiring("hipporag") (the 13-node base wiring) for an index build instead of the already-committed 7-node corpus-ingest wiring; fact-score's empty deps let it dispatch query-side with no query ever injected, reaching the provider with an empty string — 06-10 had already built the correct index-side wiring; the harness simply never used it — fixed by generalizing load_wiring with a variant keyword and swapping the harness's own load call, not by patching fact_score.py
- [Phase 06]: 06-14: added EmptyEmbeddingInputError as one guard at OpenAICompatibleClient.embed, the single method all seven embedding call sites route through, rather than per-call-site guards — three other query-side call sites carry the same unguarded str(config.get("query", "")) pattern for legitimate query-time dispatch; a guard at the shared method turns every one into a diagnosable local refusal instead of a live provider 400
- [Phase 06]: [Phase 06-hipporag-2-side-by-side]: 06-16: Finished an interrupted prior executor's uncommitted-but-complete aa_run.py draft. Fixed the one blocking defect (a del StaleNullError line referencing a name never imported, raising NameError at import time) after confirming calibrate_family never calls floor_for so StaleNullError genuinely cannot fire in this module. All 13 planned tests already present and passing; full suite 960 passed/3 skipped. MACH-03 stays Pending per the plan's own prohibition.
- [Phase 06]: 06-15: owner re-authorized the real cross-modality run (approve); both build_hipporag_index and run_cross_modality exited 0 against live parity credentials, discharging MODAL-05. — 06-14's corpus-ingest wiring-variant fix and EmptyEmbeddingInputError guard closed the fact-score empty-string defect that killed the 2026-09-10 attempt; both harnesses ran clean this time with no retry needed.
- [Phase 06]: [Phase 06-hipporag-2-side-by-side]: 06-17: Owner declined the real A/A calibration spend a third time (06-06, 06-13, 06-17), no free-text reason given beyond the selection. Every precondition and the A/A driver itself are closed; only the spend decision remains, and per the plan's own prohibition it is not to be asked again.
- [Phase 06]: [Phase 06-hipporag-2-side-by-side]: 06-17: Appended a dated correction note to 06-VERIFICATION.md naming which later commits (5827165, 2cb437a, 3de871b, 06-14) closed five of its findings, without touching its status/score/gap bodies -- a pure append, verified via git diff --numstat (41 insertions, 0 deletions).
- [Phase 07]: 07-01: trace-id -> arm-name resolution matches on the dispatched node id set, not wiring_id/arm_id (both constant literals across every LightRAG arm) — the plan's literal field description does not survive contact with the real RunRecord shape. — wiring_id is the shared 'lightrag-base' string and arm_id is always the literal 'seam' for every LightRAG arm; only the persisted node id set (RunRecord.nodes[*].node_id) is both query-invariant and unique per arm.
- [Phase 07]: 07-01: the whole ledger read-modify-append sequence inside promote() runs in one run_in_executor call, never split across the calling thread and the executor thread. — sqlite3 forbids cross-thread use of a connection opened on a different thread; opening Ledger() on the event loop thread and calling append() from run_in_executor raised sqlite3.ProgrammingError.

### Pending Todos

None yet.

### Blockers/Concerns

- **Ladder halt risk (Phase 2)**: a Falsifier 2 or Falsifier 5 failure halts the ladder outright — that is a SELECTION.md-level reversal, not a repairable defect. Phases 3-7 are conditional on Phase 2 passing.
- **Storage decomposition stall (Phase 3)**: research pitfall 1 — 17 node positions can look extracted while every node still reaches v1's singleton `shared_storage.py`. Per-node storage-ownership audit is a Phase 3 success criterion, not an afterthought.
- **Cozo 0.7.6 is architecture-frozen** with four known correctness bugs and no upstream fixes expected; pin and vendor the wheel (Phase 1).
- **Open research flags**: HippoRAG 2 porting scope (Phase 6 planning), graph-aware deletion semantics for shared entities (Phase 5 planning), sealed-set sizing/MDE (Phase 2 planning).
- **Phase 6→7 gate deferral (2026-09-11)**: MACH-03 deferred a fourth time to the first gate-adjudicated promotion (outside this milestone under MACH-09); MODAL-01's two owner items deferred to the parity claim. Phase 7 authorised to start; Phase 6 stays `gaps_found`, Phase 3 stays `human_needed`; milestone cannot close until both discharged. Record: `.planning/phases/06-hipporag-2-side-by-side/06-GATE-AMENDMENT.md`.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Record Phase 6→7 gate deferral (MACH-03, MODAL-01) | 2026-09-11 | e64c694 | .planning/quick/260911-e7a-record-phase-6-to-7-gate-deferral/ |

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

Last session: 2026-09-12T04:20:18.990Z
Stopped at: Completed 07-01-PLAN.md
Resume file: None

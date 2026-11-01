---
phase: 12-hipporag-fixes
verified: 2026-11-01T07:22:23Z
status: passed
score: 5/5 roadmap success criteria verified (19/19 HIPP requirements satisfied in code)
covered_files:
  - ".planning/phases/12-hipporag-fixes/12-01-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-01-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-02-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-02-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-03-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-03-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-04-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-04-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-05-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-05-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-06-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-06-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-07-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-07-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-08-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-08-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-09-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-09-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-10-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-10-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-11-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-11-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-12-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-12-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-13-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-13-SUMMARY.md"
  - ".planning/phases/12-hipporag-fixes/12-14-PLAN.md"
  - ".planning/phases/12-hipporag-fixes/12-14-SUMMARY.md"
  - "databasise/evidence/HIPPORAG-PORT-RECORD.md"
  - "databasise/foreign/v1_corpus_adapter.py"
  - "databasise/mcp/server.py"
  - "databasise/mcp/tools.py"
  - "databasise/parts/registry.py"
  - "databasise/parts_core/hipporag/__init__.py"
  - "databasise/parts_core/hipporag/assemble_result.py"
  - "databasise/parts_core/hipporag/chunk_embed.py"
  - "databasise/parts_core/hipporag/document_remover.py"
  - "databasise/parts_core/hipporag/dpr_fallback.py"
  - "databasise/parts_core/hipporag/entity_fact_embed.py"
  - "databasise/parts_core/hipporag/fact_edges.py"
  - "databasise/parts_core/hipporag/fact_filter.py"
  - "databasise/parts_core/hipporag/fact_score.py"
  - "databasise/parts_core/hipporag/graph_augment_persist.py"
  - "databasise/parts_core/hipporag/openie.py"
  - "databasise/parts_core/hipporag/passage_edges.py"
  - "databasise/parts_core/hipporag/ppr.py"
  - "databasise/parts_core/hipporag/qa.py"
  - "databasise/parts_core/hipporag/reset_vector_join.py"
  - "databasise/parts_core/hipporag/synonymy_edges.py"
  - "databasise/runner/scheduler.py"
  - "databasise/runner/trace.py"
  - "databasise/seam/engine.py"
  - "databasise/seam/promotion.py"
  - "databasise/seam/refusals.py"
  - "databasise/seam/rest.py"
  - "databasise/seam/selectors.py"
  - "databasise/seam/tokens.py"
  - "databasise/stores/probes.py"
  - "databasise/stores/vector.py"
  - "databasise/wirings/hipporag/base.json"
  - "databasise/wirings/hipporag/corpus-delete.json"
  - "databasise/wirings/hipporag/corpus-ingest.json"
  - "databasise/wirings/resolve.py"
covered_digest: "v3:sha256:d8678c56d3f79d56aa213091bc808c5c6d718309101b581b27a40093c1425d0a"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
deferred:
  - truth: "HippoRAG empty-namespace pre-check (D-15): a query on a never-populated hipporag-chunks is refused with EmptyNamespaceError like LightRAG"
    addressed_in: "Phase 13 (WIRE-02)"
    evidence: "12-CONTEXT.md D-15 and Deferred section: no HIPP row requires it; it would change what protected test_ingest_abort.py (STOR-06) asserts. Revisit with WIRE-02."
---

# Phase 12: HippoRAG Fixes Verification Report

**Phase Goal:** HippoRAG ingests build a graph whose evidence resolves and accumulates correctly, its queries run only query-side work, and its documents have the same corpus lifecycle as LightRAG's
**Verified:** 2026-11-01T07:22:23Z
**Status:** passed
**Re-verification:** Yes, after covered files moved (Phases 13-16 edited 18 covered files; 2026-11-01 audit fixes edited 5 more). Prior status passed; no gaps carried.

## Goal Achievement

### Re-verification Note

Phases 13-16 edited 18 covered files (scheduler guard-signal reads, wiring `resolve.py`/`base.json` arm data, registry admission, selectors, refusals, `stores/probes.py`, `stores/vector.py`, `assemble_result.py`, `fact_filter.py`). Each Phase 12 claim was re-checked against current code: `without_recipe_only_nodes` still prunes the engine query run (`engine.py:2554`), selector union and promotion (`promotion.py:136`); `scheduler.py:849` still sets `degraded` on any fired guard with a node-free reason; `assemble_result.py:55-64` still drops zero-score PPR items and cuts to `top_k` (validated >= 1); `trace.py:84` `sum_token_accountings` is still the single helper used by `openie.py` and `entity_fact_embed.py`; `base.json` still lists `fact-filter` and `qa` in `consumes_query`, `max_concurrency: 4`, and declares the guard `signal` keys (`guard_fired`, `dpr_stand_in`) that `fact_filter.py` and `assemble_result.py` emit; none of the removed dead config keys is back; the Phase 13 WIRE-08 guard-signal change is backed by code on both sides. Requirements table now shows all 19 HIPP rows Complete (the earlier bookkeeping item is resolved).

### Re-verification 2026-11-01 (audit fixes)

Trigger: staleness trip after the 2026-11-01 debugging and security battery (base 3aafcc62, 50 commits). Of the 63 covered files, 5 changed: `seam/engine.py`, `seam/refusals.py`, `seam/rest.py`, `seam/selectors.py`, `stores/probes.py`. `runner/scheduler.py` is net unchanged (`git diff 3aafcc62 HEAD -- databasise/runner/scheduler.py` is empty: the e682f687 trace scrub was reverted in 3500f131, so D-11 node fault cause redaction is the pre-fix behaviour and `scheduler.py:849` is as cited). No HippoRAG part, wiring, trace, promotion, token, vector or MCP file moved.

What changed and what it touches here:
- `refusals.py` (5c00aabc, 13fda6a6, 7a07da50): new `json_safe`/`bounded_echo` helpers (ECHO_LIMIT 200, ECHO_ITEMS 20), new `NonEncodableTextError` (422, `field` attribute) and `require_encodable`. `ForeignEngineRefusalError` is unchanged: `failure_class` mapping `ExtractionFailedError -> ExtractionFailed`, closed reason codes, public `failed_chunks`/`failure_reasons`, private `_node_id` behind the `node_id` property (truth 3, HIPP-03/04/10).
- `rest.py`: `_status_for` unchanged (StoreBusy 409; ForeignEngineRefusal 503/502; not-found 404; else 422), so the HIPP-03 exception (REST 502 for a failed ingest) still holds. The only behaviour change is the schema-422 handler no longer echoing `input`/ctx; no HippoRAG route or body field changed.
- `engine.py`: `require_encodable` on alias/trace_reference/trace_ids/version, `CanonicalisationError` surfaced as `NonEncodableTextError(field="text")` before dispatch, `OverflowError` added to the store-fault excepts on `/corpus` and `/traces` paging, `log_tail` bounds `limit` with `PageBoundsError`, `_v1_row_track_id` moved off the loop thread. The query-run pruning call moved to `engine.py:2166` (`run = without_recipe_only_nodes(wiring)`) and the recipe-pruned dispatch to `engine.py:2554`; health namespace table (`engine.py:432-433`) still lists `hipporag-graph`, `hipporag-chunks`, and the kv `hipporag-text-chunks` (truth 5, HIPP-15).
- `selectors.py` (7a07da50): one added `require_encodable` per selector member before the instance-hash check; the effect union over `without_recipe_only_nodes` is now at `selectors.py:192` (truth 4, HIPP-12).
- `stores/probes.py` (4bfdb8db): `probe_kv` opens plain `mode=ro` when both `kv.sqlite3-wal` and `-shm` exist, `immutable=1` otherwise; the health states and the probed namespaces are unchanged (truth 5).

Targeted tests re-run at HEAD, all green: `tests/parts_core/hipporag` + `tests/runner/test_token_sum.py` + `tests/parts/test_registry.py` + `tests/evidence/test_hipporag_port_record.py` (114 passed); the five `tests/seam/test_hipporag_*.py` + `test_extraction_failed_refusal.py` + `test_ingest_abort.py` (57 passed); `tests/stores/test_probe_hardening.py` + `test_probe_kv_live_writer.py` + `tests/seam/test_health_probe.py` + `test_health_honesty.py` (34 passed); `tests/runner/test_degraded_on_guard.py` + `tests/seam/test_cross_modality_run.py` + `test_foreign_engine_refusal.py` (20 passed); `tests/foreign/test_secret_redaction.py` + `tests/wirings/test_query_run_pruning.py` (22 passed). Named refusals keep their names and status codes, no new unvalidated input path was introduced (the fixes only add validation), and the store lifecycle truths hold. Goal still achieved; status stays passed. Line citations in the tables below were updated to HEAD; no other content changed.

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After a real ingest, a PPR-path query returns non-empty hydrated content and every ref resolves; passage vertices get non-zero reset weight; fact-filter prompt contains the query; every chunk has a passage vertex even with no triples | VERIFIED | Bare chunk sha is the one id form: `chunk_embed.py:89` mints it, `ppr.py` strips the `chunk:` prefix on readback (`name[len(CHUNK_VERTEX_PREFIX):]`), `reset_vector_join.py` adds the prefix only when keying passage weights; one `CHUNK_VERTEX_PREFIX` constant in `entity_fact_embed.py:300`. `passage_edges.py` emits a `vertices` entry per chunk from openie's `chunks` passthrough and `graph_augment_persist.py` upserts that stream. `test_a_ppr_branch_query_hydrates_content_and_every_ref_resolves` passes with `guards_fired == []` on fact-filter (PPR branch actually taken), all refs resolving. `base.json` `consumes_query` lists `fact-filter`; `test_fact_filter_prompt_carries_the_query_between_the_markers` passes for two queries. |
| 2 | Graph accumulates across ingests: synonymy edge appears on the introducing ingest and is not re-emitted; co-occurrence follows the merge rule; facts keep the union of chunks; token accounting never mixes counters | VERIFIED | Own two-ingest probe through the real engine: edge `entity:ed wood`-`entity:films` carries `cooccurrence_by_chunk` with both chunk ids (1.0 each), `edge_types` `["fact-cooccurrence","synonymy"]`, `weight` 3.0 (2 co-occurrence + 1 synonymy); KV `fact:<id>` holds both chunk ids; `doc:d1` manifest holds chunk/fact/entity ids. `synonymy_edges.py` matches only `new_entities` via `self_knn(ids=...)` which searches staged vectors (`stores/vector.py:436-465`). `runner/trace.py:66` `sum_token_accountings` returns the unbudgetable sentinel on mixed labels; the duplicated `_sum_token_accountings` is gone (grep finds none); `openie.py` and `entity_fact_embed.py` import the shared helper. |
| 3 | A failed ingest commits nothing and its refusal names the failing node and real exception; per-chunk OpenIE failures counted and reported; bounded concurrency | VERIFIED | `test_an_ingest_with_no_embedding_client_names_chunk_embed_privately` (node_id == "chunk-embed", cause ClientNotWiredError naming embedding, node absent from `str(refusal)` and body) and `test_an_ingest_with_no_llm_client_refuses_and_commits_nothing` (zero vectors, zero KV rows, empty graph, no query evidence) pass. Own probe with an LLM that returns junk and raises: refusal `ExtractionFailed`, `failed_chunks=3`, `failure_reasons=['unparseable_response','llm_call_failed:RuntimeError','unparseable_response']`, no raw text or key in `str(exc)`. `openie.py` gathers all chunks under the scheduler semaphore; `base.json` and `corpus-ingest.json` set `max_concurrency: 4`. |
| 4 | A query runs only query-side nodes, embeds once, returns at most top_k non-zero-score items, carries an answer unlike the joined evidence, and the non-debug envelope shows the fallback | VERIFIED | `without_recipe_only_nodes` (`wirings/resolve.py`) prunes to ancestors of `provides`; used by the engine run (`engine.py:2166`), selector effect union (`selectors.py:192`) and promotion (`promotion.py:136`). `test_a_query_runs_only_query_side_nodes_and_embeds_once`: node set equals the 7 query-side nodes, embed calls `[["What did Ed Wood direct?"]]`, `writes_graph` selector no longer resolves to hipporag. `qa` is the 14th node and sole `provides`; `test_the_answer_is_generated_text_not_the_joined_evidence` asserts the answer is `low-budget films`, not the joined evidence. `assemble_result.py` cuts to `config.top_k` (default 5) after branch selection and drops zero-score PPR items; `test_a_query_returns_at_most_top_k_items_on_both_branches` over 20 documents passes. `scheduler.py:849` sets `degraded = partial or any(guards_fired)`; `test_a_fired_fallback_is_degraded_with_a_node_free_reason_and_ppr_is_not` asserts `(degraded, partial) == (True, False)` on the non-debug envelope with reasons free of node and guard names. |
| 5 | Full document lifecycle: jobs, /corpus, /corpus/counts, /health cover HippoRAG; delete removes records; re-ingest leaves no stale chunks; old refs never resolve silently to new text; every config key and docstring claim backed by code | VERIFIED | `test_hipporag_documents_appear_in_jobs_corpus_counts_and_health` (GET /jobs/{id} terminal `processed`; /corpus and /corpus/counts list and count from the `doc:` manifest under a HippoRAG selector; /health lists `kv:hipporag-text-chunks`, `graph:hipporag-graph`, `vector:hipporag-chunks`). `document_remover.py` + `corpus-delete.json` + remover as first node of `corpus-ingest.json`; `test_a_hipporag_delete_removes_the_document_and_a_second_delete_is_not_found`, `test_reingest_leaves_no_stale_chunk_and_delete_removes_everything`, `test_reingesting_a_document_keeps_its_synonymy_edges` pass. Chunk id is `sha256(document_id:ordinal:text)`; `test_an_old_ref_never_resolves_to_the_new_text_after_reingest` and `test_identical_text_in_two_documents_gets_two_chunk_ids` pass. `base.json`/`corpus-ingest.json` carry none of the removed dead keys (`namespaces`, synonymy `guard`, `socket_shape`, `arm_precedence`, `apportionment_policy`, `readback`, `order_policy`); no "no token spend" or "auditable" claim remains in the parts. |

**Score:** 5/5 roadmap truths verified, 0 behavior-unverified.

### Requirements Coverage

All 19 IDs appear in PLAN frontmatter (01: HIPP-01/02; 02: 06/19; 03: 07/08; 04: 09/10; 05: 05/12; 06: 16; 07: 12; 08: 16/17; 09: 15; 10: 13; 11: 11; 12: 14; 13: 18; 14: 03/04). No orphaned HIPP IDs in REQUIREMENTS.md.

| Requirement | Status | Evidence |
|-------------|--------|----------|
| HIPP-01 | SATISFIED | bare chunk id; ppr readback strips prefix; PPR-branch resolve test |
| HIPP-02 | SATISFIED | `reset_vector_join.py` keys `chunk:`+id, equal to graph vertex names; row check plant killed (2bc642e) |
| HIPP-03 | SATISFIED (exception: REST 502 not 422, recorded in REQUIREMENTS.md) | no-llm ingest test: zero records, no evidence |
| HIPP-04 | SATISFIED (exception: private `node_id`, recorded) | `getattr(caught,"node_id")=="chunk-embed"`, cause ClientNotWiredError |
| HIPP-05 | SATISFIED | `consumes_query` includes fact-filter and qa; prompt test |
| HIPP-06 | SATISFIED | vertices stream; chunk with no triples still gets a vertex |
| HIPP-07 | SATISFIED | `self_knn(ids=...)` over staged+committed; new-entities-only |
| HIPP-08 | SATISFIED | probe output above (sum by chunk, type union, synonymy max) |
| HIPP-09 | SATISFIED | probe: `fact:<id>` holds both chunk ids; same union mirrored into fact vector metadata (`entity_fact_embed.py:336-342,388`) |
| HIPP-10 | SATISFIED (exception: refusal outcome, recorded) | probe above; `test_extraction_failed_refusal.py` passes |
| HIPP-11 | SATISFIED | top_k=5 in `base.json`; top_k test both branches |
| HIPP-12 | SATISFIED | pruned run, selector union, one embed |
| HIPP-13 | SATISFIED | `qa` node; answer test |
| HIPP-14 | SATISFIED | degraded without partial on non-debug envelope |
| HIPP-15 | SATISFIED (exception: tests in write-path file, recorded) | jobs/corpus/counts/health test |
| HIPP-16 | SATISFIED | delete and re-ingest tests |
| HIPP-17 | SATISFIED (exception: id hashes document id too, recorded) | old-ref and twin-text tests |
| HIPP-18 | SATISFIED | keys removed; allowlist test of read keys (`test_review_fixes.py`) |
| HIPP-19 | SATISFIED | shared `sum_token_accountings`; `tests/runner/test_token_sum.py` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| HippoRAG part tests + token-sum | pytest `tests/parts_core/hipporag tests/runner/test_token_sum.py` (re-run 2026-10-31) | 98 passed | PASS |
| HippoRAG seam tests (corpus surface, query path, review fixes, write gate, write path) | pytest the five `tests/seam/test_hipporag_*.py` | 43 passed | PASS |
| Refusal/abort, registry, port record, redaction, degraded-on-guard, cross-modality, foreign refusal, query-run pruning | pytest `test_extraction_failed_refusal`, `test_ingest_abort`, `test_registry`, `test_hipporag_port_record`, `test_secret_redaction`, `test_degraded_on_guard`, `test_cross_modality_run`, `test_foreign_engine_refusal`, `test_query_run_pruning` | 32 + 58 passed | PASS |
| 2026-11-01 audit re-run: all of the above plus `tests/stores/test_probe_hardening.py`, `test_probe_kv_live_writer.py`, `tests/seam/test_health_probe.py`, `test_health_honesty.py` | pytest, five targeted groups at HEAD | 114 + 57 + 34 + 20 + 22 = 247 passed | PASS |
| Full offline suite | not run by this re-verification (orchestrator runs it as the regression gate) | n/a | SKIPPED |

Initial verification (2026-10-19) additionally ran a two-ingest scratch probe through the real engine and the full suite (2203 passed); those results are not re-run here.

### Probe Execution

Step 7c: SKIPPED. No `probe-*.sh` is declared by any Phase 12 PLAN or SUMMARY.

### Anti-Patterns Found

No TBD/FIXME/XXX marker in any Phase 12 implementation file. The code review (12-REVIEW.md, 3 iterations) closed with 0 critical, 0 warning and 15 info findings, all advisory; ten critical/warning findings from iterations 1-2 were fixed in 26ca959, f4ef3ba, 27dd16d, 25ea962, e869d26, 76441a9, 0d42188, edd4883, e85c3fc.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `databasise/parts_core/hipporag/chunk_embed.py` | 89 | chunk-id preimage `document_id:ordinal:text` is ambiguous if a document id contains `:` | Info (IN-04) | Engine refuses `:` in document ids, so unreachable through the seam |
| `databasise/runner/trace.py` | 66-80 | a `"none"`-labelled accounting with non-zero counts is merged under another label | Info (B-IN-03) | Needs a buggy client; not reachable by shipped parts |
| `databasise/parts_core/hipporag/openie.py` | 202-204 | fallback semaphore accepts 0 on a hand-built context | Info (IN-05) | Scheduler validates the real path |

### Human Verification Required

None blocks the phase. Items already flagged by the review as owner-run, carried in `.planning/TESTING-PLAN.md` per owner policy (no live runs during build), treated as documented deferrals and not gaps:

1. Real-provider qa answer quality and per-query cost (HIPP-13, price against RIG F3).
2. Real-provider `unparseable_response` rate per corpus (IN-07; D-08 raises the refusal rate with real models).
3. Three lax assertions in protected `test_hipporag_write_path.py` (310-316, 394-399) and `test_hipporag_query_path.py` (230-240) remain; strict replacements exist in `test_hipporag_review_fixes.py`. Tightening them needs the owner's `grant-check-edit` (B-IN-08).

### Gaps Summary

No goal-blocking gap. The earlier bookkeeping item is resolved: `.planning/REQUIREMENTS.md` marks all 19 HIPP requirements checked and Complete. The five Phase 12 exception clauses (HIPP-03/04/10/15/17) are present in REQUIREMENTS.md (lines 273, 278, 299, 320, 329).

The deferred D-15 (HippoRAG empty-namespace pre-check) is an owner-recorded deferral to Phase 13 (WIRE-02) and no HIPP row requires it.

---

_Verified: 2026-11-01T07:22:23Z_
_Verifier: Claude (gsd-verifier)_

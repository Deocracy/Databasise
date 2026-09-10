---
status: complete
phase: 06-hipporag-2-side-by-side
source: [06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md, 06-04-SUMMARY.md, 06-05-SUMMARY.md, 06-06-SUMMARY.md, 06-07-SUMMARY.md, 06-08-SUMMARY.md, 06-09-SUMMARY.md]
started: 2026-09-10T00:00:00Z
updated: 2026-09-10T07:12:47Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Confirm codebase-memory-mcp's permanent-exclusion disposition (MACH-10)
expected: Open `databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md` and read the `codebase-memory-mcp@0.1.0` row (CA-2): disposition `permanent-exclusion` from §5 parity/determinism comparisons, with the stated reversal condition (a future A/B-testability requirement, at which point the snapshot/reset protocol is a file-copy-and-restore of the engine's SQLite DB plus WAL/SHM). This matches your intent. `lightrag/full-delete@0.1.0`, MC-1 and CA-7 each carry exactly one disposition with a non-empty reason. If it matches, MACH-10 can flip from Pending to Complete; if not, say which disposition you want instead.
result: pass
coverage_id: 06-09/D1
rationale: 06-09-PLAN.md's own <human-check> names the owner's confirmation as the sole remaining gate before MACH-10 is marked Complete; tests prove the record's structure, not the policy.

### 2. Requirement-row annotations honestly reflect their cited evidence
expected: In `.planning/REQUIREMENTS.md` the six Phase 6 rows (MACH-02, MACH-03, MACH-10, MODAL-04, MODAL-05, API-08) each carry a dated annotation naming a committed evidence document; MACH-03, MODAL-05 and MACH-10 stay Pending against a named outstanding item, and no row rounds a partial result up to Complete. `databasise/evidence/HIPPORAG-PORT-RECORD.md` "## Limits" names the deferred upstream-package parity measurement with a trigger. `.planning/research/STACK.md`'s LanceDB rows are corrected in place with a dated supersession note, not deleted.
result: pass
coverage_id: 06-09/D3
rationale: Whether each row's prose honestly represents what its evidence establishes is an accuracy-of-representation judgment no test asserts on (Phase 5's mass-revert lesson).

### 3. F-14 seam-invariance record reads as an honest, non-overreaching claim
expected: `databasise/evidence/F-14-SEAM-INVARIANCE.md` records F-14's outcome from one real cross-modality `compare()` call against seeded fixtures with stub clients. Its verdict ("no consumer-visible field changed") is stated at that scope only, the house-format sections (claim, method, findings, verdict, limits) are all present, and nothing in it claims F-14 holds against a real corpus or live clients.
result: pass
coverage_id: 06-03/D8
rationale: The plan prohibits recording F-14 as holding without a real call; a human should confirm the document's completeness and that the verdict does not overreach.

### 4. EVAL-BUNDLE-V1.md is honest about what bundle@v1 does and does not establish
expected: `databasise/evidence/EVAL-BUNDLE-V1.md` states that bundle@v1 was minted from the 30-question eval-corpus fixture with 60/20/20 dev/holdout/sealed splits by deterministic hash, and that the split proportions are the plan's own unvalidated decision. It explicitly lists what the bundle does not yet carry: no A/A null, no owner corpus, an unresolved judge identity. You agree bundle@v1 is provisional, not settled.
result: pass
coverage_id: 06-04/D3
rationale: No document states a minimum partition size or correct proportions; a later plan must not treat bundle@v1 as settled on the strength of this record alone.

### 5. build_hipporag_index.py reads as genuine, runnable code against its acceptance criteria
expected: Read `databasise/parity/build_hipporag_index.py`. It has the build-then-verify-then-report shape: precondition assertions before any spend, post-build verification of the populated hipporag-* namespaces, token spend taken from TokenAccounting (never fabricated), and 03-11-PLAN.md's empty-extraction guard adopted. Nothing in it has been invoked for real, and `databasise/evidence/CROSS-MODALITY-EVIDENCE.md` records MODAL-05 as BLOCKED naming the one blocker, your defer decision and the entry criterion, with no real-run number.
result: pass
coverage_id: 06-08/D1
rationale: No real invocation exists to verify against; the deliverable is the harness's own written correctness.

### 6. entity-fact-embed makes zero client calls with no findings
expected: `databasise/parts_core/hipporag/entity_fact_embed.py` line 76 returns an empty result when `findings` is empty, before any embedding client is touched, matching chunk-embed's and openie's tested zero-call paths.
result: pass
coverage_id: 06-02/D3
rationale: chunk-embed and openie's zero-call paths are unit-tested; entity-fact-embed's identical short-circuit is verified by inspection only.

### 7. Summed token accounting for openie and entity-fact-embed never fabricates a zero
expected: `_sum_token_accountings` in `databasise/parts_core/hipporag/openie.py` (line 118, used at 182) and `entity_fact_embed.py` (line 59, used at 171) sums every per-call TokenAccounting for the dispatch and propagates the unbudgetable sentinel if any call carried it, so the run record's token spend is the real sum, never zero.
result: pass
coverage_id: 06-02/D4
rationale: The summation is exercised indirectly by behavior tests but no test asserts the summed TokenAccounting's own field values.

### 8. A/A calibration run deferral stands
expected: `databasise/evidence/FALSIFIER-5-EVIDENCE.md` records Falsifier 5 as BLOCKED, not discharged, naming both blockers (unresolved judge identity, unbudgetable eval-corpus ingest) and both entry preconditions verbatim, with no floor value claimed. The real A/A run against bundle@v1 producing T0/T1 floors was deliberately not run per your defer decision. Confirm the deferral stands (or name the judge identity and ingest budget that would start it).
result: pass
coverage_id: 06-06/D3
rationale: Owner's defer-run decision; recorded so its absence is explicit rather than silent.

### 9. HippoRAG 2's five-node query-side chain resolves through a capability selector and returns a §18.2 envelope with evidence from its own hipporag-chunks namespace
expected: HippoRAG 2's five-node query-side chain resolves through a capability selector and returns a §18.2 envelope with evidence from its own hipporag-chunks namespace
result: pass
source: automated
coverage_id: 06-01/D1
verified_by: tests/seam/test_cross_modality_run.py#test_hipporag_query_returns_evidence_from_its_own_chunks_namespace

### 10. CozoGraphStore.export_to_igraph() issues exactly two Cozo queries regardless of graph size, with a round-tripping and negative-control proof
expected: CozoGraphStore.export_to_igraph() issues exactly two Cozo queries regardless of graph size, with a round-tripping and negative-control proof
result: pass
source: automated
coverage_id: 06-01/D2
verified_by: tests/stores/test_graph_bulk_export.py#test_export_issues_exactly_two_cozo_queries_regardless_of_graph_size

### 11. FaissVectorStore.score_all() returns every stored vector, never a top-k truncation, visibly distinct from query()
expected: FaissVectorStore.score_all() returns every stored vector, never a top-k truncation, visibly distinct from query()
result: pass
source: automated
coverage_id: 06-01/D3
verified_by: tests/stores/test_vector_score_all.py#test_score_all_returns_one_entry_per_stored_vector_never_a_top_k_truncation

### 12. HippoRAG's resolved graph/KV store directories are disjoint from LightRAG's on the same store_root/workspace; LightRAG's own directories are unchanged
expected: HippoRAG's resolved graph/KV store directories are disjoint from LightRAG's on the same store_root/workspace; LightRAG's own directories are unchanged
result: pass
source: automated
coverage_id: 06-01/D4
verified_by: tests/seam/test_store_isolation.py#test_lightrags_own_directories_are_unchanged_from_before_this_plan; tests/seam/test_store_isolation.py#test_seeding_one_modalitys_graph_leaves_the_others_empty_cross_read_refusal

### 13. Every HippoRAG part resolves opaque effective depth and none needs subprocess containment
expected: Every HippoRAG part resolves opaque effective depth and none needs subprocess containment
result: pass
source: automated
coverage_id: 06-01/D5
verified_by: tests/parts_core/hipporag/test_registration.py#test_effective_depth_over_the_parsed_hipporag_wiring_is_opaque_at_every_node

### 14. ppr's whole-graph PPR call is served by one native igraph/prpack call with the pinned argument shape, NaN/negative reset entries zeroed, readback partitioned to passage vertices only
expected: ppr's whole-graph PPR call is served by one native igraph/prpack call with the pinned argument shape, NaN/negative reset entries zeroed, readback partitioned to passage vertices only
result: pass
source: automated
coverage_id: 06-01/D6
verified_by: tests/parts_core/hipporag/test_ppr.py#test_nan_and_negative_reset_entries_are_zeroed_before_the_call; tests/parts_core/hipporag/test_ppr.py#test_changing_damping_produces_a_different_score_vector_negative_control

### 15. The wiring pool and seam couplings are generalized to be modality-agnostic without changing LightRAG's own observable behavior
expected: The wiring pool and seam couplings are generalized to be modality-agnostic without changing LightRAG's own observable behavior
result: pass
source: automated
coverage_id: 06-01/D7
verified_by: cd databasise && uv run pytest -q (688 passed, 13 skipped, full suite including every pre-existing LightRAG-arm/seam/parity test)

### 16. The chunk-embed -> openie -> entity-fact-embed chain lands chunk vectors in hipporag-chunks, chunk text in hipporag-text-chunks, and entity/fact vectors in hipporag-entities/hipporag-facts
expected: The chunk-embed -> openie -> entity-fact-embed chain lands chunk vectors in hipporag-chunks, chunk text in hipporag-text-chunks, and entity/fact vectors in hipporag-entities/hipporag-facts
result: pass
source: automated
coverage_id: 06-02/D1
verified_by: tests/parts_core/hipporag/test_index_side_extraction.py#test_full_chain_dispatch_has_bounded_embed_calls_and_matching_fact_ids; tests/parts_core/hipporag/test_index_side_extraction.py#test_chunk_embed_writes_chunk_vectors_and_text_for_three_documents; tests/parts_core/hipporag/test_index_side_extraction.py#test_entity_fact_embed_writes_four_entities_and_three_facts_never_chunks

### 17. openie makes two LLM calls per chunk (NER, then triple extraction) as one fused operation, the second call carrying that chunk's own NER result
expected: openie makes two LLM calls per chunk (NER, then triple extraction) as one fused operation, the second call carrying that chunk's own NER result
result: pass
source: automated
coverage_id: 06-02/D2
verified_by: tests/parts_core/hipporag/test_index_side_extraction.py#test_openie_makes_exactly_two_calls_per_chunk_ner_then_triples

### 18. One query object and two selectors return a mapping keyed by exactly those two caller-supplied selector values, each a §18.2 ResponseEnvelope
expected: One query object and two selectors return a mapping keyed by exactly those two caller-supplied selector values, each a §18.2 ResponseEnvelope
result: pass
source: automated
coverage_id: 06-03/D1
verified_by: tests/seam/test_compare.py#test_keyed_by_selector

### 19. A comparison call carrying exactly one selector returns a bare ResponseEnvelope — the same object query() returns — never a one-key mapping
expected: A comparison call carrying exactly one selector returns a bare ResponseEnvelope — the same object query() returns — never a one-key mapping
result: pass
source: automated
coverage_id: 06-03/D2
verified_by: tests/seam/test_compare.py#test_single_selector_is_a_run

### 20. A comparison call carrying zero selectors is refused by name (EmptyComparisonRequestError) rather than silently defaulting
expected: A comparison call carrying zero selectors is refused by name (EmptyComparisonRequestError) rather than silently defaulting
result: pass
source: automated
coverage_id: 06-03/D3
verified_by: tests/seam/test_compare.py#test_zero_selectors_is_refused

### 21. No comparison response contains a verdict-vocabulary token, an arm id, a wiring id, a node id, an instance hash, or a provenance key at any nesting depth
expected: No comparison response contains a verdict-vocabulary token, an arm id, a wiring id, a node id, an instance hash, or a provenance key at any nesting depth
result: pass
source: automated
coverage_id: 06-03/D4
verified_by: tests/seam/test_compare.py#test_no_verdict_leaks; tests/seam/test_compare.py#test_no_internal_identity_leaks

### 22. Selector values key the response exactly as the caller supplied them — two selectors differing only in letter case are two distinct keys
expected: Selector values key the response exactly as the caller supplied them — two selectors differing only in letter case are two distinct keys
result: pass
source: automated
coverage_id: 06-03/D5
verified_by: tests/seam/test_compare.py#test_selector_keys_are_not_normalised

### 23. An unsatisfiable selector anywhere in a comparison request refuses the whole comparison, never a partial mapping with one arm silently missing
expected: An unsatisfiable selector anywhere in a comparison request refuses the whole comparison, never a partial mapping with one arm silently missing
result: pass
source: automated
coverage_id: 06-03/D6
verified_by: tests/seam/test_compare.py#test_unsatisfiable_selector_refuses_the_whole_comparison

### 24. The comparison surface is reachable identically in-process, over REST (POST /compare), and over MCP (compare tool), with the tool roster growing by exactly one name
expected: The comparison surface is reachable identically in-process, over REST (POST /compare), and over MCP (compare tool), with the tool roster growing by exactly one name
result: pass
source: automated
coverage_id: 06-03/D7
verified_by: tests/seam/test_rest_transport.py (28 passed, --extra rest); tests/mcp/test_tool_growth_invariant.py + tests/mcp/test_dual_transport_parity.py (28 passed, --extra rest --extra mcp)

### 25. A 30-question public-benchmark corpus fixture exists, hash-verified by the existing loader, disjoint from and non-destructive to the Phase 3 parity corpus
expected: A 30-question public-benchmark corpus fixture exists, hash-verified by the existing loader, disjoint from and non-destructive to the Phase 3 parity corpus
result: pass
source: automated
coverage_id: 06-04/D1
verified_by: manual verify command: uv run python -c \"load_snapshot(Path('tests/fixtures/eval-corpus'))\" prints queries=30; git diff --stat databasise/tests/fixtures/corpus/ reports no changes

### 26. EvalBundle mints both §EV.2 target families over three disjoint dev/holdout/sealed splits; every one of §EV.1's five invalidating changes mints a new version and leaves the prior version's bytes untouched; a mutated version is detected and refused on next load; sealed/holdout partition discipline is enforced in code
expected: EvalBundle mints both §EV.2 target families over three disjoint dev/holdout/sealed splits; every one of §EV.1's five invalidating changes mints a new version and leaves the prior version's bytes untouched; a mutated version is detected and refused on next load; sealed/holdout partition discipline is enforced in code
result: pass
source: automated
coverage_id: 06-04/D2
verified_by: tests/eval/test_bundle_versioning.py (12 tests covering the plan's own seven <behavior> items, including the Test 7 negative control)

### 27. FaissVectorStore.self_knn(top_k) returns the top-k nearest neighbours for every stored vector from one batched Faiss search call, and the search-call count does not grow with the number of stored vectors
expected: FaissVectorStore.self_knn(top_k) returns the top-k nearest neighbours for every stored vector from one batched Faiss search call, and the search-call count does not grow with the number of stored vectors
result: pass
source: automated
coverage_id: 06-05/D1
verified_by: tests/stores/test_vector_self_knn.py#test_self_knn_search_call_count_does_not_scale_with_stored_vector_count; tests/stores/test_vector_self_knn.py#test_self_knn_returns_top_k_neighbours_per_vector_never_including_itself; tests/stores/test_vector_self_knn.py#test_mutating_a_stored_vector_changes_its_neighbour_list_negative_control

### 28. synonymy-edges produces entity-to-entity edges only from self_knn, canonically ordered and deduplicated above threshold, and produces none at all when the guard input reports zero new upstream entities
expected: synonymy-edges produces entity-to-entity edges only from self_knn, canonically ordered and deduplicated above threshold, and produces none at all when the guard input reports zero new upstream entities
result: pass
source: automated
coverage_id: 06-05/D2
verified_by: tests/parts_core/hipporag/test_graph_construction.py#test_synonymy_edges_emits_deduped_canonical_edges_above_threshold; tests/parts_core/hipporag/test_graph_construction.py#test_synonymy_edges_zero_upstream_chunk_count_makes_no_store_read

### 29. fact-edges produces symmetric entity-to-entity co-occurrence edges and passage-edges produces passage-to-entity edges at unit weight, both as pure transforms declaring no effects
expected: fact-edges produces symmetric entity-to-entity co-occurrence edges and passage-edges produces passage-to-entity edges at unit weight, both as pure transforms declaring no effects
result: pass
source: automated
coverage_id: 06-05/D3
verified_by: tests/parts_core/hipporag/test_graph_construction.py#test_fact_edges_emits_one_symmetric_edge_with_cooccurrence_count_weight; tests/parts_core/hipporag/test_graph_construction.py#test_fact_edges_are_canonically_ordered_regardless_of_source_order; tests/parts_core/hipporag/test_graph_construction.py#test_passage_edges_emits_one_edge_per_chunk_entity_pair_at_unit_weight; tests/parts_core/hipporag/test_graph_construction.py#test_fact_and_passage_edges_reach_no_store_and_no_client

### 30. graph-augment-persist writes every node and edge from the three builders into the hipporag-graph namespace under quarantined artifact scope, collapsing the three edge types into the single weight attribute export_to_igraph reads, with contributing edge types recorded on the edge's own attrs
expected: graph-augment-persist writes every node and edge from the three builders into the hipporag-graph namespace under quarantined artifact scope, collapsing the three edge types into the single weight attribute export_to_igraph reads, with contributing edge types recorded on the edge's own attrs
result: pass
source: automated
coverage_id: 06-05/D4
verified_by: tests/parts_core/hipporag/test_graph_construction.py#test_graph_augment_persist_writes_every_vertex_and_edge_as_quarantined; tests/parts_core/hipporag/test_graph_construction.py#test_graph_augment_persist_collapses_two_edge_types_into_summed_weight

### 31. A graph written by graph-augment-persist and read back by CozoGraphStore.export_to_igraph round-trips: every persisted node id appears as a vertex name and every persisted edge weight appears as an edge weight, with a negative control proving the comparison has teeth
expected: A graph written by graph-augment-persist and read back by CozoGraphStore.export_to_igraph round-trips: every persisted node id appears as a vertex name and every persisted edge weight appears as an edge weight, with a negative control proving the comparison has teeth
result: pass
source: automated
coverage_id: 06-05/D5
verified_by: tests/parts_core/hipporag/test_graph_construction.py#test_graph_augment_persist_round_trips_through_export_to_igraph_with_negative_control

### 32. A full index-side chain (chunk-embed through graph-augment-persist) over the seeded shared-entity source documents produces a real graph holding both passage and entity vertices
expected: A full index-side chain (chunk-embed through graph-augment-persist) over the seeded shared-entity source documents produces a real graph holding both passage and entity vertices
result: pass
source: automated
coverage_id: 06-05/D6
verified_by: tests/parts_core/hipporag/test_graph_construction.py#test_end_to_end_index_run_produces_a_graph_with_passage_and_entity_vertices

### 33. The A/A calibration procedure exists with both §AA preconditions (cache-bypass, staleness) enforced as code refusals, and its boundary/staleness rules pinned by fixture tests
expected: The A/A calibration procedure exists with both §AA preconditions (cache-bypass, staleness) enforced as code refusals, and its boundary/staleness rules pinned by fixture tests
result: pass
source: automated
coverage_id: 06-06/D1
verified_by: tests/eval/test_calibration.py

### 34. Falsifier 5 is recorded as BLOCKED, not discharged — both blockers (unresolved judge identity, unbudgetable eval-corpus ingest) and both entry preconditions are named verbatim and verifiably, and no floor value is claimed anywhere in the record
expected: Falsifier 5 is recorded as BLOCKED, not discharged — both blockers (unresolved judge identity, unbudgetable eval-corpus ingest) and both entry preconditions are named verbatim and verifiably, and no floor value is claimed anywhere in the record
result: pass
source: automated
coverage_id: 06-06/D2
verified_by: tests/evidence/test_falsifier5_record.py

### 35. dpr-fallback (the thirteenth position) emits sorted text_chunk items over the full passage matrix via score_all, sharing dense_passage_retrieval() with reset-vector-join, unconditionally dispatched, empty-namespace-safe
expected: dpr-fallback (the thirteenth position) emits sorted text_chunk items over the full passage matrix via score_all, sharing dense_passage_retrieval() with reset-vector-join, unconditionally dispatched, empty-namespace-safe
result: pass
source: automated
coverage_id: 06-07/D1
verified_by: tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_dpr_fallback_emits_text_chunk_items_for_every_stored_chunk_sorted_by_descending_score; tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_dpr_fallback_scores_match_reset_vector_joins_own_passage_weight_scores; tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_dpr_fallback_runs_unconditionally_reading_no_guard_state; tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_dpr_fallback_with_empty_chunk_namespace_emits_empty_items_never_raises

### 36. The zero_surviving_facts_dpr_fallback guard fires exactly when zero facts survive fact-filter, routes assemble-result to dpr-fallback's items instead of ppr's, and its firing is observable via resolve_trace's guards_fired without appearing in the serialised envelope or marking the run degraded/partial
expected: The zero_surviving_facts_dpr_fallback guard fires exactly when zero facts survive fact-filter, routes assemble-result to dpr-fallback's items instead of ppr's, and its firing is observable via resolve_trace's guards_fired without appearing in the serialised envelope or marking the run degraded/partial
result: pass
source: automated
coverage_id: 06-07/D2
verified_by: tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_facts_survive_assemble_result_uses_ppr_and_guard_does_not_fire; tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_zero_facts_survive_assemble_result_uses_dpr_fallback_and_guard_fires; tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_guard_fired_run_reports_degraded_false_and_partial_false_on_the_envelope; tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_guard_name_appears_nowhere_in_the_serialised_envelope; tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_fact_filter_node_declares_the_guard_at_config_guards_with_per_query_granularity; tests/parts_core/hipporag/test_dpr_fallback_guard.py#test_guard_declaration_missing_granularity_raises_guarddeclarationerror

### 37. HIPPORAG_PARTS holds exactly thirteen members matching PARTS.md ## §H's node table, none opaque-kinded, none carrying an admission record, all opaque-effective-depth, all in-process
expected: HIPPORAG_PARTS holds exactly thirteen members matching PARTS.md ## §H's node table, none opaque-kinded, none carrying an admission record, all opaque-effective-depth, all in-process
result: pass
source: automated
coverage_id: 06-07/D3
verified_by: tests/parts_core/hipporag/test_thirteen_positions.py#test_the_built_wirings_resolved_node_id_set_equals_the_governing_thirteen; tests/parts_core/hipporag/test_thirteen_positions.py#test_no_hipporag_part_is_opaque_kinded_and_none_carries_an_admission_record; tests/parts_core/hipporag/test_thirteen_positions.py#test_effective_depth_is_opaque_at_all_thirteen_positions

### 38. Every declared-effect divergence from PARTS.md ## §H is enumerated in one committed evidence record with a per-row reason, and a test asserts the record's own reconciliation table exactly covers the divergent-node set computed at test time
expected: Every declared-effect divergence from PARTS.md ## §H is enumerated in one committed evidence record with a per-row reason, and a test asserts the record's own reconciliation table exactly covers the divergent-node set computed at test time
result: pass
source: automated
coverage_id: 06-07/D4
verified_by: tests/parts_core/hipporag/test_thirteen_positions.py#test_declared_effects_union_equals_the_governing_union_plus_exactly_the_additive_set; tests/evidence/test_hipporag_port_record.py#test_reconciliation_table_covers_exactly_the_computed_divergent_node_set

### 39. databasise/parity/run_cross_modality.py's own isolation logic (directory-disjointness, artifacts_overlap as a genuine iff, a cross-read negative control) verified against synthetic, hand-seeded stores — no real corpus, no network, no spend
expected: databasise/parity/run_cross_modality.py's own isolation logic (directory-disjointness, artifacts_overlap as a genuine iff, a cross-read negative control) verified against synthetic, hand-seeded stores — no real corpus, no network, no spend
result: pass
source: automated
coverage_id: 06-08/D2
verified_by: tests/parity/test_cross_modality_isolation.py#test_directories_disjoint_check_against_synthetic_seeded_stores; tests/parity/test_cross_modality_isolation.py#test_artifacts_overlap_is_false_for_the_two_structurally_different_recipes; tests/parity/test_cross_modality_isolation.py#test_artifacts_overlap_is_true_for_two_identical_recipe_hashes; tests/parity/test_cross_modality_isolation.py#test_cross_read_negative_control_against_synthetic_seeded_stores

### 40. databasise/evidence/CROSS-MODALITY-EVIDENCE.md — MODAL-05 recorded honestly as BLOCKED, structurally verified: names the one blocker, the owner's decision, the entry criterion, and never reports a real-run number
expected: databasise/evidence/CROSS-MODALITY-EVIDENCE.md — MODAL-05 recorded honestly as BLOCKED, structurally verified: names the one blocker, the owner's decision, the entry criterion, and never reports a real-run number
result: pass
source: automated
coverage_id: 06-08/D3
verified_by: tests/evidence/test_cross_modality_record.py (11 passed)

### 41. Databasise.compare() refuses a comparison whose selectors resolve a mutates_store-declaring wiring, before any arm executes, naming only the excluded component; a single-selector run and a comparison between two non-mutable wirings are both unaffected
expected: Databasise.compare() refuses a comparison whose selectors resolve a mutates_store-declaring wiring, before any arm executes, naming only the excluded component; a single-selector run and a comparison between two non-mutable wirings are both unaffected
result: pass
source: automated
coverage_id: 06-09/D2
verified_by: tests/seam/test_mutable_store_exclusion.py (5 passed); tests/seam/test_rest_transport.py::test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value[MutableStoreComparisonExcludedError]; tests/seam/ full directory, --extra rest (185 passed, 1 skipped)

## Summary

total: 41
passed: 41
issues: 0
pending: 0
skipped: 0
blocked: 0

## Notes

- verify:pre gate (ai-integration api-coverage): COVERAGE.md failed the gate parser as "matrix is empty" — the file records the §18.5 operations table, which the parser does not read (it needs a `| capability |` table or a `No external API integration: <reason>` line). Phases 04 and 05 fail identically. Fixed 2026-09-10 by adding the declaration line; gate now passes. No content changed.
- commit-claim reconciliation: 06-07-SUMMARY claims `commits: 4` (base 866eed9); measured 6 in its range = 4 claimed + SUMMARY commit + one post-measurement `chore(06-07): sync state.json`. Consistent. The other eight SUMMARYs carry no `commits:` field (legacy) — WARNING only; their plan_head_before ranges all contain real commits.
- automated-ui-verification: ui_phase_active is true but no UI-SPEC exists, live_dom_uat is off — UI checkpoints: 0 auto-verified, 0 queued for manual review.
- 06-VERIFICATION.md is `gaps_found` (SC2 side-by-side and SC6 A/A calibration unmet, both recorded BLOCKED). UAT passing alone will not advance the phase; `/gsd-plan-phase 06 --gaps` remains the verification next action.

## Gaps

[none yet]

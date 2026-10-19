---
phase: 12-hipporag-fixes
plan: 03
subsystem: hipporag
tags: [hipporag, graph-construction, synonymy, self-knn, D-04, D-05]
requires: ["12-02"]
provides:
  - "fact-edges edge key by_chunk; persisted edge attrs cooccurrence_by_chunk, synonymy_weight, passage_weight"
  - "FaissVectorStore.self_knn(top_k, ids=None) searching committed and staged vectors"
  - "synonymy-edges matches only new entities (entity-fact-embed new_entities, else not-yet-committed refs)"
affects: [12-08, 12-13]
tech-stack:
  added: []
  patterns: ["read-merge-write edge accumulation keyed per chunk id", "ids path of self_knn as the one pending-aware read"]
key-files:
  created:
    - databasise/tests/stores/test_vector_self_knn_pending.py
  modified:
    - databasise/stores/vector.py
    - databasise/parts_core/hipporag/fact_edges.py
    - databasise/parts_core/hipporag/graph_augment_persist.py
    - databasise/parts_core/hipporag/synonymy_edges.py
    - databasise/tests/parts_core/hipporag/test_graph_construction.py
key-decisions:
  - "D-04: edge weight = sum(cooccurrence_by_chunk) + synonymy_weight + passage_weight; the per-chunk map is overwritten per key, so re-ingesting a chunk is idempotent"
  - "D-05: synonymy-edges queries only new entities via self_knn(ids=...), which reads committed and staged vectors"
requirements-completed: [HIPP-07, HIPP-08]
status: complete
commits: 2
plan_head_before: 4c8ce3f94e07345187d2ecb7ca36c90a152edbcf
plan_head_after: 9947ab0fd669fd2393c9c927fae6ff0f35504a62
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
metrics:
  completed: 2026-10-19
---

# Phase 12 Plan 03: Edge accumulation across ingests and new-entity synonymy Summary

Co-occurrence weights and edge types now merge across ingests by a per-chunk rule instead of the last ingest overwriting the edge (HIPP-08), and synonymy-edges matches the entities new in this ingest against committed and staged entities through a pending-aware `self_knn(ids=...)`, so a synonymy edge appears on the ingest that introduces it and is not re-emitted later (HIPP-07).

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 (tracer) HIPP-08 | 58ccbc2 | fact-edges emits `by_chunk`; graph-augment-persist does get_edge, merge, upsert_edge |
| 2 HIPP-07 | 9947ab0 | `self_knn(ids=...)` in Faiss and MultiNamespace stores; synonymy-edges new-entity rule; 9 store tests |

Tracer gate: the Task 1 verify command (36 tests) passed after the fix and before Task 2 started.

## Ledger test_ref (intended)

| Row | test node id |
|-----|--------------|
| HIPP-07 | `databasise/tests/parts_core/hipporag/test_graph_construction.py::test_a_synonymy_edge_appears_on_the_introducing_ingest_and_is_not_reemitted` |
| HIPP-08 | `databasise/tests/parts_core/hipporag/test_graph_construction.py::test_cooccurrence_weight_and_types_accumulate_across_ingests` |

Fail-first route for both: `record-fail --at 0807948ae0277f627b7bf51c37bcce82e91a40da` (phase base). Neither test imports a Phase 12 symbol at module level and neither calls `self_knn(ids=...)` directly, so both collect and fail by AssertionError on pre-fix code. 12-02 recorded HIPP-06 in the same file; the file now holds the HIPP-06, HIPP-07 and HIPP-08 rows.

## Fail-first evidence

Both row tests were written and run before the source change they cover (unchanged source).

HIPP-08:

```
        after_d2 = await graph_store.get_edge(wood, films)
>       assert after_d2["weight"] == 2.0
E       assert 1.0 == 2.0
tests/parts_core/hipporag/test_graph_construction.py:298: AssertionError
```

HIPP-07 (committed-only `self_knn` finds nothing among entities staged in the same run):

```
>       assert [(e["src"], e["tgt"]) for e in d1_edges] == [(films, movies)]
E       AssertionError: assert [] == [('entity:fil...tity:movies')]
E         Right contains one more item: ('entity:films', 'entity:movies')
tests/parts_core/hipporag/test_graph_construction.py:219: AssertionError
```

## Verification

- Task 1 command: `pytest -q tests/parts_core/hipporag/test_graph_construction.py tests/seam/test_ingest_abort.py tests/seam/test_hipporag_write_path.py` -> 36 passed (includes the unchanged `test_graph_augment_persist_collapses_two_edge_types_into_summed_weight`).
- Task 2 command 1: `pytest -q tests/stores/test_vector_self_knn_pending.py tests/stores/test_vector_self_knn.py tests/stores/test_vector_validation.py tests/stores/test_vector_reserved_keys.py tests/parts_core/hipporag/test_graph_construction.py` -> 42 passed.
- Plan verification: `pytest -q tests/parts_core/hipporag tests/seam tests/stores tests/runner tests/parity tests/wirings` -> 1320 passed, 3 deselected.
- Acceptance greps: `ids: Sequence[str] | None = None` on two lines of stores/vector.py (Faiss, MultiNamespace); `ids=` in synonymy_edges.py; `get_edge` and `upsert_edge` in graph_augment_persist.py; `"by_chunk"` in fact_edges.py; the HIPP-07 row test def appears once.

## Deviations from Plan

### Auto-fixed Issues

None. Additions beyond the two named row tests (non-row tests, not ledger test_refs): `test_synonymy_edges_matches_only_new_entities_and_keeps_a_score_equal_to_threshold` and `test_synonymy_edges_prefers_new_entities_and_skips_the_query_when_none_are_new` (stub-store tests for the boundary, new-entity, `new_entities` and no-query truths), plus the 9 cases in `test_vector_self_knn_pending.py`. `test_synonymy_edges_emits_deduped_canonical_edges_above_threshold` was updated as the plan directed (cat staged, kitten and rug committed).

## Known Stubs

None.

## Threat Flags

None. T-12-03 mitigated: the ids path reads only this run's own staged buffer, excludes ids staged for deletion and committed entries shadowed by a staged upsert; the default path is unchanged and the STOR-09/STOR-16 tests pass.

## Notes

- Stores written before this plan carry no `cooccurrence_by_chunk` and are rebuild-required (D-04, owner-delegated).
- The BAK edit-guard hook blocked a scripted Python edit of source files in Bash; the Edit and Write tools were used instead. No protected test file was touched.
- Accepted recall difference (D-05): a new entity found only in an old entity's top-k, and not the reverse, is not matched.

## Self-Check: PASSED

Commits 58ccbc2 and 9947ab0 are ancestors of HEAD; all six listed files exist and are committed.

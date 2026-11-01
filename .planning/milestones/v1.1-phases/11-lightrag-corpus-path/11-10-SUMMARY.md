---
phase: 11-lightrag-corpus-path
plan: 10
subsystem: seam
tags: [lightrag, d-15, d-04, q4, lrag-16, lrag-19, refusal, trace]
status: complete

requires:
  - phase: 11-01
    provides: the per-workspace v1 working dir and the v1-index-sync node that populates chunks, entities and relationships
  - phase: 11-04
    provides: the KG lookups reading ll_vector / hl_vector, so the hybrid, local and global arms run end to end on a real ingest
  - phase: 11-09
    provides: the write-free health path (the last engine change before this plan)
provides:
  - "EmptyNamespaceError(store_kind) in the refusal catalogue: REST 422, public field store_kind only"
  - "engine pre-check after _build_stores: a retrieval node whose vector namespace has no vector.faiss refuses before any node runs"
  - "_RETRIEVAL_NAMESPACES: component name (no version) to the part modules' own namespace constants, with a drift test"
  - "FaissVectorStore creates its directory on the first staged write; construction and reads create nothing"
  - "_without_recipe_only_nodes: query runs skip recipe-map nodes nothing depends on; identities still come from the full wiring"
affects: [LRAG-16, LRAG-19, operator-console query panel, Phase 12 HippoRAG query path]

estimate:
  tokens: 35000
  tasks: 2
actuals:
  tokens: 5950
  tasks: 2
  commits: 2
plan_head_before: 60573a2d6be521d346542cf98d79e89753adfbdb
plan_head_after: d37af1306949f00768783578335291f1ffe46476

tech-stack:
  added: []
  patterns:
    - "run copy vs identity copy: the engine runs a pruned deep copy of the resolved wiring and hashes the full one"
    - "existence pre-check on the committed index file, so an emptied-by-delete namespace (zero-row index) stays a plain no-match"

key-files:
  created:
    - databasise/tests/seam/test_empty_namespace.py
    - databasise/tests/seam/test_query_trace_nodes.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/stores/vector.py
    - databasise/wirings/lightrag/README.md
    - databasise/parts_core/lightrag/embedder_index.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/seam/test_evidence_refs.py
    - databasise/tests/seam/test_trace_token.py

key-decisions:
  - "LRAG-16 is a refusal, not an envelope flag (D-15): 'never populated' means no committed vector.faiss in the namespace directory; a namespace emptied by a delete keeps its zero-row index and answers as no match"
  - "The pre-check reads the run wiring's retrieval nodes only (chunk-vector, entity-lookup, relation-lookup); bypass has none and is never refused"
  - "embedder-index stays in base.json and every arm patch (Q4); only the engine's run copy drops it, so derive_mutation_class, the promotion tests and RUN-11 see the same wiring"

requirements-completed: [LRAG-16, LRAG-19]

duration: 45min
completed: 2026-10-18
---

# Phase 11 Plan 10: Empty-namespace refusal and recipe-only embedder-index Summary

**A query on a never-populated LightRAG vector namespace is now a named 422 `EmptyNamespaceError` raised before any model call. Reading a namespace creates no directory. Query traces no longer carry the no-op `embedder-index` node, which stays in every wiring as the index recipe.**

## What changed

- `seam/refusals.py`: `EmptyNamespaceError(*, store_kind)`, added to `__all__`. The message says the store has never been populated and suggests ingesting first. It names no namespace and no path. `_status_for` maps it to 422 through its default branch, so `rest.py` is unchanged.
- `seam/engine.py`:
  - `_RETRIEVAL_NAMESPACES` maps the three retrieval components to `chunk_vector._CHUNKS_NAMESPACE`, `entity_lookup._ENTITIES_NAMESPACE` and `relation_lookup._RELATIONSHIPS_NAMESPACE`. The constants are imported, not retyped.
  - `_refuse_empty_namespaces` runs inside the `try`, after `_build_stores` and before `run_wiring`. The `finally` still finalizes every opened store, and `test_build_stores_cleanup.py`'s first-error pin holds.
  - `_without_recipe_only_nodes(resolved)` returns a deep copy without each `recipe` value node that no remaining node lists in `deps`. `_execute_resolved` parses, opens stores for, pre-checks and runs that copy. `wiring_bytes`, `wiring_instance_hash`, `wiring_id`, `provides` and `evidence_position` still come from the full `resolved`.
- `stores/vector.py`: `FaissVectorStore.__init__` no longer runs `mkdir`. `_write_staged`, the one tmp-pair write path (called from `prepare`), creates the directory first. `load_committed` already treated a missing directory as empty, and `drop` uses `unlink(missing_ok=True)`.
- `wirings/lightrag/README.md`: a "Recipe-only nodes (LRAG-19)" section.
- `parts_core/lightrag/embedder_index.py`: the docstring no longer says the node dispatches on every arm run.

## TDD evidence

- Task 1 RED (unchanged engine and store; `EmptyNamespaceError` added first so the module imports): `5 failed, 2 passed in 2.18s`.
  - Hybrid and naive on a fresh root: `DID NOT RAISE EmptyNamespaceError`.
  - REST: `assert 200 == 422`. The body was a stub-completion envelope with `evidence: []` and spend from both the embedding and LLM clients, so the answer came from the bare query.
  - `select('never-written').query(...)`: the directory existed afterwards.
  - The drift test failed with `no attribute '_RETRIEVAL_NAMESPACES'`.
- Task 1 GREEN:
  - `tests/seam/test_empty_namespace.py tests/stores tests/seam/test_build_stores_cleanup.py tests/seam/test_evidence_resolve_stores.py`: `182 passed`.
  - `tests/seam tests/mcp tests/parity tests/eval tests/runner tests/wirings`: `1 failed, 1207 passed, 3 deselected` on the first run (`test_evidence_refs`, below). After the fix, the tracer gate re-run gave `1208 passed, 3 deselected`.
- Task 2 RED (unchanged engine): `3 failed, 5 passed in 4.14s`.
  - The naive trace listed `['embedder-index', 'embedder-query', 'chunk-vector', ...]`.
  - The real-driver case ran (not skipped) and failed on the same assertion.
  - `_without_recipe_only_nodes` did not exist.
- Task 2 GREEN:
  - `tests/seam/test_query_trace_nodes.py tests/seam/test_promote.py tests/seam/test_promotion_posture.py tests/parity/test_embedder_index_reproduction.py tests/parity/test_arm_conformance.py`: `59 passed, 1 deselected`, with no skips (`-rs`).
  - `tests/seam tests/mcp tests/parity tests/stores tests/runner`: `1 failed, 1287 passed, 3 deselected` (`test_trace_token`, below). After the fix, the file gave `8 passed`.
- Full gate `cd databasise && .venv/bin/python tools/check_offline_suite.py`: **exit 0**, `pytest -q -rs: 2019 passed, 4 deselected` and `python -m pytest -q -rs: 2019 passed, 4 deselected`

## Unprotected tests updated

1. `tests/seam/test_evidence_refs.py::test_zero_item_retrieval_yields_an_empty_but_present_evidence_list` queried a never-written root and expected a 200 with empty evidence. It now upserts one chunk, deletes it and flushes, so the namespace was populated and then emptied. The test still proves that zero-item retrieval gives empty evidence, which is the D-15 no-match path.
2. `tests/seam/test_rest_transport.py`: added the `EmptyNamespaceError` import and its `_REFUSAL_FACTORIES` entry, as the refusals module docstring requires.
3. `tests/seam/test_trace_token.py::test_exchanging_the_reference_with_debug_returns_the_runs_own_node_entries` pinned `embedder-index` in the naive trace's node set. It is removed from the expected set (LRAG-19).

No protected (ledger `test_ref`) file was edited. The protected pins were read with the Read tool and hold unchanged:

- `test_build_stores_cleanup.py`
- `test_evidence_resolve_stores.py`, including `load_committed` on a missing directory creating nothing
- `test_refusal_catalogue.py`
- `test_refusal_status_codes.py`, which parametrizes over `__all__` and now covers `EmptyNamespaceError` at 422
- the store tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The `embedder_index.py` docstring was stale**

- **Found during:** Task 2
- **Issue:** the module docstring said the node "dispatches on every arm run that keeps it". After this plan that is false for seam query runs. Parity runs through `parity/run_arm.py` call `run_wiring` directly, so they still dispatch it.
- **Fix:** the docstring now says the node is recipe-only and that seam query runs skip it, and names the parity exception. The file was outside the plan's `files_modified`. Only the docstring changed.
- **Commit:** d37af13

**2. [Rule 3 - Blocking] Two unprotected tests pinned the old behaviour**

- `test_evidence_refs` and `test_trace_token` are listed above. The plan expected this kind of update and asked for each one to be listed.

Otherwise the plan executed as written. The pre-check lives in a small helper, `_refuse_empty_namespaces`, called from `_execute_resolved` in the planned position.

## Known Stubs

None.

## Threat Flags

None. T-11-21 is mitigated: the refusal is raised before `run_wiring`, and the counting clients record 0 LLM and 0 embedding calls. T-11-22 is mitigated: the REST body keys are exactly `refusal_type`, `message` and `store_kind`, and the message names no namespace and no store path.

## Notes for later plans

- The pre-check covers the three LightRAG retrieval components only. HippoRAG's vector-reading parts (`hipporag-*` namespaces) are not in `_RETRIEVAL_NAMESPACES`, so a HippoRAG query on a fresh root keeps the old behaviour. To extend the check in Phase 12, add their components and constants to the table and to the drift test.
- `parity/run_arm.py` still dispatches `embedder-index`, which RUN-11's reproduction test relies on.

## Self-Check: PASSED

- FOUND: databasise/tests/seam/test_empty_namespace.py
- FOUND: databasise/tests/seam/test_query_trace_nodes.py
- FOUND: 954425e (Task 1)
- FOUND: d37af13 (Task 2)
- Measured commits: `git rev-list --count 60573a2..HEAD` = 2
- Acceptance greps: one `class EmptyNamespaceError`, one `"EmptyNamespaceError",`, two `_RETRIEVAL_NAMESPACES` lines, one `def _without_recipe_only_nodes`, and the `base.json` recipe assertion exits 0

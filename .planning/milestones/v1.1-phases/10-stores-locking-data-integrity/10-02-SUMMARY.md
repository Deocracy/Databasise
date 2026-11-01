---
phase: 10-stores-locking-data-integrity
plan: 02
subsystem: stores
tags: [stores, removal, d-15, lexical, blob, artifact-registry]
status: complete

requires: []
provides:
  - "stores/lexical.py, stores/blob.py and registry_artifact/ removed with their tests (STOR-12 removal half)"
  - "STOR-13 and STOR-14 met by removal (D-15, TOOL-17 removed branch)"
  - "tests/test_removed_stores_absent.py: AST import scan, text scan, pyproject check, 17-member Effect check"
affects: [10-12, TOOL-17, phase-15]

actuals:
  tokens: 19460
  tasks: 2
  commits: 2
plan_head_before: a66cbdb13b77fac84546a5b77534430cc5331e63
plan_head_after: 04efe454141425bb376fe81b58e8cee03a48c8bb

tech-stack:
  added: []
  patterns:
    - "Removal guard: AST scan resolves relative imports and `from pkg import mod` aliases to absolute module names"

key-files:
  created:
    - databasise/tests/test_removed_stores_absent.py
  modified:
    - databasise/pyproject.toml
    - databasise/tests/test_embed_startup.py
    - databasise/tests/test_phase_success_criteria.py
    - databasise/parts_core/lightrag/full_ingest.py
    - databasise/parts_core/lightrag/full_delete.py
    - databasise/parts_core/codebase_memory_mcp.py
    - databasise/README.md
    - databasise/tools/check_import_boundary.py
  deleted:
    - databasise/stores/lexical.py
    - databasise/stores/blob.py
    - databasise/registry_artifact/__init__.py
    - databasise/registry_artifact/index.py
    - databasise/registry_artifact/write_path.py
    - databasise/tests/stores/test_lexical.py
    - databasise/tests/stores/test_blob.py
    - databasise/tests/registry_artifact/__init__.py
    - databasise/tests/registry_artifact/test_index.py
    - databasise/tests/registry_artifact/test_write_path_blast_radius.py

key-decisions:
  - "Phase-1 criterion 4 keeps writes_artifact and artifact_scope on its two arm parts (the marker stays per 10-12) and drops the now-unused scope/effective_depth/producer_instance_hash node config keys"

requirements-completed: [STOR-12, STOR-13, STOR-14]

duration: 15min
completed: 2026-10-17
---

# Phase 10 Plan 02: Remove the unwired lexical store, blob store and artifact registry Summary

The lexical store, blob store and artifact registry are deleted with their tests. A new guard test (AST import scan plus text scan) fails if any of them comes back or is named again, and the 17-member Effect vocabulary is unchanged.

## Accomplishments

- Deleted 10 files with `git rm` and removed the `registry_artifact/` and `tests/registry_artifact/` folders completely, including their `__pycache__`.
- `pyproject.toml` `[tool.setuptools] packages` no longer lists `databasise.registry_artifact`.
- `tests/test_embed_startup.py` test 6 now checks `CozoGraphStore`, `FaissVectorStore` and `SqliteKVStore` only. The docstring says "three".
- `tests/test_phase_success_criteria.py` criterion 4: the arm body writes only graph and vector and finalizes both stores before returning. The test still asserts the derived `quarantined-`/`shared-` namespaces, the per-namespace `graph.cozo`/`vector.faiss` directories, and that `gc_namespace` removes exactly the quarantined directory while the shared one stays intact. The registry-row, `Pin` and write-path `BlastRadiusRefusal` assertions were removed. The docstring records the D-15 removal and points to `tests/validator/test_blast_radius.py`.
- The condition-10 admission evidence in `full_ingest.py`, `full_delete.py` and `codebase_memory_mcp.py` now says the machine keeps no artifact registry (removed in Phase 10, D-15). The `cross_check_conditions` clause and the `(PARTS.md ## §X condition 10)` citation remain.
- The README stores line and the `check_import_boundary.py` docstring example no longer mention lexical/blob.
- Confirmed: `.planning/REQUIREMENTS.md` holds the two "Phase 10 D-15 exception" lines (168 under STOR-13, 173 under STOR-14).

## TDD / tracer evidence

- Pre-change run of `tests/test_removed_stores_absent.py` (Task 1 tests, unchanged source): `3 failed, 1 passed`. Failures: the three module paths exist; the import scan found 38 offending imports, the first being `tests/test_phase_success_criteria.py: databasise.registry_artifact.index`; pyproject lists `databasise.registry_artifact`. The Effect check passed.
- Post-deletion: `tests/test_removed_stores_absent.py tests/test_embed_startup.py tests/test_phase_success_criteria.py tests/stores`: `79 passed`.
- Tracer gate (auto, re-run verify): `tests/parts tests/parts_core tests/validator tests/runner tests/parity`: `453 passed, 3 deselected`.
- Task 2 RED: the new text-scan test failed with `1 failed, 4 passed`. It found 6 hits in the three admission files, the first being `parts_core/codebase_memory_mcp.py: databasise.registry_artifact`.
- Task 2 GREEN: `tests/test_removed_stores_absent.py tests/parts_core/test_codebase_memory_mcp_admission.py tests/parts`: `59 passed`.
- Full default offline suite after both tasks: `1607 passed, 1 skipped, 4 deselected` (266 s).

## Task Commits

1. Task 1: `226b2cf` feat(10-02): remove the unwired lexical store, blob store and artifact registry
2. Task 2: `04efe45` fix(10-02): admission evidence and docs stop naming the removed registry

## Deviations from Plan

None in scope. One small addition: criterion 4's two arm nodes no longer carry the `scope`, `effective_depth` and `producer_instance_hash` config keys, because only the deleted write path read them. Criterion 4 also asserts that `transparent-arm` appears in the trace.

## Notes

- Left as the plan directs: `ledger/ledger.py:76` and `parts_core/__init__.py:38` mention `stores/lexical.py` (slash form) in comments. Neither matches the dotted names the text scan checks. `evidence/ADMISSION-CODEBASE-MEMORY-MCP.md` and `databasise.egg-info/SOURCES.txt` are unchanged.
- Stale `stores/__pycache__/{blob,lexical}*.pyc` files may remain on disk. They are untracked and cannot be imported without their source files.
- No protected test file was edited.

## Self-Check: PASSED

- FOUND: databasise/tests/test_removed_stores_absent.py
- ABSENT (as intended): databasise/stores/blob.py, databasise/stores/lexical.py, databasise/registry_artifact/
- FOUND: 226b2cf, 04efe45 (ancestors of HEAD)

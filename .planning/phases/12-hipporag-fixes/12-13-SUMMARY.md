---
phase: 12-hipporag-fixes
plan: 13
subsystem: hipporag-config-and-docs
tags: [hipporag, wiring-config, docstrings, port-record, offline-gate, d-22]
status: complete
requires:
  - phase: 12-hipporag-fixes
    provides: 12-08, 12-09, 12-11, 12-12 (strict extraction, top_k cut, degraded-on-guard)
provides:
  - base.json and corpus-ingest.json without the seven unread config keys
  - HIPP-18 row test in test_registration.py
  - corrected docstrings in reset_vector_join, synonymy_edges, assemble_result and engine._inject_query
  - HIPPORAG-PORT-RECORD.md Phase 12 divergences and D-21 guard-observability rewrite
  - TESTING-PLAN.md section 2 row for the owner-run HippoRAG qa check
affects: [12-14]
actuals:
  tokens: 9000
  tasks: 3
  commits: 4
plan_head_before: 2133c6bac6f57b51fc850a0a96e4ce9f8a7f1f6d
plan_head_after: ff06ca2251dd962994f58b702263a8ff031db243
tech-stack:
  added: []
  patterns: ["wiring config keys exist only if a part body, the scheduler or the guard machinery reads them"]
key-files:
  created: []
  modified:
    - databasise/wirings/hipporag/base.json
    - databasise/wirings/hipporag/corpus-ingest.json
    - databasise/tests/parts_core/hipporag/test_registration.py
    - databasise/parts_core/hipporag/reset_vector_join.py
    - databasise/parts_core/hipporag/synonymy_edges.py
    - databasise/parts_core/hipporag/assemble_result.py
    - databasise/seam/engine.py
    - databasise/evidence/HIPPORAG-PORT-RECORD.md
    - .planning/TESTING-PLAN.md
key-decisions:
  - "declared_capability is kept in the wirings as a transcription of the governing wiring, recorded in the port record (flagged assumption of the plan)"
requirements-completed: [HIPP-18]
---

# Phase 12 Plan 13: Config and docs are honest Summary

Seven unread HippoRAG wiring keys are removed, four stale docstrings are corrected, the port record states every Phase 12 divergence, and the offline gate is green in both pytest styles.

## Tasks

| Task | Name | Commit |
|---|---|---|
| 1 | Tracer: no unread config key remains (HIPP-18, D-22) | 388fd9a |
| 2 | Docstrings match the code (D-18, D-21, D-22) | 4bcf068 |
| 3 | Port record, TESTING-PLAN row, offline gate | 0fa4013 (record), ff06ca2 (TESTING-PLAN) |

## HIPP-18 ledger row

| Row | Intended test_ref | Fail-first evidence |
|---|---|---|
| HIPP-18 | `databasise/tests/parts_core/hipporag/test_registration.py::test_no_unread_config_key_remains_and_no_docstring_claims_export_level_edge_types` | Run against the source as left by 12-12 (HEAD 2133c6b), before the wiring edit: `AssertionError: ('base', 'entity-fact-embed', 'namespaces')` from `assert not (node_id == removed_node and removed_key in config)`; `1 failed, 5 passed`. After the edit: `46 passed` on test_registration.py, tests/wirings and tests/parity/test_build_hipporag_index.py. |

The test loads both wirings with `load_wiring`, asserts each parses with `report.ok`, asserts none of the seven (node, key) pairs is present (exact key equality, so `linking_top_k` and `top_k` are untouched), no string config value contains "no token spend", and graph_augment_persist's docstring contains "not exported" and not "auditable". The graph_augment_persist docstring already carried the "persisted, not exported" sentence from 12-03, so no edit was needed there. Removed keys: entity-fact-embed `namespaces`, synonymy-edges `guard`, reset-vector-join `socket_shape` / `arm_precedence` / `apportionment_policy`, ppr `readback`, assemble-result `order_policy`. Entity-fact-embed's config object became empty and was dropped; node order, deps and provides are unchanged.

## Task 2 detail

Comment/docstring-only commit (4 files, 19 insertions, 33 deletions; `git show 4bcf068` touches no code line):

- `reset_vector_join.py`: the conftest-seeding note replaced by the real writer (entity-fact-embed's `fact:<id>` record, D-06); states the node makes no client call and reads the query vector from fact-score (D-17).
- `synonymy_edges.py`: guard paragraph names no wiring key; the new-entity rule is the guard (D-05).
- `assemble_result.py`: order_policy text deleted; the "Observability, resolved" paragraph replaced by the D-21 statement (a fired guard is `degraded` with node-free reason codes).
- `engine._inject_query`: HippoRAG's `consumes_query` list copied from the wiring.
- `ppr.py`: no edit. It already carried no readback-config or fixture claim after 12-01 (the only "readback" is the upstream line reference and the bare-id sentence).

## Task 3 detail

- `HIPPORAG-PORT-RECORD.md`: "The guard-observability resolution" rewritten for D-21 (words guard-observability, guards_fired, degraded kept); new section "Phase 12 divergences and limits" with D-05, D-04, D-08, D-20, D-19, D-03 with D-12 (pre-Phase-12 stores rebuild-required: no `doc:` manifest, ordinal-only ids, no per-chunk co-occurrence map), D-16 (`[writes_artifact]` selector now unsatisfiable), D-22 (removed keys, config_hash change, `declared_capability` kept) and the edge_types persisted-not-exported note. The stale "synonymy-edges guard proxy" paragraph in Limits was reworded because the guard key no longer exists. `test_hipporag_port_record.py` unchanged (no parsed table shape changed).
- `.planning/TESTING-PLAN.md` section 2: one row for the owner-run real-provider HippoRAG qa answer and per-query cost check (HIPP-13).
- Offline gate `cd databasise && .venv/bin/python tools/check_offline_suite.py` exit 0:
  - `pytest -q -rs: 2171 passed, 4 deselected in 567.89s (0:09:27)`
  - `python -m pytest -q -rs: 2171 passed, 4 deselected in 561.08s (0:09:21)`

## Deviations from Plan

None - plan executed exactly as written. One process note: a first attempt to apply the docstring edits through a scripted Bash edit was refused by the BAK edit-guard hook; nothing had been written, and the edits were then made with the Edit tool.

## Known Stubs

None.

## Threat Flags

None (config and documentation only).

## Self-Check: PASSED

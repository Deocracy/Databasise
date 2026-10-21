---
phase: 14-promotion-ledger
plan: 07
subsystem: parts
tags: [registry, reachability, f07, falsifier2, catalogued-not-registered, granted-edit]
requires: ["14-01", "14-04"]
provides:
  - databasise/parts_core/declared_only.py DECLARED_ONLY_PARTS without CODEBASE_MEMORY_MCP_PART
  - databasise/evidence/falsifier2.py probe_registry() with the catalogued part, _parse on probe_registry()
  - databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md regenerated (CA-2 catalogued, not registered row)
  - databasise/tests/fixtures/codebase-memory-mcp.json (moved single-node wiring)
  - databasise/tests/parts/test_registry_reachability.py (LEDG-12 row test)
affects: [14-10, 14-11, phase-15]
status: complete
actuals:
  tokens: 6000
  tasks: 1
  commits: 1
plan_head_before: 135811c857911191eab81f51c724c1879a4bd679
plan_head_after: 3e228867b35bcb00d56ceb0ff25530494de05d33
tech-stack:
  added: []
  patterns: ["admitted but unregistered parts are registered by the probe registry and by tests through registry=", "F-07 record renders unregistered CA-2 from the fixed catalogued rows, not _KNOWN_REASONS"]
key-files:
  created:
    - databasise/tests/parts/test_registry_reachability.py
    - databasise/tests/fixtures/codebase-memory-mcp.json
  modified:
    - databasise/parts_core/declared_only.py
    - databasise/evidence/falsifier2.py
    - databasise/evidence/f07_report.py
    - databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md
    - databasise/tests/seam/test_refusal_reachability.py
    - databasise/tests/seam/test_mutable_store_exclusion.py
    - databasise/tests/parts_core/test_codebase_memory_mcp_admission.py
    - databasise/tests/parts/test_registry.py
    - databasise/tests/validator/test_falsifier2_evidence.py
key-decisions:
  - "codebase-memory-mcp@0.1.0 leaves default_registry() (37 entries); the CODEBASE_MEMORY_MCP_PART constant stays, registered by probe_registry() and by tests"
  - "F-07 keeps the part as a permanent-exclusion catalogued row 'codebase-memory-mcp@0.1.0 (CA-2, admitted, not registered)'; rendering from a registry that holds it raises the named 'no disposition reason' ValueError"
  - "the granted protected edit uses function-local imports in the one test, so the three granted hunks are the only changed regions"
requirements-completed: [LEDG-12]
---

# Phase 14 Plan 07: Reachable-or-unregistered production registry Summary

`codebase-memory-mcp@0.1.0` no longer sits in `default_registry()`: no selector reaches it, so the evidence lane (`probe_registry()`) and the tests that need it register it themselves, its wiring is a test fixture, and F-07 records it as catalogued, not registered.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 tracer: registry change, probe registry, F-07 regeneration, fixture move, granted protected edit, four unprotected followers, LEDG-12 row test | 3e22886 | 618 passed (plan verify set plus parts_core and mcp dirs); 1339 passed (seam, wirings, runner, foreign dirs) |

## Ledger rows

| Row | Intended test_ref (node id) |
|-----|-----------------------------|
| LEDG-12 | `databasise/tests/parts/test_registry_reachability.py::test_every_admitted_registered_part_is_reachable` |

## Fail-first evidence

Run in the main tree against the unchanged source (before any source edit), the row test failed by a plain `AssertionError`:

```
E       AssertionError: admitted parts in default_registry() that no selector or corpus wiring reaches: ['codebase-memory-mcp@0.1.0']
E       assert ['codebase-memory-mcp@0.1.0'] == []
E         Left contains one more item: 'codebase-memory-mcp@0.1.0'
```

The file imports at module level only `default_registry`, `WIRING_NAMES`, `all_wirings` and `load_wiring`, all present at the phase base bb52fbb, and copies its one helper, so the orchestrator's `record-fail --at` can collect it there. A scratch-worktree run at bb52fbb was not repeated here.

## Granted edit (WIRE-17 protected file)

Precondition confirmed with the Read tool: `check_edit_grants` holds `databasise/tests/seam/test_refusal_reachability.py` at `granted_at` 706 (14-07 Task 1). Three hunks changed, nothing else: line 29 `_CBM_WIRING_PATH` points at `tests/fixtures/codebase-memory-mcp.json`; `_engine` gains `registry=None` and passes it to `Databasise`; `test_compare_with_one_mutating_selector_is_refused` builds `default_registry()` plus `CODEBASE_MEMORY_MCP_PART` and passes it. The orchestrator owes plant runs for WIRE-17 (`plants/WIRE-17.json`).

## Verification

- `databasise/tests/parts`, `parts_core`, `validator`, `evidence`, `mcp`, `seam/test_mutable_store_exclusion.py`, `seam/test_refusal_reachability.py`, `seam/test_seam_doc_consistency.py`: 618 passed. This set includes `test_f07_record.py` (unchanged, passes against the regenerated document), `test_falsifier2_evidence.py` and `test_falsifier2_probes.py`.
- `databasise/tests/seam`, `wirings`, `runner`, `foreign` in full: 1339 passed (includes the protected selector-reachability, status-code and doc-consistency tests).
- Acceptance one-liner (`default_registry()` lacks the part, `probe_registry()` has it) exits 0; `git ls-files` shows the fixture and no `databasise/wirings/codebase-memory-mcp.json`.
- ruff on touched files: only pre-existing findings remain (`falsifier2.py:510` RUF059, `test_codebase_memory_mcp_admission.py:101` PLW1510); the new `.keys()` iterations carry `noqa: SIM118` like the existing registry tests.

## Deviations from Plan

None - plan executed as written. Notes:

- The F-07 prose around the verdict and the population paragraph were reworded beyond the reason text (the old text said "both real, registered" and "admitted and registered"); `CA-2`, `MC-1`, `CA-7`, `MutableStoreComparisonExcludedError` and `lightrag/full-delete@0.2.0` are kept as `test_f07_record.py` requires.
- `_KNOWN_REASONS` no longer holds the part; the reason text moved into the new `_CATALOGUED_NOT_BUILT` row, so a registry holding the part makes `_live_mutates_store_rows` raise the named ValueError.
- Documents that name the old wiring path (`ADMISSION-CODEBASE-MEMORY-MCP.md:137`, `docs/gui/CODEBASE-MAP.md`, `pyproject.toml:160-163`, `docs/gui/API-INVENTORY.md`) are untouched, as the plan assigns them to 14-10 and 14-11.

## Known Stubs

None.

## Self-Check: PASSED

Commit 3e22886 is on HEAD; `databasise/tests/parts/test_registry_reachability.py` and `databasise/tests/fixtures/codebase-memory-mcp.json` exist.

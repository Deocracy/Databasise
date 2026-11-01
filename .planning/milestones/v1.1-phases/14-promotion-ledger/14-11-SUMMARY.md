---
phase: 14-promotion-ledger
plan: 11
subsystem: docs
tags: [d13, wiring-path, documentation]
requires: ["14-07"]
provides:
  - current wiring path in ADMISSION-CODEBASE-MEMORY-MCP.md, CODEBASE-MAP.md and the pyproject.toml package-data comment
affects: [14-10]
status: complete
actuals:
  tokens: 700
  tasks: 1
  commits: 1
plan_head_before: e4afdc5d9999d0d2177c081903b5dd20a44cc83c
plan_head_after: 207657b01849cc2cc7fffffe4ddff03056f5caa5
key-files:
  modified:
    - databasise/evidence/ADMISSION-CODEBASE-MEMORY-MCP.md
    - docs/gui/CODEBASE-MAP.md
    - databasise/pyproject.toml
key-decisions:
  - "the pattern line for databasise.wirings is byte-identical; only the comment changed"
requirements-completed: []
---

# Phase 14 Plan 11: Wiring-path documentation follow-through Summary

The admission record, the codebase map and the pyproject package-data comment now name `databasise/tests/fixtures/codebase-memory-mcp.json` and state the part is not in `default_registry()` since Phase 14 (D-13).

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Documents that named the old wiring path say where it lives now | 207657b |

## Verification

- `pytest databasise/tests/parts_core/test_codebase_memory_mcp_admission.py databasise/tests/evidence`: 109 passed.
- Acceptance greps: fixture path present in both documents; pattern line count 1; stale comment count 0.

## Ledger rows

No LEDG row completes in this plan (D-13 follow-through for LEDG-12, which 14-07 completes). No new test node id; no fail-first evidence applies (documentation only).

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

207657b is in HEAD; the three modified files exist.

---
phase: 13-selectors-wiring-runner
plan: 09
subsystem: wirings
tags: [lightrag, guards, d-20, wiring-patches, documentation]
requires: ["13-06"]
provides:
  - no file under databasise/wirings/ carries a top-level guards key
  - the LightRAG README and CODEBASE-MAP row G-25 record the dropped fall-through guards (D-20)
affects: []
actuals:
  tokens: 4000
  tasks: 2
  commits: 2
plan_head_before: f47511ab6ff6c8b2ca7393925d7eacc9073db87a
plan_head_after: fbe4b11125d29890d62be130ada257bf19e900f7
tech-stack:
  added: []
  patterns: ["tree scan test that flags only top-level guards keys, leaving node-level config.guards alone"]
key-files:
  created:
    - databasise/tests/wirings/test_lightrag_guards.py
  modified:
    - databasise/wirings/lightrag/arm-local.json-patch.json
    - databasise/wirings/lightrag/arm-global.json-patch.json
    - databasise/wirings/lightrag/README.md
    - docs/gui/CODEBASE-MAP.md
key-decisions:
  - "The keyword fall-through guards are removed, not implemented: reinstating v1's chain switch would put the relation chain into the local arm (D-20)"
requirements-completed: [WIRE-09]
status: complete
duration: 15m
completed: 2026-10-19
---

# Phase 13 Plan 09: LightRAG keyword fall-through guards dropped Summary

**The unread top-level `guards` arrays are gone from the local and global LightRAG arm patches, the README and CODEBASE-MAP no longer claim them, and the resolved arms hash identically before and after.**

## Accomplishments

- Removed the top-level `guards` array (lines 30-42) from `arm-local.json-patch.json` and `arm-global.json-patch.json`; `operations` and `resulting_node_id_set` are untouched. Resolved-arm sha256 over `json.dumps(sort_keys=True)` is identical before and after: local `e89d8752...94b2`, global `c6cbce5a...c3d8`.
- `wirings/lightrag/README.md`: local and global table rows lose "carries a declared guard"; a "Recorded deviations" section states that v1's chain switch (`operate.py:5021-5062`) is not modelled, why, and that the frozen `docs/system-model/wirings` copies keep the illustrative declarations.
- `docs/gui/CODEBASE-MAP.md` row G-25: the top-level-guards sentence is replaced by one stating the removal (D-20).
- Frozen `docs/system-model/` and `databasise/evidence/wirings` untouched (`git diff --stat` empty). `wirings/hipporag/base.json` node-level `config.guards` untouched.

## Ledger test_ref and fail-first evidence

| Row | Intended test_ref | Fail-first evidence |
|-----|-------------------|---------------------|
| WIRE-09 | `databasise/tests/wirings/test_lightrag_guards.py::test_no_wiring_file_has_a_top_level_guards_key` | Run on unchanged patches: `AssertionError: top-level guards arrays nothing evaluates: ['lightrag/arm-global.json-patch.json', 'lightrag/arm-local.json-patch.json']` |
| WIRE-09 | `databasise/tests/wirings/test_lightrag_guards.py::test_the_readme_records_the_dropped_guards` | README reverted in the working tree only (restored, never committed): `AssertionError: README does not record the D-20 deviation` |
| WIRE-09 | `...::test_node_level_guards_stay_legitimate`, `...::test_the_resolved_local_and_global_arms_are_unchanged` | Guard-rail tests; pass before and after by design (the resolver never read the arrays) |

The row test_ref for the ledger is the file `databasise/tests/wirings/test_lightrag_guards.py`.

## Verification

`cd databasise && .venv/bin/pytest -q tests/wirings tests/seam/test_selectors.py tests/seam/test_query_trace_nodes.py` -> 69 passed. The acceptance scan prints `[]`.

## Deviations from Plan

None - plan executed exactly as written. (The pre-fix README failure was shown by temporarily restoring the original README file, since the doc change landed before the README test was written.)

## Known Stubs

None.

## Self-Check: PASSED

Commits 8016cce and fbe4b11 are on main; the test file, both patches, README and CODEBASE-MAP exist and are committed.

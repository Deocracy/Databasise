---
phase: 14-promotion-ledger
plan: 06
subsystem: seam
tags: [alias, selectors, wiring-lookup, read-only-ledger, corpus-wiring, row-tests]
requires: ["14-02", "14-03", "14-05"]
provides:
  - databasise/tests/seam/test_alias_resolution.py (LEDG-03 row test)
  - databasise/tests/seam/test_corpus_wiring.py (LEDG-13 row test)
affects: [14-07, 14-09]
status: complete
actuals:
  tokens: 11000
  tasks: 2
  commits: 3
plan_head_before: b5df2a27ed5c57458d048a18db24365724eb0cfa
plan_head_after: ee2a9882385f79c0fa825ee01f9d9bee216b37af
tech-stack:
  added: []
  patterns: ["read path opens existing store only, closes with `with`", "one refusal object for every miss", "single loader for wiring file layout"]
key-files:
  created:
    - databasise/tests/seam/test_alias_resolution.py
    - databasise/tests/seam/test_corpus_wiring.py
  modified:
    - databasise/seam/selectors.py
    - databasise/seam/engine.py
    - databasise/tests/seam/test_query_object.py
    - databasise/tests/seam/test_operator_verb_concurrency.py
key-decisions:
  - "_resolve_alias builds one UnsatisfiableSelectorError(alias=<caller's alias>) and raises it for a missing ledger.db, a missing row and an unresolvable mutation_id, so the three cases cannot differ"
  - "engine._corpus_wiring calls load_wiring(family, variant=f'corpus-{operation}'); the engine's own wirings-root constant is deleted"
requirements-completed: [LEDG-03, LEDG-13]
---

# Phase 14 Plan 06: Alias resolution through the shared lookup, and one corpus wiring loader Summary

An alias row naming any `all_wirings()` name (HippoRAG included) now resolves through `wiring_for_name`; an unresolvable row, a missing row or a missing `ledger.db` is one named 422 `UnsatisfiableSelectorError` that names only the caller's alias, and the read path no longer creates `ledger.db`. `_corpus_wiring` loads through `load_wiring`, so the corpus path layout is defined only in `resolve.py`.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 tracer: `_resolve_alias` over `open_existing`, `with`, `wiring_for_name`; docstrings; `test_query_object` patch target; six-arm assertion | 4767b47 | 176 passed (selector set in the plan's verify) |
| 2: `_corpus_wiring` through `load_wiring`, constant removed | df15d93 | 70 passed (corpus set, v1-backed tests included) |
| follow-up: row test no longer calls `Ledger.close`, which the phase base lacks | ee2a988 | row test collects and fails by assertion at bb52fbb |

## Ledger rows

| Row | Intended test_ref (node ids) |
|-----|------------------------------|
| LEDG-03 | `databasise/tests/seam/test_alias_resolution.py::test_a_hipporag_alias_never_gives_a_500`, `::test_an_unresolvable_alias_row_is_a_named_422`, `::test_the_mcp_tools_never_raise_an_unexpected_error_for_either_row`, `::test_promoting_a_hipporag_trace_creates_an_alias_that_resolves`, `::test_a_store_root_without_a_ledger_refuses_and_stays_empty` (use the file as `test_ref`) |
| LEDG-13 | `databasise/tests/seam/test_corpus_wiring.py::test_corpus_wiring_reads_through_load_wiring`, `::test_a_missing_corpus_file_is_a_named_refusal` (use the file as `test_ref`) |

## Fail-first evidence

Run in a scratch worktree at the phase base bb52fbb with only the two row files copied in (`PYTHONPATH=<wt> databasise/.venv/bin/python -P -m pytest -q ... --rootdir=<wt>`). Both files collect there. 7 failed, 0 passed; every failure is an AssertionError. The worktree was removed.

- `test_a_hipporag_alias_never_gives_a_500`: `AssertionError: engine.query under a hipporag alias raised UnknownArmError: unknown arm 'hipporag'; known arms: ['bypass', 'global', 'hybrid', 'local', 'naive']`
- `test_an_unresolvable_alias_row_is_a_named_422`: `AssertionError: engine.query under an unresolvable row gave UnknownArmError: ...` / `assert 'UnknownArmError' == 'UnsatisfiableSelectorError'`
- `test_the_mcp_tools_never_raise_an_unexpected_error_for_either_row`: `AssertionError: query under a hipporag alias raised UnexpectedToolError: Error executing tool query`
- `test_promoting_a_hipporag_trace_creates_an_alias_that_resolves`: `AssertionError: _resolve_alias raised UnknownArmError: unknown arm 'hipporag'; ...`
- `test_a_store_root_without_a_ledger_refuses_and_stays_empty`: `AssertionError: the alias read path created ledger.db`
- `test_corpus_wiring_reads_through_load_wiring`: `AssertionError: assert {'wiring_id': ...} == {'marker': 'corpus-ingest from the patched resolve root'}` (the engine returned the repository file, ignoring the patched `resolve._WIRINGS_ROOT`)
- `test_a_missing_corpus_file_is_a_named_refusal`: `AssertionError: a corpus-delete wiring loaded from a root that holds none`

The engine-level step of each loop fails first at the base, so the REST route 500s are not separately shown there; the post-change run passes all six REST routes and the three MCP tools for both rows.

## Verification

- Task 1 verify command: 176 passed (row file, test_query_object, test_alias_registry, test_operator_verb_concurrency, and the protected test_selectors, test_selector_reachability, test_empty_capability_selector, test_compare_keys, test_seam_doc_consistency, test_refusal_status_codes, test_hipporag_write_path, test_hipporag_query_path).
- Task 2 verify command: 70 passed, run in the main tree with `v1/.venv` present (test_corpus_write_gate, test_lightrag_corpus_path, test_lightrag_inbox, test_lightrag_ingest_mach11, test_interrupted_documents, test_refusal_reachability, test_hipporag_write_path, row file).
- Plan wave command `pytest databasise/tests/seam databasise/tests/wirings databasise/tests/mcp`: 1187 passed in 459 s.
- `import databasise.seam.engine` has no `_WIRINGS_ROOT`; `grep` finds `wiring_for_name(record.mutation_id)` only as the `wiring_for_name(record.mutation_id) if record is not None` line and `open_existing` in `selectors.py`.
- The full offline gate was not run (the plan scopes verification to the sets above).

## Deviations from Plan

**1. [Rule 1 - Bug in my own row test] Row test called `Ledger.close()`**
- **Found during:** fail-first run at the phase base
- **Issue:** `Ledger.close` is a 14-02 addition, so at bb52fbb the test errored with AttributeError instead of failing by assertion.
- **Fix:** the fixture helper closes `ledger._conn` directly.
- **Files modified:** databasise/tests/seam/test_alias_resolution.py
- **Commit:** ee2a988

**2. [Wording] `grep -n "wiring_for_name(record.mutation_id)"` acceptance line** returns one line, but the call is `wiring_for_name(record.mutation_id) if record is not None else None`: the `with` block holds only the `by_alias` read, so the row is read inside the connection and resolved after it closes. The behaviour matches the plan.

Otherwise the plan was executed as written. `ruff` reports pre-existing findings (SIM117 and others) in the touched files; none are new from this plan's logic.

## Known Stubs

None.

## Threat Flags

None. T-14-10, T-14-11 and T-14-12 are mitigated and asserted by the row tests (no arm name, row value or "known arms" in any body; 422 or a normal result on all six REST routes and the MCP tools; no `ledger.db` created).

## Self-Check: PASSED

- databasise/tests/seam/test_alias_resolution.py, databasise/tests/seam/test_corpus_wiring.py: FOUND
- 4767b47, df15d93, ee2a988: FOUND on main

---
phase: 14-promotion-ledger
plan: 04
subsystem: seam
tags: [selectors, capability-matching, validator, kind-mismatch, row-tests]
requires: []
provides:
  - databasise/tests/seam/test_capability_effects.py (LEDG-10 row test)
  - databasise/tests/validator/test_node_kind.py (LEDG-11 row test)
affects: [14-07]
status: complete
actuals:
  tokens: 4500
  tasks: 2
  commits: 2
plan_head_before: b5cc8ed3531ee697d1cc1c8e9618b0163b81c69f
plan_head_after: 4b10bf10bbc014ef3f15de247aab546a9a635a42
tech-stack:
  added: []
  patterns: ["row test imports only names present at the old fix parent", "refusal captured with try/except and asserted on the type name"]
key-files:
  created:
    - databasise/tests/seam/test_capability_effects.py
    - databasise/tests/validator/test_node_kind.py
  modified: []
key-decisions:
  - "No production code changed: both rows were already met at HEAD (fixes 3fd6e4c and 5d61a79); this plan only pins them"
requirements-completed: []
---

# Phase 14 Plan 04: Capability-effect and node-kind row tests Summary

Two row tests pin behaviour HEAD already has: a `writes_*` capability selector never selects a read-only query arm (LEDG-10), and a node whose kind differs from its Part's kind is reported as `kind-mismatch` by name while every shipped wiring parses clean (LEDG-11).

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 tracer: LEDG-10 capability-effects row test | c0c574f | 55 passed (row file + test_selectors, test_selector_reachability, test_empty_capability_selector) |
| 2: LEDG-11 node-kind row test | 4b10bf1 | validator directory + row file: 129 passed |

## Ledger rows

| Row | Intended test_ref | Tests |
|-----|-------------------|-------|
| LEDG-10 | `databasise/tests/seam/test_capability_effects.py` | `::test_write_capabilities_never_select_a_read_only_query_arm[writes_artifact|writes_graph|writes_vector|writes_kv]`, `::test_read_capabilities_select_the_same_arms_as_before[...]`, `::test_the_effect_set_matching_uses_for_every_arm` |
| LEDG-11 | `databasise/tests/validator/test_node_kind.py` | `::test_a_kind_mismatch_is_reported_by_name`, `::test_every_shipped_wiring_parses` |

## Fail-first evidence (old fix parents, scratch git worktrees)

Run as `PYTHONPATH=<worktree> databasise/.venv/bin/python -P -m pytest -q <worktree>/<file> -p no:cacheprovider --rootdir=<worktree>`. The `-P` flag is required: with plain `python -m pytest` run from the repository root the current directory comes first on `sys.path`, so `databasise` resolves to the main tree and the old-commit run falsely passes (9 passed). With `-P` the worktree's own `databasise` is imported (confirmed by printing `databasise.__file__`).

LEDG-10 at `3fd6e4c^` (2fc25ef): 5 failed, 4 passed. All failures are AssertionError:
- `test_write_capabilities_never_select_a_read_only_query_arm[writes_artifact]`: `AssertionError: ['writes_artifact'] must be refused (no query wiring writes); it selected arm 'naive'`
- `...[writes_graph]`: `AssertionError: ['writes_graph'] must be refused (no query wiring writes); it selected arm 'hipporag'`
- `...[writes_vector]`: same text, `it selected arm 'hipporag'`
- `...[writes_kv]`: same text, `it selected arm 'hipporag'`
- `test_the_effect_set_matching_uses_for_every_arm`: `AssertionError: hipporag: ['calls_embedding', 'calls_llm', 'reads_graph', 'reads_kv', 'reads_vector', 'writes_artifact', 'writes_graph', 'writes_kv', 'writes_vector']`

LEDG-11 at `5d61a79^` (82529bf): 1 failed, 1 passed.
- `test_a_kind_mismatch_is_reported_by_name`: `AssertionError: no kind-mismatch violation; got []`

Both worktrees were removed with `git worktree remove --force`; `git worktree list` afterwards shows the main tree plus the pre-existing `.claude/worktrees/agent-aa9dde19a41b39acb` (not mine).

## Deviations from Plan

**1. [Rule 3 - Blocking] Old-commit run needs `python -P`.** The plan's command (`PYTHONPATH=<dir> ... python -m pytest`) imports the main tree's `databasise`, so the old-commit run passed. Added `-P` and `--rootdir=<worktree>`; the orchestrator's `record-fail --at` should check it imports the worktree's package the same way. No file changed.

Otherwise: plan executed as written. The LEDG-10 tests are parametrized, so node ids carry `[id]` suffixes; use the file as `test_ref`.

## Known Stubs

None.

## Self-Check: PASSED

- databasise/tests/seam/test_capability_effects.py: FOUND
- databasise/tests/validator/test_node_kind.py: FOUND
- c0c574f, 4b10bf1: FOUND on main
- `grep -c _capability_tokens` on the LEDG-10 file and `grep -c CODE_KIND_MISMATCH` on the LEDG-11 file: both 0

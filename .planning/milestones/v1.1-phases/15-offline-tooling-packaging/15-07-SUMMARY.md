---
phase: 15-offline-tooling-packaging
plan: 07
subsystem: mcp
tags: [mcp, tool-descriptions, TOOL-19, TOOL-20]
requires: []
provides:
  - "description= on all ten MCP tool decorators; every published description and inputSchema is plan-free"
  - "MCP package text states ten tools (TOOL_NAMES) instead of five"
affects: [databasise/mcp/server.py, databasise/mcp/tools.py, databasise/mcp/__init__.py, databasise/seam/evidence.py]
key-files:
  created:
    - databasise/tests/mcp/test_tool_descriptions.py
  modified:
    - databasise/mcp/server.py
    - databasise/mcp/tools.py
    - databasise/mcp/__init__.py
    - databasise/seam/evidence.py
    - databasise/tests/mcp/test_dual_transport_parity.py
key-decisions:
  - "compare's description is 'Run one query ... Requires query and selectors. ' + COMPARE_RESPONSE_SHAPE_RULE, because seam/test_compare_keys.py pins the rule inside the MCP description (D-10)"
requirements-completed: [TOOL-19]
status: complete
duration: 40min
completed: 2026-10-21
commits: 2
plan_head_before: dedcbe6b0f2f7546f4eccc5fd3e670055c55ed75
plan_head_after: f50c36daa3238c54b1e132e961e95e456350fbec
actuals:
  tokens: 6000
  tasks: 2
  commits: 2
---

# Phase 15 Plan 07: MCP tool descriptions Summary

Each of the ten MCP tools now publishes a modality-neutral description saying what it does, its required arguments and what it returns, no published description or input schema names a plan, phase, arm or part, and the package text says ten tools.

## What changed

- `databasise/mcp/server.py`: `description=` on all ten `@server.tool(...)` decorators (`grep -c "description="` prints 10). The plan references in the `compare`, `retry` and `promote` docstrings became `#` comments. The module docstring now describes the `call_tool` override once. `create_server`'s docstring cites `TOOL_NAMES` (ten).
- `databasise/mcp/tools.py`: plan ids removed from the `Delete`, `Retry`, `Status`, `Promote`, `Rollback` and `Retire` `*ToolArgs` docstrings (they publish into `inputSchema.$defs`). Line 1 cites `TOOL_NAMES` (ten). The delete note no longer claims ingest declares `writes_artifact`; both corpus ports declare `mutates_store`.
- `databasise/mcp/__init__.py`, `databasise/tests/mcp/test_dual_transport_parity.py` (docstring line 3, comment at ~402; no assertion changed): cite `TOOL_NAMES`.
- `databasise/tests/mcp/test_tool_descriptions.py`: the TOOL-19 row test, six nodes.

## Row test node ids and fail-first evidence

Intended ledger test_ref: `databasise/tests/mcp/test_tool_descriptions.py` (whole file). Run against unchanged source (phase base code) with only the test file present:

- `test_every_tool_publishes_a_non_empty_description`: `AssertionError: tools publishing an empty description: ['delete', 'ingest', 'query', 'resolve', 'retire', 'rollback', 'status']`
- `test_no_description_names_a_plan_or_a_phase`: `AssertionError: descriptions naming a plan or phase: {'compare': ['06-03', 'PLAN.md'], 'retry': ['11-08'], 'promote': ['07-03', 'PLAN.md', 'Phase 7']}`
- `test_no_published_input_schema_names_a_plan`: `AssertionError: input schemas naming a plan or phase: {'delete': [...], 'retry': [...], 'status': ['12-09'], 'resolve': ['04-07', '04-04'], 'promote': [...], 'rollback': [...], 'retire': [...]}`
- `test_no_description_names_an_arm_or_a_part`: `AssertionError: descriptions naming an arm, wiring or part: {'compare': ['HippoRAG']}`
- `test_no_stale_five_tool_count_remains`: `AssertionError: files still stating the old tool count: {'__init__.py': ['intention'], 'server.py': ['tools'], 'tools.py': ['tool names'], 'test_dual_transport_parity.py': ['tools']}`
- `test_no_fixed_registry_count_phrase_remains`: passes at the base, as the plan states (pins the row's second half).

The pre-fix run was 5 failed, 1 passed. The module collects at the phase base: it imports only `create_server` and `TOOL_NAMES`, which exist there. `record-fail --at dedcbe6` (the commit before this plan's first code commit, `2410ede`) is the fail-first route.

## Tests

- `databasise/tests/mcp` (including protected `test_mcp_refusal_mapping.py`, `test_tool_growth_invariant.py`), protected `databasise/tests/seam/test_run01_coverage_crosscheck.py`, protected `databasise/tests/launcher/test_launchers.py`, `databasise/tests/seam/test_compare_keys.py`: 127 passed after Task 2.
- A wider run of `databasise/tests/mcp databasise/tests/seam databasise/tests/launcher/test_launchers.py databasise/tests/test_docstring_currency.py` was 1226 passed, 1 failed (`test_compare_keys`, see deviation 1, fixed and re-run green).
- No protected test failed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] compare's description must carry the shared response-shape rule**
- **Found during:** Task 1 verification (wider seam run)
- **Issue:** `databasise/tests/seam/test_compare_keys.py::test_the_rule_is_stated_in_the_docstring_the_openapi_description_and_the_mcp_tool` requires `COMPARE_RESPONSE_SHAPE_RULE` inside the MCP `compare` description. My first, paraphrased description dropped it.
- **Fix:** the description is `"Run one query ... Requires query and selectors. " + COMPARE_RESPONSE_SHAPE_RULE`, imported from `databasise.seam.compare` (a constant, no call; the growth-invariant AST check stays green).
- **Files modified:** `databasise/mcp/server.py`

**2. [Rule 3 - Blocking] EvidenceRef docstring published a plan reference through resolve's inputSchema**
- **Found during:** Task 1 (row test `test_no_published_input_schema_names_a_plan`)
- **Issue:** `resolve`'s `$defs` embeds `EvidenceRef`'s docstring, which cited "T-04-07" and "04-04" (matches `\d\d-\d\d`). `databasise/seam/evidence.py` is not in the plan's file list, but the plan's truth cannot hold without editing it.
- **Fix:** one-sentence docstring rewrite, no behaviour change.
- **Files modified:** `databasise/seam/evidence.py`
- **Commit:** 2410ede

**3. [Process] An unconfigured `ruff format` run reformatted whole files**
- Ran `ruff format` from the repo root, which used the 88-column default instead of the code's ~110. I reverted the three affected source files with `git checkout -- <file>` and re-applied only the intended edits. The final diffs contain no formatting churn.

## Known Stubs

None.

## Threat Flags

None. T-15-19 is mitigated: four row nodes forbid plan, phase, arm and part tokens in descriptions and schemas.

## Self-Check: PASSED

- `databasise/tests/mcp/test_tool_descriptions.py` exists; commits 2410ede and f50c36d are ancestors of HEAD.

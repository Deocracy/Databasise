---
phase: 11-lightrag-corpus-path
plan: 09
subsystem: api
tags: [lightrag, health, d-14, d-12, q5, lrag-13, lrag-14, lrag-06]
status: complete

requires:
  - phase: 11-03
    provides: the facade-free driver health op returning {configured, missing_keys, unsupported_keys}, and the interim storages_initialized bridge this plan removes
  - phase: 11-06
    provides: jobs.db created only by the first job record (lazy)
  - phase: 11-07
    provides: the v1-not-configured key check the driver health op reports from
provides:
  - "HealthReport.engine_reason: str | None (fixed text, key names only, never values; Q5, D-12)"
  - "HealthReport.engine is exactly {interpreter_present, working_dir_present, v1_reachable}; storages_initialized is gone"
  - "working_dir_present is an engine-side Path.exists() check, kept true when the driver call fails"
  - "status ok needs every store ok, every engine fact true and both llm and embedding clients (D-14 amends Phase 8 D-08)"
  - "a probe that raises reports that store 'corrupted' (logged once, type name only); /health never answers 500"
affects: [LRAG-06, LRAG-13, LRAG-14, operator-console health panel]

estimate:
  tokens: 30000
  tasks: 2
actuals:
  tokens: 4700
  tasks: 2
  commits: 2
plan_head_before: a792c2efa9805b1225c6f2df4a371d070dfd17a5
plan_head_after: a26e72edf1b5236696df2c83736defa2e6900be5

tech-stack:
  added: []
  patterns:
    - "health reasons collected in a fixed order and joined with '; ', None when nothing is wrong"
    - "per-probe containment: each read-only probe wrapped so a raise becomes 'corrupted'"

key-files:
  created:
    - databasise/tests/seam/test_health_honesty.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/corpus.py
    - databasise/tests/seam/test_corpus_status.py

key-decisions:
  - "engine_reason order: 'v1 not configured: missing <keys>', 'v1 backend unsupported: <keys>', 'v1 unreachable', 'v1 interpreter missing', 'model clients not configured'"
  - "A failed driver health call and a raising probe are logged with the exception type name only, because a subprocess error's text can carry driver stderr"
  - "rerank stays optional for ok (Phase 8 D-09); only llm and embedding are required"

requirements-completed: [LRAG-13, LRAG-14, LRAG-06]

duration: 30min
completed: 2026-10-18
---

# Phase 11 Plan 09: Honest, write-free /health Summary

**GET /health now writes nothing, reports `v1_reachable` instead of `storages_initialized`, names missing v1 keys in a new `engine_reason` field, needs both model clients for `ok`, and reports a raising probe as a `corrupted` store instead of a 500.**

## Performance

- Duration: about 30 min
- Completed: 2026-10-18
- Tasks: 2 (1 tracer, 1 TDD)
- Files: 1 created, 3 modified

## Accomplishments

- `HealthReport.engine_reason` added as an optional field (default `None`). The docstring now lists the engine keys `interpreter_present`, `working_dir_present` and `v1_reachable`, says `engine_reason` names keys and never values, records the D-14 amendment of Phase 8 D-08, and states that a single-modality install reads `degraded`.
- `Databasise.health()` checks the v1 working dir's existence itself. `v1_reachable` is `bool(result["configured"])` from the facade-free driver op. The 11-03 bridge that stored `configured` under `storages_initialized` is removed.
- `ok` now needs `llm` and `embedding` in `self.clients`. Without them the reason is `model clients not configured`.
- Each read-only probe is wrapped: a raise reports that store as `corrupted`, so GET /health stays 200 `degraded`.
- The `_HEALTH_PROBES` list and the probes are unchanged, so the HippoRAG namespaces are still reported (STOR-04).

## Task Commits

1. **Task 1 (tracer): GET /health writes nothing and names the missing v1 keys** - `a06be06` (feat)
2. **Task 2 (TDD): health is not ok without model clients and degrades when a probe raises** - `a26e72e` (feat)

## TDD / test evidence

### Task 1 (tracer): `tests/seam/test_health_honesty.py`

- **RED** (unchanged source): `2 failed in 3.17s`. The fresh-root case failed on the engine key set (`Extra items in the left set: 'storages_initialized' / right set: 'v1_reachable'`). Its tree-unchanged and no-`lightrag-v1`/no-`jobs.db` assertions, which come before that check, already passed. The missing-key case failed with `KeyError: 'v1_reachable'`.
- **GREEN**: `pytest -q tests/seam/test_health_honesty.py tests/seam/test_health_probe.py tests/seam/test_corpus_adapter_failures.py` gave `39 passed in 8.22s`, 0 skipped (`v1/.venv/bin/python` is present, so both real-driver cases ran).
- **Tracer gate**: the verify command was re-run after the lint fixes: `39 passed in 8.03s`.

### Task 2 (TDD): new cases in `test_health_honesty.py` plus the `test_corpus_status.py` rewrite

- **Pin check first**: the protected files `tests/seam/test_health_probe.py` and `tests/seam/test_corpus_adapter_failures.py` were read in full with the Read tool, and every pin holds. Every `status` assertion expects `degraded`, which the new client rule only reinforces. The store keys and states are unchanged. Neither file reads `engine` or `clients`. Adapter failures still expect 200 `degraded`. `_make_fake_run_corpus_op()` is still called with no arguments. The protected `tests/seam/test_rest_corpus_endpoints.py` compares REST health with in-process health, and both now carry `engine_reason`. Neither protected file was edited.
- **RED**: `3 failed, 3 passed in 5.25s`. `test_status_is_ok_only_with_both_model_clients` and `test_rest_health_without_clients_is_degraded` failed with `assert 'ok' == 'degraded'`. `test_a_raising_probe_is_a_200_degraded_report_with_that_store_corrupted` failed with `assert 500 == 200` (Internal Server Error). `test_a_driver_failure_keeps_the_working_dir_fact` already passed, because Task 1 made `working_dir_present` an engine-side check.
- **GREEN**: `pytest -q tests/seam/test_health_honesty.py tests/seam/test_corpus_status.py tests/seam/test_health_probe.py tests/seam/test_rest_corpus_endpoints.py` gave `44 passed in 11.73s`.
- **Broad verify**: `pytest -q tests/seam tests/mcp tests/launcher tests/stores` gave `1076 passed in 285.93s`.
- **Full offline gate**: `.venv/bin/python tools/check_offline_suite.py` exited 0 (`pytest -q -rs: 2001 passed, 4 deselected in 473.04s`; `python -m pytest -q -rs: 2001 passed, 4 deselected in 469.48s`).

## Self-Check: PASSED

- Files exist: databasise/tests/seam/test_health_honesty.py, databasise/seam/engine.py, databasise/seam/corpus.py, databasise/tests/seam/test_corpus_status.py.
- Commits a06be06 and a26e72e are ancestors of HEAD.
- `engine_reason` appears in both corpus.py and engine.py, `v1_reachable` and `model clients not configured` appear in engine.py, `corrupted` appears in `health()`, and `storages_initialized` appears in neither source file.

## Files Created/Modified

- `databasise/seam/corpus.py`: `HealthReport.engine_reason` and the amended docstring.
- `databasise/seam/engine.py`: `health()` engine facts, reasons, the client requirement for `ok`, and per-probe containment.
- `databasise/tests/seam/test_health_honesty.py` (new): two real-driver cases (fresh-root tree unchanged and the engine key set; blank `EMBEDDING_DIM` named with no overlay value) and four fake-driver cases (clients rule in-process and over REST, the working-dir fact surviving a driver failure, a raising probe giving 200 with `kv:text_chunks` `corrupted` and the HippoRAG keys still present).
- `databasise/tests/seam/test_corpus_status.py` (unprotected): `_make_fake_run_corpus_op` now takes `configured`, `missing_keys` and `unsupported_keys` and feeds the stub's `_stub_*` keys. It stays callable with no arguments. Three D-14 assertion rewrites, each with a one-line reason.

## Decisions Made

See `key-decisions` in the frontmatter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security] Log the exception type name only**
- **Found during:** Task 1
- **Issue:** The plan says to log the driver exception once at warning. A `CorpusOpSubprocessError`'s text carries driver stderr, so logging it in full could put paths or configuration text in the log (T-11-19).
- **Fix:** The driver-failure and probe-failure warnings log `type(exc).__name__` only.
- **Files modified:** databasise/seam/engine.py
- **Commits:** a06be06, a26e72e

**2. [Rule 3 - Blocking] Lint compliance in the new test file**
- **Found during:** Task 1
- **Issue:** ruff flagged I001 (it sorts `fastapi` after `databasise` in this repo) and F811 on the `real_v1` fixture parameter.
- **Fix:** Reordered the imports and used the house `# noqa: F811` pattern from `test_v1_driver_protocol.py`. `# noqa: BLE001` was added on the two intentional blind excepts in `health()`.
- **Files modified:** databasise/tests/seam/test_health_honesty.py, databasise/seam/engine.py
- **Commit:** a06be06

No other deviations. Task 1 placed the "model clients not configured" reason, and Task 2 added the matching `ok` gate, as the plan split them.

## Deferred Issues

- Pre-existing ruff findings, out of scope and not touched: I001, RUF100 x2 and ASYNC230 in `seam/engine.py`; UP037 x2 and RUF022 in `seam/corpus.py`; I001 in `tests/seam/test_corpus_status.py` (its import lines are unchanged).
- `docs/gui/API-INVENTORY.md`, `docs/gui/CODEBASE-MAP.md` and `docs/gui/DEFECTS.json` still describe `storages_initialized`. These are the operator-console research records of the old defect, so they were not changed here.

## Known Stubs

None.

## Threat Flags

None. The plan's T-11-19 (no values in `engine_reason`, asserted by the real-driver test) and T-11-20 (the tree-snapshot test) are both mitigated.

## Next Phase Readiness

LRAG-13, LRAG-14 and LRAG-06's /health clause pass through the real driver. The ledger rows still need the phase verifier.

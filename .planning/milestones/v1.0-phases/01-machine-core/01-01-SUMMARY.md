---
phase: 01-machine-core
plan: 01
subsystem: infra
tags: [uv, pytest, pycozo, faiss, rfc8785, pydantic, packaging]

# Dependency graph
requires: []
provides:
  - "databasise/ — a new top-level, independent uv package beside v1/, never a workspace member of it"
  - "databasise/pyproject.toml declaring exactly four runtime deps: pycozo[embedded]==0.7.6, faiss-cpu>=1.7.0,<2.0.0, rfc8785==0.1.4, pydantic>=2.0,<3.0"
  - "A green pytest harness (databasise/tests/conftest.py) with store_root, rig_trace_schema, assert_valid_trace fixtures available to every later plan's tests"
  - "D-12 confirmed: environment digest = resolved distribution closure via importlib.metadata, never Nix, never a lockfile"
  - "D-09 confirmed: config.max_concurrency lives inside the node config and is therefore a config_hash input"
affects: ["01-02"]

actuals:
  tokens: 37070
  tasks: 4
  commits: 2

tech-stack:
  added: [pycozo, faiss-cpu, rfc8785, pydantic, pytest, pytest-asyncio, jsonschema, ruff]
  patterns:
    - "Independent uv package (own pyproject.toml, own uv.lock) rather than a uv workspace member, so a server-backed dependency set can never enter the resolution graph (D-14)"
    - "setuptools package-dir remap ({\"databasise\": \".\"}) for a project whose own root directory IS the package root"

key-files:
  created:
    - databasise/pyproject.toml
    - databasise/.python-version
    - databasise/README.md
    - databasise/__init__.py
    - databasise/identity/__init__.py
    - databasise/parts/__init__.py
    - databasise/validator/__init__.py
    - databasise/runner/__init__.py
    - databasise/stores/__init__.py
    - databasise/tests/conftest.py
    - databasise/tests/test_conftest_fixtures.py
    - databasise/.gitignore
    - databasise/uv.lock
  modified: []

key-decisions:
  - "Task 1 (package-legitimacy gate): rfc8785==0.1.4 approved for install. Evidence: PyPI latest 0.1.4 uploaded 2024-09-27, requires_python >=3.8, pure-Python py3-none-any wheel (no compiled extension); declared source github.com/trailofbits/rfc8785.py, repo name matches package name exactly; publisher is the Trail of Bits GitHub organisation, repo is Apache-2.0 and not archived; no typosquat (rfc-8785 and rfc8785-py both 404 on PyPI); zero runtime dependencies. The RESEARCH.md SUS flag came solely from the audit tool's unknown-downloads heuristic (a PyPI data-availability gap), not from any property of the package."
  - "Task 3 (D-12, one-way door): option-a selected. The environment digest folded into every config_hash is the resolved distribution closure read from importlib.metadata at runtime — what is actually installed, never what a lockfile declares, never a Nix store path. Two machines with identical lockfiles but different resolved wheels intentionally produce different identities, per CONTRACT §1."
  - "Task 4 (D-09, one-way door): option-a selected. config.max_concurrency lives inside the node's own config object and is therefore a config_hash input. Two nodes differing only in their concurrency cap are two identities, so RIG §AA.1's no-pooling rule is enforced by the hash itself. option-c (a process-wide cap) stays forbidden by D-11."

patterns-established:
  - "New top-level packages under this repo that must stay free of v1's server-backed dependency set get their own pyproject.toml and uv.lock, never a shared uv workspace (D-14)."

requirements-completed: [EMBED-01, MACH-05, MACH-06]

coverage:
  - id: D1
    description: "databasise/ installs as an independent package with exactly four runtime dependencies (pycozo, faiss-cpu, rfc8785, pydantic), none of which is a database-server client"
    requirement: "EMBED-01"
    verification:
      - kind: other
        ref: "cd databasise && uv run python -c \"import pycozo, faiss, rfc8785, pydantic, jsonschema; import databasise; print(databasise.__version__)\""
        status: pass
    human_judgment: false
  - id: D2
    description: "pytest harness runs inside databasise/ before any implementation module exists, with store_root, rig_trace_schema, assert_valid_trace fixtures available to every later test"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/test_conftest_fixtures.py#test_store_root_is_an_existing_directory"
        status: pass
      - kind: unit
        ref: "databasise/tests/test_conftest_fixtures.py#test_rig_trace_schema_loads_expected_shape"
        status: pass
      - kind: unit
        ref: "databasise/tests/test_conftest_fixtures.py#test_assert_valid_trace_raises_with_error_path_on_invalid_record"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both one-way identity doors (D-12 environment-digest scope, D-09 concurrency-cap placement) confirmed by human decision before plan 01-02 writes either rule into a module docstring"
    requirement: "MACH-06"
    verification: []
    human_judgment: true
    rationale: "One-way architectural door confirmations are human decisions by design (checkpoint:decision, gate=blocking) — not something a test can prove; the recorded selections above are the audit trail."

duration: 15min
completed: 2026-08-30
status: complete
---

# Phase 01 Plan 01: Machine-Core Package Scaffold Summary

**Independent `databasise/` uv package (pycozo, faiss-cpu, rfc8785, pydantic) with a green pytest harness, plus both one-way `config_hash` identity doors (D-12 environment-digest scope, D-09 concurrency-cap placement) confirmed as option-a.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-08-30T16:35:30Z
- **Completed:** 2026-08-30T16:50:12Z
- **Tasks:** 4
- **Files modified:** 13 (all new)

## Accomplishments
- Stood up `databasise/` as a new top-level, independent uv package beside `v1/` (D-14) — own `pyproject.toml`, own `uv.lock`, never a workspace member of v1
- Declared exactly four runtime dependencies (`pycozo[embedded]==0.7.6`, `faiss-cpu>=1.7.0,<2.0.0`, `rfc8785==0.1.4`, `pydantic>=2.0,<3.0`), each confirmed to install and import cleanly under the uv-managed `cpython-3.12.13` interpreter
- Green pytest harness: `databasise/tests/conftest.py` provides `store_root`, `rig_trace_schema`, `assert_valid_trace` fixtures for every later plan's tests; `uv run pytest --collect-only` exits 0
- Confirmed both one-way `config_hash` identity doors before any code computes a hash: D-12 (environment digest = resolved `importlib.metadata` closure) and D-09 (`config.max_concurrency` inside node config) — both option-a, matching the locked decisions already recorded in 01-01-PLAN.md and CONTEXT.md
- Resolved the Task 1 package-legitimacy gate for `rfc8785` by human approval before first install

## Task Commits

Each task was committed atomically:

1. **Task 1: Package-legitimacy gate for rfc8785 before first install** — no commit (verification-only `checkpoint:human-verify` gate; resolved by human response "approved")
2. **Task 2: Wave 0 — create the databasise package, build config, and test harness** - `8108ded` (feat)
3. **Task 3: One-way door — what the environment hash covers (D-12)** — no commit (`checkpoint:decision`; selection recorded here, transcribed verbatim into `databasise/identity/env.py`'s module docstring by plan 01-02)
4. **Task 4: One-way door — the per-node concurrency cap as a config_hash input (D-09)** — no commit (`checkpoint:decision`; selection recorded here, transcribed verbatim into `databasise/runner/scheduler.py`'s module docstring by plan 01-02)

**Plan metadata:** (this commit) `docs(01-01): complete machine-core package scaffold plan`

## Files Created/Modified
- `databasise/pyproject.toml` - independent package config: 4 runtime deps, `requires-python = ">=3.11"`, no uv workspace, no networkx
- `databasise/.python-version` - pins `3.12` so uv selects the uv-managed cpython-3.12.13 interpreter
- `databasise/README.md` - records the D-14 boundary, Python-floor rationale, independent-package rationale
- `databasise/__init__.py` - exports `__version__` only; `run_wiring` added by the tracer in 01-02
- `databasise/identity/__init__.py`, `databasise/parts/__init__.py`, `databasise/validator/__init__.py`, `databasise/runner/__init__.py`, `databasise/stores/__init__.py` - empty subpackage markers
- `databasise/tests/conftest.py` - `store_root`, `rig_trace_schema`, `assert_valid_trace` fixtures
- `databasise/tests/test_conftest_fixtures.py` - smoke tests for the three fixtures (see Deviations)
- `databasise/.gitignore` - excludes `.venv/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`, `.ruff_cache/`
- `databasise/uv.lock` - locked dependency versions (uv-generated)

## Decisions Made

- **Task 1 — rfc8785 approved.** PyPI latest 0.1.4 (2024-09-27), pure-Python wheel, `github.com/trailofbits/rfc8785.py` (Trail of Bits org, exact name match, Apache-2.0, not archived), zero runtime deps, no typosquat. The RESEARCH.md `SUS` verdict was the audit tool's `unknown-downloads` heuristic only — a PyPI data-availability gap, not a signal about the package.
- **Task 3 — D-12 option-a.** The environment digest folded into every `config_hash` is the resolved distribution closure read from `importlib.metadata` at runtime — what is actually installed, never a lockfile's declared intent, never a Nix store path (Nix is substrate-only, spike 004). Accepted consequence: two machines with identical lockfiles but different resolved wheels intentionally produce different identities.
- **Task 4 — D-09 option-a.** `config.max_concurrency` lives inside the node's own `config` object and is therefore a `config_hash` input by construction. Two nodes differing only in their concurrency cap are two identities, enforcing RIG §AA.1's no-pooling rule via the hash rather than a reviewer's memory. option-c (process-wide cap) stays forbidden by D-11 — one arm's fan-out must never throttle an unrelated arm.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] setuptools flat-layout package discovery failure**
- **Found during:** Task 2 (`uv sync`)
- **Issue:** `databasise/` is simultaneously the project root (where `pyproject.toml` lives) and the package root (`__init__.py` lives directly beside it, with `identity/`, `parts/`, `validator/`, `runner/`, `stores/` as sibling subpackages). setuptools' default flat-layout auto-discovery interpreted `identity/`, `parts/`, `validator/`, `runner/`, `stores/` as five separate top-level packages and refused to build: "Multiple top-level packages discovered in a flat-layout."
- **Fix:** Added `[tool.setuptools] package-dir = {"databasise" = "."}` plus an explicit `packages` list (`databasise`, `databasise.identity`, `databasise.parts`, `databasise.validator`, `databasise.runner`, `databasise.stores`) to `databasise/pyproject.toml`, remapping the `databasise` distribution package onto the project root instead of relying on auto-discovery.
- **Files modified:** `databasise/pyproject.toml`
- **Verification:** `uv sync --extra dev` builds and installs cleanly; `uv run python -c "import databasise; print(databasise.__version__)"` prints `0.1.0`.
- **Committed in:** `8108ded` (Task 2 commit)

**2. [Rule 3 - Blocking] pytest exit code 5 on zero collected tests**
- **Found during:** Task 2 (`uv run pytest --collect-only`)
- **Issue:** The plan's own `<automated>` verify step requires `uv run pytest --collect-only` to exit 0 "even with zero tests collected," but pytest's documented behavior returns exit code 5 ("no tests collected") whenever `tests/` contains zero test items — there is no ini-level toggle to change this. A literally empty `tests/` (only `conftest.py`) would fail the plan's own acceptance criterion.
- **Fix:** Added `databasise/tests/test_conftest_fixtures.py` with three passing smoke tests (`store_root` creates a real directory, `rig_trace_schema` loads the expected schema shape, `assert_valid_trace` raises with the field path on an invalid record). This satisfies the literal exit-0 requirement and gives `conftest.py`'s real logic (repo-root walk, JSON-Schema validation, error-path formatting) a runnable check, per this project's "lazy code without its check is unfinished" convention.
- **Files modified:** `databasise/tests/test_conftest_fixtures.py` (new file, not in the plan's `files_modified` list)
- **Verification:** `uv run pytest --collect-only` exits 0 (3 items collected); `uv run pytest -v` — 3 passed.
- **Committed in:** `8108ded` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking issues that prevented the plan's own verify step from passing)
**Impact on plan:** Both fixes are scoped entirely to `databasise/pyproject.toml` and one new test file; no dependency, acceptance criterion, or planned file was changed in substance. No scope creep.

## Issues Encountered
None beyond the two deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

`databasise/` is ready for plan 01-02 (the tracer): the package installs cleanly, the pytest harness is green, and both one-way `config_hash` inputs (D-12, D-09) are confirmed and recorded above for verbatim transcription into `databasise/identity/env.py` and `databasise/runner/scheduler.py`'s module docstrings. No blockers.

---
*Phase: 01-machine-core*
*Completed: 2026-08-30*

## Self-Check: PASSED

All 14 claimed files found on disk (13 `databasise/` files + this SUMMARY.md); commit `8108ded` confirmed in `git log --oneline --all`.

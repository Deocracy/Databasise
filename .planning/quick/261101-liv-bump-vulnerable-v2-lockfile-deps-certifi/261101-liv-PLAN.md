---
quick_id: 261101-liv
type: quick
created: 2026-11-01
files_modified: [databasise/uv.lock]
---

# Bump vulnerable v2 lockfile dependencies

Clear the 17 open Dependabot alerts on `databasise/uv.lock` (owner decision 2026-11-01: "Bump now"; leave `v1/uv.lock` untouched).

| Package | Locked | Target | Alerts |
|---------|--------|--------|--------|
| certifi | 2026.7.22 | >= 2026.10.18 | 1 critical (compromised emSign CAs) |
| PyJWT (via `mcp[crypto]`) | 2.13.0 | >= 2.15.0 if `mcp` allows, else >= 2.14.0 | 15 (1 critical); one has no fix yet |
| opentelemetry-api (transitive) | 1.44.0 | >= 1.45.1 | 1 medium |

## Task 1: upgrade only these three packages and prove the suite

1. From `databasise/`: `uv lock --upgrade-package certifi --upgrade-package pyjwt --upgrade-package opentelemetry-api` (network allowed for this resolve). If opentelemetry-api's upgrade forces opentelemetry-sdk or another sibling, let uv move it and report the diff.
2. `git diff --stat databasise/uv.lock` and list every package whose version changed. Anything beyond the three targets and their forced siblings is a stop-and-report.
3. `uv sync --frozen` (keep the extras the venv already has, including `mcp`, the dev group and playwright).
4. Full offline suite from `databasise/`: `uv run pytest -q -p no:randomly`. Expected: 3377 passed; the namespace-wide socket-count test `tests/test_phase_success_criteria.py::test_criterion_1_library_startup_with_no_external_server` may fail only if another process opens a port, and must pass when rerun alone. Also run the console suite with `PLAYWRIGHT_BROWSERS_PATH` and `DATABASISE_REQUIRE_BROWSER=1` exported.
5. Commit `databasise/uv.lock` alone as `fix(deps): bump certifi, PyJWT and opentelemetry-api in the v2 lockfile` with a trailer block (a `phase/18` line, then the co-author line). The orchestrator pushes.

Verify: locked versions meet the targets; full suite green; `git status` shows only `databasise/uv.lock` committed and `v1/uv.lock` unchanged.

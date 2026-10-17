---
phase: 08-run-the-engine
plan: 06
subsystem: infra
tags: [mcp, stdio, console-script, flock, store-lock, httpx, launcher]

requires:
  - phase: 08-run-the-engine
    provides: "08-01 launcher package, store_lock.py and the databasise-rest console script"
  - phase: 08-run-the-engine
    provides: "08-05 rerank client that imports httpx at runtime"
provides:
  - "databasise-mcp console script and python -m databasise.launcher.serve_mcp (stdio, sse, streamable-http)"
  - "examples/mcp-client.stdio.json example MCP client config"
  - "httpx declared as a runtime dependency"
  - "cross-process proof of one engine process per store root, plus in-process lock tests"
affects: [08-07, 08-08, 08-10, console phases 16-18]

actuals:
  tokens: 6500
  tasks: 2
  commits: 2
plan_head_before: 6bda358f3aadaa9eae6b35c9afb2ac7a9a75e5d1
plan_head_after: b1250a4ced06203be3c883b7c27703ec8c45c4c4
commits: 2

tech-stack:
  added: []
  patterns:
    - "MCP launcher reuses the shared lock-then-clients start sequence; create_server is imported after the lock is taken"
    - "stdout is never written by the launcher; refusals go to stderr through refuse()"

key-files:
  created:
    - databasise/launcher/serve_mcp.py
    - databasise/examples/mcp-client.stdio.json
    - databasise/tests/launcher/test_store_lock.py
  modified:
    - databasise/pyproject.toml
    - databasise/uv.lock
    - databasise/README.md
    - databasise/tests/launcher/test_launchers.py

key-decisions:
  - "No change to store_lock.py: all six in-process lock edge tests passed against the 08-01 implementation"
  - "The example client config is examples/mcp-client.stdio.json, not a repo-root .mcp.json, so no Claude Code session auto-starts the engine and holds the parity store lock"

requirements-completed: [RUN-06, RUN-07]

coverage:
  - id: D1
    description: "databasise-mcp --transport stdio, spawned through the real mcp SDK client, lists the same nine tool names as create_server in-process and as TOOL_NAMES"
    requirement: "RUN-06"
    verification:
      - kind: integration
        ref: "databasise/tests/launcher/test_launchers.py#test_databasise_mcp_stdio_lists_the_in_process_tool_set"
        status: pass
    human_judgment: false
  - id: D2
    description: "Both console scripts are installed entry points; both python -m modules print help and exit 0; sse and streamable-http reach server.run with host and port"
    requirement: "RUN-06"
    verification:
      - kind: unit
        ref: "databasise/tests/launcher/test_launchers.py#test_both_console_scripts_are_installed_entry_points"
        status: pass
      - kind: unit
        ref: "databasise/tests/launcher/test_launchers.py#test_python_m_modules_print_help"
        status: pass
      - kind: unit
        ref: "databasise/tests/launcher/test_launchers.py#test_databasise_mcp_passes_each_transport_to_the_server_run_method"
        status: pass
    human_judgment: false
  - id: D3
    description: "The example MCP client config parses and invokes databasise-mcp over stdio with absolute store-root and env-file paths"
    requirement: "RUN-06"
    verification:
      - kind: unit
        ref: "databasise/tests/launcher/test_launchers.py#test_example_mcp_config_invokes_databasise_mcp_over_stdio"
        status: pass
    human_judgment: false
  - id: D4
    description: "A second databasise-rest and a databasise-mcp on a held store root exit non-zero naming the root and holder PID; the refused stdio launcher writes nothing to stdout; the first launcher keeps answering /health 200; a released root can be launched again"
    requirement: "RUN-07"
    verification:
      - kind: integration
        ref: "databasise/tests/launcher/test_launchers.py#test_second_launcher_on_a_held_store_root_exits_with_the_store_lock_error"
        status: pass
      - kind: integration
        ref: "databasise/tests/launcher/test_launchers.py#test_a_released_store_root_can_be_launched_again"
        status: pass
    human_judgment: false
  - id: D5
    description: "In-process lock edges: missing root created with PID, same-process re-acquire refused with this PID, symlink and relative spellings refused, no-PID holder reported as unknown, release on context exit, non-inheritable fd"
    requirement: "RUN-07"
    verification:
      - kind: unit
        ref: "databasise/tests/launcher/test_store_lock.py (6 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Two launchers started at the same instant: exactly one acquires the lock"
    requirement: "RUN-07"
    verification: []
    human_judgment: true
    rationale: "Atomicity of flock(LOCK_EX | LOCK_NB) is a kernel guarantee; the plan marks this truth as backstop and no simultaneous-start test was written."

duration: ~20min (start time not captured)
completed: 2026-10-16
status: complete
---

# Phase 8 Plan 6: MCP launcher and one-engine-per-store-root proof Summary

**`databasise-mcp` console script serving the nine §18 tools over stdio, sse or streamable-http behind the same store flock as `databasise-rest`, with `httpx` promoted to a runtime dependency and cross-process tests proving a second launcher is refused by name while the first keeps answering `/health`.**

## Performance

- **Duration:** about 20 min (start time not captured)
- **Completed:** 2026-10-16
- **Tasks:** 2
- **Files modified:** 7 (3 created, 4 modified)

## Accomplishments

- `launcher/serve_mcp.py`: `build_parser()` (shared engine flags, `--transport`, default `stdio`, default port 8001) and `main()`; lock first, then `create_server`, then `server.run`. No `print(` in the module; stdout stays free for the protocol.
- `databasise-mcp` entry point added; `httpx>=0.28.1` is now in `[project].dependencies` (kept in the dev group), `uv.lock` gained two `httpx` lines and no package. The venv was reinstalled with `uv sync --inexact --extra rest --extra mcp --reinstall-package databasise`.
- `examples/mcp-client.stdio.json` and a README "Run the engine" section.
- A stdio subprocess driven through the real SDK client (imported with `import_real_mcp`) lists tool names equal to the in-process set and to `TOOL_NAMES` (nine).
- Second `databasise-rest` and `databasise-mcp --transport stdio` on a held root each exit non-zero within 30 s with the root, the holder PID and `one engine process per store root` on stderr; the refused stdio process wrote zero bytes to stdout; launcher A still answered `/health` 200. After A is terminated a new launcher on the same root serves `/health` 200.
- Six in-process tests in `test_store_lock.py` all passed against the 08-01 lock unchanged.

## Task Commits

1. **Task 1: databasise-mcp launcher, console script, httpx dependency, example config** - `97e5ef3` (feat)
2. **Task 2: one engine process per store root, cross-process and in-process** - `b1250a4` (test)

**Plan metadata:** the SUMMARY commit that carries this file.

## Verification

- `pytest -q tests/launcher/test_launchers.py` after Task 1: 14 passed (plan floor 9).
- `pytest -q tests/launcher tests/mcp` at the end: 55 passed (launcher 22, plan floor 17).
- Entry-point check printed `entry-points-ok`; `grep -c "print(" launcher/serve_mcp.py` prints 0; `databasise/mcp/serve_mcp.py` does not exist; `pgrep -f "databasise-(rest|mcp) --store-root /tmp"` printed nothing after the run.
- `ruff check launcher tests/launcher` clean. `ruff format --check` would reformat several files, including ones untouched by this plan (08-01 files and the pre-existing tests); the repo does not enforce it and nothing was reformatted.

## Deviations from Plan

None - plan executed exactly as written. Implementation notes, not deviations:
- `serve_mcp.main` imports `create_server` inside the lock `try` block, after the lock is taken, so a refused start never imports the mcp extra.
- The `launch` fixture in `test_launchers.py` gained a `stdout_path` attribute next to `stderr_path` so the empty-stdout assertion can read it.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: unauthenticated-network-endpoint | databasise/launcher/serve_mcp.py | `databasise-mcp --transport sse` or `streamable-http` serves the MCP tools on a TCP port with no authentication; default host is 127.0.0.1 and `--host` can widen it. stdio (the default) opens no port. |

## User Setup Required

None. To use the example client config, replace each `/ABSOLUTE/PATH/TO` prefix in `databasise/examples/mcp-client.stdio.json` with your own absolute path, and supply an env file (or keep the config minimal with `--no-clients`).

## Next Phase Readiness

- 08-07 and 08-08 can rely on `databasise-mcp` and the shared lock; the parity CLI lock integration (RUN-07) is theirs.
- The simultaneous-start truth stays backstop-only (kernel atomicity), with no dedicated test.

## Self-Check: PASSED

Created files exist (`launcher/serve_mcp.py`, `examples/mcp-client.stdio.json`, `tests/launcher/test_store_lock.py`); commits `97e5ef3` and `b1250a4` are ancestors of HEAD.

---
*Phase: 08-run-the-engine*
*Completed: 2026-10-16*

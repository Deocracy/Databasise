---
phase: 08-run-the-engine
reviewed: 2026-10-17T02:35:00Z
depth: standard
files_reviewed: 43
files_reviewed_list:
  - databasise/clients/builder.py
  - databasise/clients/rerank.py
  - databasise/clients/openai_compat.py
  - databasise/store_lock.py
  - databasise/launcher/__init__.py
  - databasise/launcher/serve_rest.py
  - databasise/launcher/serve_mcp.py
  - databasise/seam/rest.py
  - databasise/seam/corpus.py
  - databasise/seam/engine.py
  - databasise/foreign/_mcp_sdk_guard.py
  - databasise/parity/run_arm.py
  - databasise/parity/import_index.py
  - databasise/parity/build_hipporag_index.py
  - databasise/parity/run_comparison.py
  - databasise/parity/run_cross_modality.py
  - databasise/parity/storage_audit.py
  - databasise/tools/check_offline_suite.py
  - databasise/pyproject.toml
  - databasise/examples/mcp-client.stdio.json
  - databasise/evidence/COVERAGE.md
  - databasise/README.md
  - databasise/tests/conftest.py
  - databasise/tests/clients/test_build_clients.py
  - databasise/tests/clients/test_rerank_client.py
  - databasise/tests/clients/test_openai_compat.py
  - databasise/tests/foreign/__init__.py
  - databasise/tests/foreign/test_mcp_sdk_guard.py
  - databasise/tests/launcher/__init__.py
  - databasise/tests/launcher/test_launchers.py
  - databasise/tests/launcher/test_store_lock.py
  - databasise/tests/launcher/test_bind_guard.py
  - databasise/tests/mcp/test_tool_growth_invariant.py
  - databasise/tests/parity/test_embedder_index_reproduction.py
  - databasise/tests/parity/test_naive_arm_end_to_end.py
  - databasise/tests/parity/test_parity_cli_store_lock.py
  - databasise/tests/parity/test_retrieval_parity.py
  - databasise/tests/seam/test_corpus_status.py
  - databasise/tests/seam/test_rest_corpus_endpoints.py
  - databasise/tests/seam/test_rest_cors.py
  - databasise/tests/seam/test_token_accounting.py
  - databasise/tests/test_check_offline_suite.py
  - databasise/tests/test_embed_startup.py
findings:
  critical: 0
  warning: 0
  info: 7
  total: 7
status: clean
---

# Phase 08: Code Review Report (iteration 3, final)

**Reviewed:** 2026-10-17T02:35:00Z
**Depth:** standard
**Files Reviewed:** 43 (iteration-1 scope; iteration 3 re-read the 14 files changed by `81a39fb..HEAD`)
**Status:** clean (no Critical or Warning findings; 7 Info items remain)

## Summary

Both iteration-2 warnings are resolved in code. The 113 offline tests under `tests/clients/test_rerank_client.py`, `tests/launcher` and `tests/parity/test_cli_builder_refusals.py` pass. I did not run the larger suites or any `-m live` test, and I did not read any `v1/.env*` file.

- **Iteration-2 WR-01 (OverflowError) is resolved.** `databasise/clients/rerank.py:75-82` rejects bools and non-numbers first, then wraps `math.isfinite` in `try/except OverflowError` and returns False. A 400-digit integer score therefore reaches the existing `RerankResponseError` path. The test case is at `databasise/tests/clients/test_rerank_client.py:231` (400 nines in the first result's `relevance_score`), inside the "refused by name" parametrize list.
- **Iteration-2 WR-02 (BUILDER_REFUSALS everywhere) is resolved.** I grepped `build_clients` and `_build_clients` across `databasise/` outside tests. There are nine call sites, and each sits under a handler that names `BUILDER_REFUSALS`:

  | Call site | Handler |
  |---|---|
  | `parity/run_arm.py:190` | `main`, `:250` |
  | `parity/storage_audit.py:188` | `main`, `:247` |
  | `parity/run_cross_modality.py:310` | `main`, `:395-402` |
  | `parity/build_hipporag_index.py:175` | `main`, `:339-345` |
  | `eval/aa_run.py:548` | `:549` |
  | `eval/corpus_ingest.py:219` | `:220` |
  | `eval/remint.py:122` | `:123` |
  | `parity/run_comparison.py:553` | per-query catch, `:701` |
  | `launcher/__init__.py:119` | `LAUNCH_REFUSALS` splices the tuple, `:35-41` |

  `BUILDER_REFUSALS` is defined at `clients/builder.py:151-156` and exported in `__all__` (`:25`). It holds the four named errors the builder raises. `storage_audit` no longer imports `run_arm._CLI_REFUSALS`, which is gone. No other module outside the builder calls the builder.
- **Regression check on `git diff 81a39fb HEAD`:** no regression found.
  - Exit codes and the `print(str(exc), file=sys.stderr)` style are unchanged in every CLI.
  - The tuple is the four named builder errors only. It is not a broad `Exception` or `ValueError` catch (`UnsupportedRerankBindingError` subclasses `ValueError`, but only the named class is caught). The eval CLIs wrap only `_load_env_file` and `_build_clients`.
  - In `run_arm`, `StoreLockedError` stays imported (`:58`) and the unused re-exports keep `# noqa: F401` (`:37`).
  - The new parametrised test covers seven CLIs and asserts a non-zero return, `RERANK_BINDING` named, the bad value absent and no traceback. It stubs the store open, so no RocksDB lock leaks.
- **Wildcard-host change (IN-05 part b) works.** `launcher/__init__.py:71-85` now refuses an empty host, `0`, `0.0` (through `socket.inet_aton`) and `::ffff:0.0.0.0`, and the test list at `tests/launcher/test_bind_guard.py:45` covers both launchers. One edge remains (IN-06 below).

Seam authentication is an open owner decision and is not reported.

## Info

### IN-01: MCP transport security accepts any loopback page on any port, while REST uses an exact-origin list (carried forward, unchanged)

**File:** `databasise/launcher/serve_mcp.py:39-40`
**Issue:** `allowed_origins` includes `http://localhost:*`, `http://127.0.0.1:*` and `http://[::1]:*`. Any local web page on any port can call the MCP HTTP transports. The REST launcher requires an exact `--cors-origin` and rejects cross-site writes with its origin guard, so the two surfaces differ.
**Fix:** Add a `--cors-origin` equivalent to `databasise-mcp` and allow only those origins, or state the any-loopback-origin policy in the README and the `serve_mcp` docstring.

### IN-02: Stale-PID race and fd leak in `acquire_store_lock` (carried forward, unchanged)

**File:** `databasise/store_lock.py:429-461`
**Issue:** A contender that loses `flock` reads the PID file immediately. If the new holder has not yet run `ftruncate`, the file still holds the previous process's PID, so the refusal can name a dead process. If `os.ftruncate` or `os.write` raises after the lock is taken (for example ENOSPC), `fd` is not closed, because the `except BaseException` block covers only the `flock` call.
**Fix:** Truncate and write the PID inside the same `try` as `flock`, with the same close-on-error handling.

### IN-03: Launcher refusals reuse parity wording, and the launcher imports the parity package for a default (carried forward, unchanged)

**File:** `databasise/clients/builder.py:46-47`, `databasise/clients/builder.py:60-63`, `databasise/launcher/__init__.py:25`
**Issue:** `MissingParityEnvError` and `MissingParityEnvKeyError` tell a `databasise-rest` operator to "see v1/README-PARITY.md ... or pass an explicit clients= mapping to run_arm()". `databasise.launcher` imports `databasise.parity.import_index` (numpy, faiss and cozo load at startup, and the default store path is computed from the source tree) only to read `DEFAULT_STORE_ROOT`. A non-editable install would point the default store into site-packages.
**Fix:** Let the launcher re-word the refusals in `refuse`, and move `DEFAULT_STORE_ROOT` to a light module, or require `--store-root` when the default path does not exist.

### IN-04: Lint violations in phase-08 files (carried forward; re-confirmed with `.venv/bin/ruff`)

**File:** `databasise/launcher/serve_rest.py:35` (I001, imports inside `build_app`), `databasise/parity/build_hipporag_index.py:40` (I001), `databasise/tests/conftest.py:18` (UP035), `databasise/tests/launcher/test_bind_guard.py:216` (RUF028, `# fmt: skip` inside an argument list)
**Issue:** `ruff check` reports exactly these four on code this phase added. The `# fmt: skip` comment cannot protect the intended formatting. The iteration-2 fixes added no new violations in these files.
**Fix:** Run `ruff check --fix` on the listed files and move the `# fmt: skip` to the statement it should cover.

### IN-05: The origin guard matches only literal same-origin forms (carried forward; part (a) of the old IN-05)

**File:** `databasise/launcher/serve_rest.py:54`
**Issue:** The same-origin set is built as `http://{name}:{port}` for every name. A browser omits the port when it is the scheme default, and an `https` origin (reverse proxy) never matches, so a same-origin write from `http://localhost` with `--port 80`, or from an `https://` front end, gets 403 unless it is added with `--cors-origin`. The failure is safe and the workaround exists. Part (b), the wildcard spellings, is fixed.
**Fix:** Document in the README that proxied or default-port origins must be listed with `--cors-origin`.

### IN-06: `_is_wildcard` raises `UnicodeEncodeError` for an argv host with undecodable bytes

**File:** `databasise/launcher/__init__.py:82-85`
**Issue:** The new `socket.inet_aton(name)` call is guarded by `except OSError`. A `--host` value that contains undecodable bytes arrives from argv as a surrogate-escaped string, and `inet_aton` then raises `UnicodeEncodeError` (a `ValueError`, not an `OSError`). I confirmed this with `socket.inet_aton("a\udcff")`. The path is reachable only with `--allow-remote-unauthenticated`: without the flag, `is_loopback_host` returns False first and `parser.error` runs. With the flag, the launcher prints a traceback instead of a refusal. The input is operator-supplied and the failure is a crash, not a bypass, so this is minor. `inet_aton` also accepts trailing text after whitespace (`"0 x"` returns the zero address), which only causes a harmless extra refusal.
**Fix:** `except (OSError, ValueError): return False`.

### IN-07: The `run_comparison` per-query catch is untested and repeats a config refusal for every query

**File:** `databasise/parity/run_comparison.py:701-704`
**Issue:** `compare_arm_on_query` builds clients on every call (`:553`), so a bad env or rerank binding now prints one identical `error comparing query ...` line per query and then exits 1 after the whole loop. This is correct and avoids the old traceback (previously `MissingParityEnvKeyError`, `UnparseableProviderRoutingError` and `UnsupportedRerankBindingError` escaped here), but a deterministic config error cannot succeed on later queries. The fixer's own report notes there is no test for this path.
**Fix:** Optional. Build clients once before the loop and refuse once, or add a small test that patches `compare_arm_on_query` to raise `UnsupportedRerankBindingError` and asserts `had_error` is True and the traceback is absent.

---

_Reviewed: 2026-10-17T02:35:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

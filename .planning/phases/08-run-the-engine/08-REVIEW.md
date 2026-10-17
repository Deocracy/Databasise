---
phase: 08-run-the-engine
reviewed: 2026-10-16T19:15:00Z
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
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-10-16T19:15:00Z
**Depth:** standard
**Files Reviewed:** 43
**Status:** issues_found

## Summary

The phase-08 diff is mostly sound. The store lock is correct (non-blocking flock, close-on-exec, kernel release on death). The env-file refusals do not echo values. The rerank client validates its responses strictly. The offline tests I ran pass (148 passed: clients, store lock, bind guard, CORS, offline gate, MCP guard, parity-CLI lock).

The concerns are mostly around the launcher edges:

- The exact-origin CORS list and the Host guard do not stop a cross-site web page from writing to the loopback REST app (WR-01).
- A configuration error that should be a clean refusal produces a traceback (WR-02).
- `--allow-remote-unauthenticated` cannot work for the wildcard binds it is most likely to be used with (WR-03).
- Rerank identity is not type-checked (WR-04).

No secret or env value leak was found. Seam authentication was treated as a deliberate open decision and is not reported.

## Warnings

### WR-01: Exact-origin CORS and the Host guard do not stop cross-site writes to the loopback REST app

**File:** `databasise/seam/rest.py:280-287`, `databasise/launcher/serve_rest.py:150-151`
**Issue:** CORS only controls whether a browser lets a page read a response. It does not stop the request from running. The only simple cross-origin request shape this app accepts is `POST /documents/upload` (multipart form), which needs no preflight. Any web page the operator visits can submit a form to `http://127.0.0.1:8000/documents/upload`. The request carries `Host: 127.0.0.1:8000`, so `TrustedHostMiddleware` passes it. DNS rebinding is not needed. I confirmed this against `serve_rest.build_app(...)` with `--cors-origin http://localhost:5173`: a `POST /documents/upload` with `Origin: http://evil.example` returned `200 {"job_id": ..., "enqueued": 1}`. The result is attacker-chosen documents written into the store and LLM and embedding tokens spent. `test_unlisted_origin_gets_no_allow_origin_header` only asserts the response header, so it passes while the write still happens. This is a web-page-to-loopback exposure, separate from the open seam-authentication decision, and it exists whether or not `--cors-origin` is passed.
**Fix:** Add a small middleware in `create_app` (or in the launcher) that rejects any non-GET/HEAD/OPTIONS request carrying an `Origin` header not in the allow-list, and rejects state-changing multipart requests whose `Origin` is absent or foreign. Add a test that posts to `/documents/upload` with a foreign `Origin` and expects 403.
```python
@app.middleware("http")
async def _origin_guard(request, call_next):
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin is not None and origin not in origins:
        return JSONResponse(status_code=403, content={"detail": "origin not allowed"})
    return await call_next(request)
```

### WR-02: Configuration errors in `build_clients` escape the launchers as tracebacks, and the rerank binding match is case-sensitive

**File:** `databasise/launcher/__init__.py:37-42`, `databasise/clients/builder.py:177-178`, `databasise/parity/run_arm.py:246-249`, `databasise/parity/storage_audit.py:244-247`
**Issue:** `build_clients` raises `UnsupportedRerankBindingError`, but `LAUNCH_REFUSALS` does not list it. I reproduced this: `databasise-rest --env-file ...` with `RERANK_BINDING=bogus` prints a full traceback instead of the clean `databasise: ...` refusal that every other env error gets. A missing, unreadable or non-UTF-8 env file (`PermissionError`, `IsADirectoryError`, `UnicodeDecodeError` from `read_text`) also escapes as a traceback. `RERANK_BINDING=Cohere` or `COHERE` is refused as unsupported, because the value is compared to `RERANK_BINDINGS` without lowercasing. The "null" and "off" check just above it does lowercase, so the two checks are inconsistent.

The new rerank keys also widen what the parity CLIs can raise. `run_arm.main` and `storage_audit.main` catch only `StoreLockedError` and `MissingParityEnvError`. A partial rerank key set in the parity env now raises `MissingParityEnvKeyError`, and a bad binding raises `UnsupportedRerankBindingError`. Both escape as tracebacks.
**Fix:** Add `UnsupportedRerankBindingError` and `OSError` / `UnicodeDecodeError` to `LAUNCH_REFUSALS`. Normalise the binding with `binding = binding.strip().lower()` before the membership test. In the parity CLIs, catch the builder's refusal classes (for example `except (StoreLockedError, MissingParityEnvError, MissingParityEnvKeyError, UnsupportedRerankBindingError, UnparseableProviderRoutingError)`).

### WR-03: `--allow-remote-unauthenticated` is unusable for wildcard binds because the Host allow-lists contain only the literal bound host

**File:** `databasise/launcher/serve_rest.py:150-151`, `databasise/launcher/serve_mcp.py:222-229`
**Issue:** With `--host 0.0.0.0` or `--host ::` and the opt-in flag, the Host allow-list becomes `localhost`, `127.0.0.1`, `[` and `0.0.0.0` (REST), or the equivalent MCP list. No remote client ever sends `Host: 0.0.0.0`, so every non-loopback request gets 400 (REST) or 421 (MCP). `test_bind_guard.py` only tests a concrete address (`192.168.1.5`), so the gap is not covered. The refusal message ("pass --allow-remote-unauthenticated to accept that") promises a mode that does not work for the most common remote-bind value. The failure is safe, but the flag is misleading.
**Fix:** Either refuse wildcard hosts (`0.0.0.0`, `::`) even with the flag and say "name the interface address", or add an explicit `--allowed-host` option (repeatable) feeding both allow-lists. Add a test that exercises `0.0.0.0` with the flag.

### WR-04: Rerank identity and scores are not type-checked

**File:** `databasise/clients/rerank.py:348-353`, `databasise/clients/rerank.py:274-275`
**Issue:** `identity = body.get("model") or self._model` takes any truthy value from the response. A non-string `model` (a dict, a number) flows into `resolved_model_identity` and `TokenAccounting.counted_by`. That can surface as a pydantic error with no rerank context, or as a non-string value in a trace identity. `_is_number` also accepts `nan` and `inf`. Python's JSON parser accepts the `NaN` literal, so the stable sort in `_validated_ranking` gives an undefined order for a NaN score, and nothing refuses it. Both are cases the module's "results that do not match the documents sent" contract is meant to refuse by name.
**Fix:**
```python
model = body.get("model")
identity = model if isinstance(model, str) and model else self._model
...
def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
```
Add one test for each (non-string model, NaN score).

## Info

### IN-01: MCP transport security accepts any loopback page on any port, while REST uses an exact-origin list

**File:** `databasise/launcher/serve_mcp.py:224-225`
**Issue:** `allowed_origins` includes `http://localhost:*`, `http://127.0.0.1:*` and `http://[::1]:*`, and `test_mcp_transport_security_enables_dns_rebinding_protection_for_loopback` asserts `http://localhost:5173` passes. Any local web page, on any port, can therefore call the MCP HTTP transports. The REST launcher requires an exact `--cors-origin` for the same case. The asymmetry is easy to miss when reasoning about exposure.
**Fix:** Either add a `--cors-origin` equivalent to `databasise-mcp` and allow only those origins, or state the any-loopback-origin policy in the README and the `serve_mcp` docstring.

### IN-02: Stale-PID race and fd leak in `acquire_store_lock`

**File:** `databasise/store_lock.py:429-461`
**Issue:** A contender that loses `flock` reads the PID file immediately. If the new holder has taken the lock but not yet run `ftruncate`, the file still holds the previous process's PID. `_read_holder_pid` retries only on empty content, so the refusal can name a dead process. Separately, if `os.ftruncate` or `os.write` raises after the lock is taken (for example ENOSPC), `fd` is not closed, because the `except BaseException` block covers only the `flock` call.
**Fix:** Truncate and write the PID inside the same `try` as `flock`, with the same close-on-error handling. Optionally write the PID to a temp file and rename it, or include a start timestamp in the file.

### IN-03: Launcher refusals reuse parity wording, and the launcher imports the parity package for a default

**File:** `databasise/clients/builder.py:46-47`, `databasise/clients/builder.py:60-63`, `databasise/launcher/__init__.py:24`
**Issue:** `MissingParityEnvError` and `MissingParityEnvKeyError` tell an operator running `databasise-rest` to "see v1/README-PARITY.md ... or pass an explicit clients= mapping to run_arm()". Neither applies to a launcher user. Also, `databasise.launcher` imports `databasise.parity.import_index` (numpy, faiss and cozo loaded at startup, and the default store path computed from the source tree) only to read `DEFAULT_STORE_ROOT`. A non-editable install would point the default store into site-packages. The README mentions this, but the code does not refuse it.
**Fix:** Let the launcher pass its own hint text to the refusal classes (or catch and re-word them in `refuse`). Move `DEFAULT_STORE_ROOT` to a light module, or require `--store-root` when the default path does not exist.

### IN-04: New lint violations in phase-08 files

**File:** `databasise/launcher/serve_rest.py` (imports inside `build_app`), `databasise/parity/build_hipporag_index.py:76` (`store_lock` import sorted before `seam.tokens`), `databasise/tests/conftest.py:18` (`typing.Callable`), `databasise/tests/launcher/test_bind_guard.py:172` (RUF028: `# fmt: skip` inside an argument list)
**Issue:** `ruff check` reports I001, UP035 and RUF028 on lines this phase added, so the project's own ruff config is not clean on the new code. The `# fmt: skip` comment at `test_bind_guard.py:172` is also ineffective and cannot protect the intended formatting.
**Fix:** Run `ruff check --fix` on the listed files and move the `# fmt: skip` to the statement it should cover.

---

_Reviewed: 2026-10-16T19:15:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

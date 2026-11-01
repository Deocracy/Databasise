# Phase 8: Run the Engine - Pattern Map

**Mapped:** 2026-10-16
**Files analyzed:** 14 new/modified
**Analogs found:** 12 / 14 (all analog paths verified git-tracked, relative to `databasise/` unless noted)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `clients/builder.py` (new, moved from parity) | service/factory | transform | `parity/run_arm.py` lines 60-183 (the code being moved) | exact (move) |
| `clients/rerank.py` (new `HttpRerankClient`) | client | request-response | `clients/openai_compat.py` | role-match |
| `clients/openai_compat.py` (RUN-02/03 edits) | client | request-response | itself, lines 131, 149, 159-161 | exact |
| `parity/run_arm.py` (re-export) | utility | n/a | itself (Pattern 1 in RESEARCH) | exact |
| `store_lock.py` (new) | utility | file-I/O | no in-repo analog; error-class style from `MissingParityEnvKeyError` | none (use RESEARCH Store lock excerpt) |
| `launcher/__init__.py`, `serve_rest.py`, `serve_mcp.py` (new) | launcher/CLI | request-response | `parity/import_index.py:main` (lines 498-530) | role-match |
| `seam/rest.py` `create_app(cors_origins=())` | factory/middleware | request-response | itself, lines 235-247 | exact |
| `seam/engine.py` + `seam/corpus.py` `HealthReport.clients` | model | CRUD | `HealthReport` at `seam/corpus.py:194-206` | exact |
| `foreign/_mcp_sdk_guard.py` `mcp_sdk_is_installed` (RUN-04) | utility | transform | itself, `import_real_mcp` stripping | exact |
| `evidence/COVERAGE.md` (new copy) | doc | n/a | `.planning/milestones/v1.0-phases/05-opaque-side-admission/COVERAGE.md` (verbatim copy) | exact |
| `tests/mcp/test_tool_growth_invariant.py` (RUN-01) | test | n/a | itself, `_COVERAGE_PATH` lines 54-56 | exact |
| `tests/clients/test_build_clients.py`, `test_rerank_client.py` (new) | test | request-response | `tests/clients/test_openai_compat.py` | exact |
| `tests/launcher/*`, `tests/seam/test_rest_cors.py` (new) | test | request-response | `tests/seam/test_rest_corpus_endpoints.py` (RESEARCH cites its fixtures); stdio client recipe in RESEARCH | role-match |
| `pyproject.toml` (scripts, packages, pytest markers) | config | n/a | itself: `[tool.pytest.ini_options]` line 101, `[tool.setuptools]` line 108 | exact |

## Pattern Assignments

### `clients/builder.py` (factory, transform)
**Analog:** `parity/run_arm.py:60-183`. Move verbatim, then extend. Keep these names: `MissingParityEnvError`, `MissingParityEnvKeyError`, `UnparseableProviderRoutingError`, `_load_env_file`, `_REQUIRED_ENV_KEYS`, `_PROVIDER_ROUTING_ENV_KEY`, `_parse_provider_routing_body`, `_build_clients`. Public names `load_env_file`, `build_clients`, `REQUIRED_ENV_KEYS`. In `run_arm.py`, re-export under the old underscore names (`build_clients as _build_clients`) so the 7 importers and the monkeypatch seams keep working.

Named-error style (copy for any new error, lines 74-83):
```python
class MissingParityEnvKeyError(RuntimeError):
    def __init__(self, missing_keys: list[str]):
        self.missing_keys = missing_keys
        super().__init__(f"v1/.env.parity is missing required key(s): {', '.join(missing_keys)} — ...")
```
Core builder (lines 160-183):
```python
missing = [key for key in _REQUIRED_ENV_KEYS if key not in env]
if missing:
    raise MissingParityEnvKeyError(missing)
provider_routing_body = _parse_provider_routing_body(env)
llm = OpenAICompatibleClient(base_url=env["LLM_BINDING_HOST"], model=env["LLM_MODEL"],
    api_key=env["LLM_BINDING_API_KEY"], provider_routing_body=provider_routing_body)
embedding = OpenAICompatibleClient(base_url=env["EMBEDDING_BINDING_HOST"], ...)
return {"llm": llm, "embedding": embedding}
```
Extension (D-08): `RERANK_ENV_KEYS = ("RERANK_BINDING_HOST","RERANK_MODEL","RERANK_BINDING_API_KEY")`. Present set empty: no rerank. Partial: `MissingParityEnvKeyError(missing_rerank_keys)`. Complete: add `"rerank": HttpRerankClient(url=..., model=..., api_key=...)`. Do not change the six required keys (existing WR-01 tests assert them; see comment at lines 119-122).

The `MissingParityEnvError`/`KeyError` messages say `v1/.env.parity`; the launcher should reuse the classes but the planner may generalise the text (existing tests match on class, not text; grep before changing).

### `clients/openai_compat.py` RUN-02/03 edits
**Analog:** itself.
- RUN-02 site, `_token_accounting` lines 159-161: change `return TokenAccounting(counted_by=resolved_model_identity)` to `TokenAccounting(call_count=1, counted_by="unbudgetable")`.
- RUN-03 site, chat line 131 `text = response.choices[0].message.content`: guard empty `choices` and `content is None` with named errors.
- RUN-03 site, embed line 149 `vectors = [item.embedding for item in response.data]`: check `len(response.data) == len(texts)`, sort by `item.index`, require indices exactly `0..n-1`.
- New error classes follow `ModelIdentityMissingError` / `EmptyEmbeddingInputError` (lines 47-87): specifics as attributes, constructed message, docstring explaining why it refuses. Add to `__all__` (line 200).
- Test stub fix: `tests/clients/test_openai_compat.py:66-70` `data=[SimpleNamespace(embedding=[...])]` needs `index=i` per item.

### `clients/rerank.py` (client, request-response)
**Analog:** `clients/openai_compat.py` for class shape and `clients/base.py:46-75` for the protocol.
Protocol to satisfy (`base.py:71-75`):
```python
class RerankClient(Protocol):
    async def rerank(self, query: str, documents: list[str], **kwargs: Any) -> RerankResult: ...
# RerankResult(ranked_indices: list[int], tokens: TokenAccounting, resolved_model_identity: str)
```
Copy from `openai_compat.py`: keyword-only constructor with a test escape hatch (`client`/`transport=` for `httpx.MockTransport`); `_resolved_identity` raising `ModelIdentityMissingError` rather than substituting the requested model (lines 142-145); empty-input refusal modelled on `EmptyEmbeddingInputError`; guarded import idiom (lines 36-42) for `httpx`. Usage missing: `TokenAccounting(call_count=1, counted_by="unbudgetable")`. POST to `RERANK_BINDING_HOST` as the full URL (do not append `/rerank`). Open Question 1 (Cohere has no `model` field) is an owner decision; do not decide it in code.

### `store_lock.py` (utility, file-I/O) and `launcher/*` (CLI)
**store_lock analog:** none in repo; use the RESEARCH "Store lock" excerpt (`fcntl.flock` on `<store_root>/.engine.lock`, `StoreLockedError(RuntimeError)` with `store_root` and `holder_pid` attributes, retry-on-empty-PID read, context manager `store_lock(root)` for the parity CLIs).

**launcher analog:** `parity/import_index.py:main` (lines 498-530). Copy: `main(argv: list[str] | None = None) -> int`, named-exception catch that prints and returns 1, `if __name__ == "__main__":` footer, `DEFAULT_STORE_ROOT` import (line 85, a `Path`, avoids the import-boundary literal scan).
```python
def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        result = asyncio.run(_run())
    except MissingV1IndexError as exc:
        print(str(exc)); return 1
```
Launcher differences: use `argparse`; errors to stderr (stdout is the MCP stdio channel); order is args (refuse `--workers>1`) -> `acquire_store_lock` -> `build_clients` (skip on `--no-clients`) -> `create_app`/`create_server` -> `uvicorn.run(app, workers=1)` / `server.run(transport, host=, port=)`. Factory signatures: `create_app(*, store_root, workspace, registry=None, clients=None)` (`seam/rest.py:235`), `create_server(*, store_root, workspace, registry=None, clients=None)` (`mcp/server.py:177`). Keep launchers in `databasise/launcher/` (not under `mcp/`; AST tests scan `mcp/` and `rest.py`). Parity CLIs wrap only their `main()` bodies in `with store_lock(root):`, never the library functions.

### `seam/rest.py` `create_app` CORS
**Analog:** itself, signature lines 235-241. Add keyword-only `cors_origins: Sequence[str] = ()`; only when non-empty call `app.add_middleware(CORSMiddleware, allow_origins=list(origins), allow_methods=["GET","POST","DELETE"], allow_headers=["Content-Type"])`. Validate origins `^https?://[^/*]+$`. Do not touch route bodies (AST test `tests/seam/test_rest_transport.py`).

### `HealthReport.clients`
**Analog:** `seam/corpus.py:194-206` (`frozen=True, extra="forbid"`; fields `status`, `stores: dict[str,bool]`, `engine: dict[str,bool]`). Add `clients: dict[str, bool]`; fill in `Databasise.health()` at `seam/engine.py:916-963` from `self.clients`. Do not alter `status`. Check shape pins in `docs/system-model/` first (RESEARCH Open Question 2).

### `foreign/_mcp_sdk_guard.py` RUN-04
**Analog:** itself. Replace the body of `mcp_sdk_is_installed` (currently `importlib.util.find_spec("mcp")`, then origin check) with:
```python
stripped = [e for e in sys.path if not _resolves_inside_project(e)]
return importlib.machinery.PathFinder.find_spec("mcp", stripped) is not None
```
Add `import importlib.machinery`. `_resolves_inside_project` and `_VENV_ROOT` handling stay as is.

### Test and config edits
- RUN-01: `tests/mcp/test_tool_growth_invariant.py` lines 54-56 currently `_COVERAGE_PATH = _REPO_ROOT / ".planning" / "phases" / ...`; repoint to `Path(__file__).resolve().parents[2] / "evidence" / "COVERAGE.md"` plus a module-level `assert _COVERAGE_PATH.is_file(), f"... expected at {_COVERAGE_PATH}"`. Source file to copy: `.planning/milestones/v1.0-phases/05-opaque-side-admission/COVERAGE.md` (tracked, from repo root).
- RUN-12 / `pyproject.toml`: add to `[tool.pytest.ini_options]` (line 101, currently only `asyncio_mode`, `testpaths`): `markers = ["live: ..."]`, `addopts = '-m "not live"'`. Add `[project.scripts]` (`databasise-rest`, `databasise-mcp`), add `"databasise.launcher"` to the `[tool.setuptools]` packages list (line 108), move `httpx` from dev to runtime deps.
- Tests for new clients: copy the `_StubOpenAIClient` / `SimpleNamespace` response helper style from `tests/clients/test_openai_compat.py` (lines 20-70); for rerank use `httpx.MockTransport`.
- Test-name hazard: never create a test directory named `mcp`, `fastapi`, `uvicorn` (shadowing, see `_mcp_sdk_guard.py` docstring). Import the SDK in tests via `import_real_mcp("mcp")`.

## Shared Patterns

### Named refusals over silent fallbacks
**Source:** `parity/run_arm.py:60-83` and `clients/openai_compat.py:47-87`. Apply to: `StoreLockedError`, rerank error family, new embedding/chat errors, CORS origin validation. Specifics on attributes, constructed message, docstring stating why.

### Secrets never printed
**Source:** `parity/run_arm.py` `_load_env_file`. Apply to: launchers (`--env-file` has no default per Open Question 4), error messages name keys only, never values. Tests write stub env files into `tmp_path`.

### Stdout reserved for protocol in stdio MCP
Apply to: `launcher/serve_mcp.py`. All diagnostics to `sys.stderr`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `store_lock.py` | utility | file-I/O | No cross-process lock exists in repo; use RESEARCH verified `fcntl.flock` excerpt |
| `.mcp.json` / docs snippet | config | n/a | No existing MCP client config; RESEARCH stdio recipe, absolute path or `cwd` (Pitfall 8) |

## Metadata

**Analog search scope:** `databasise/clients`, `databasise/parity`, `databasise/foreign`, `databasise/seam`, `databasise/mcp`, `databasise/tests/clients`, `pyproject.toml`
**Files read:** CONTEXT.md, RESEARCH.md (lines 1-436 of 521), `openai_compat.py`, `run_arm.py` (55-185), `_mcp_sdk_guard.py`, `base.py` excerpts, `import_index.py` main, pyproject excerpts
**Not verified by reading:** `seam/engine.py` health body and `seam/corpus.py` HealthReport (line numbers taken from RESEARCH); tail of RESEARCH.md (validation sections) unread.
**Pattern extraction date:** 2026-10-16

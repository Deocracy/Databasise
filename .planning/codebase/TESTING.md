---
last_mapped_commit: 8044f9a
---
# Testing Patterns

**Analysis Date:** 2026-09-08

## Overview

This codebase contains two test suites with distinct maturity levels and scopes:

- **v1/** — Minimal, focused regression tests (5 files)
- **databasise/** — Comprehensive phase acceptance tests (30+ files organized by module)

Both use pytest with asyncio support and share the same core configuration patterns.

## Test Framework

### Runner

**Framework:** pytest 8.4.2+
- Config location: `[tool.pytest.ini_options]` in each `pyproject.toml`
- Both v1 and databasise use: `asyncio_mode = "auto"`
- v1 also sets: `asyncio_default_fixture_loop_scope = "function"` (per-function event loop isolation)
- Databasise inherits default scope (less restrictive)

**Run commands:**
```bash
# v1: Run offline tests only (default)
pytest tests/ -m offline

# v1: Run with coverage
pytest tests/ --cov=lightrag

# databasise: Run all tests
pytest tests/

# databasise: Run specific test module
pytest tests/stores/test_graph.py
```

### Async test support

**Library:** pytest-asyncio 1.2+
- Automatically detects and runs async test functions
- No explicit `@pytest.mark.asyncio` required when `asyncio_mode = "auto"`
- Event loops created per test (v1) or session-scoped as needed (databasise)

## Test File Organization

### Location & Naming

**v1:**
- Directory: `v1/tests/`
- Files: `test_*.py` (flat structure, 5 test files)
- Test path config: `testpaths = ["tests"]`
- Files: `test_create_prefixed_exception.py`, `test_strip_control_characters.py`, `test_sync_wrapper_guard.py`

**Databasise:**
- Directory: `databasise/tests/`
- Files: Mirror source structure (`tests/stores/`, `tests/identity/`, `tests/parts/`, etc.)
- Test path config: `testpaths = ["tests"]`
- 30+ test files organized by module:
  - `stores/` — storage backend tests (graph, vector, KV, blob, namespaces)
  - `identity/` — config hashing and instance identity
  - `parts/` — component registry and reference implementations
  - `validator/` — wiring validation (cycles, depth, blast radius, falsifiers)
  - `ledger/` — execution ledger and artifact tracking
  - Top-level acceptance tests (`test_phase_success_criteria.py`, `test_tracer_end_to_end.py`)

### File Structure Convention

**Module-level docstring:**
- v1: Detailed explanation of what the test guards against
- Databasise: Acceptance criteria and fixture roles

**Example from v1/tests/test_sync_wrapper_guard.py:**
```python
"""Regression tests for the synchronous-wrapper event-loop guard.

``LightRAG``'s synchronous wrappers (``insert``, ``query``,
``delete_by_entity`` …) all delegate to :func:`lightrag.lightrag._run_sync`,
which drives the matching ``a*`` coroutine via ``loop.run_until_complete()``.

That call is only valid when (a) no event loop is already running on the
current thread, and (b) the loop it drives is the same one the instance's
storages were initialized on (``LightRAG._owning_loop``). Two misuse modes
break this...
"""
```

**Example from databasise/tests/test_phase_success_criteria.py:**
```python
"""The phase's acceptance module: all four ROADMAP.md Phase 1 success criteria, asserted end to
end through ``databasise.run_wiring`` — the public entry point a consumer calls — rather than
through an internal helper, so a refactor that breaks the public path fails here even if every
unit test still passes.

Two fixture wirings (built by the two ``_*_wiring`` helpers below):
- The **transparent wiring**: ...
- The **arms wiring**: ...
"""
```

## Test Structure

### Suite Organization

**v1 pattern: Single-concern functions**
```python
@pytest.mark.offline
def test_run_sync_runs_coroutine_when_no_loop_running():
    """With no running loop, the coroutine runs to completion and returns."""
    def factory():
        async def _coro():
            return 42
        return _coro()

    result = _run_sync(factory, sync_name="insert", async_name="ainsert")
    assert result == 42
```

**Databasise pattern: End-to-end wiring tests with complex setup**
```python
async def _multi_engine_touch_body(ctx: NodeContext) -> dict[str, Any]:
    """The join node: writes to the run's own kv store..."""
    kv = ctx.stores["kv"]
    await kv.upsert({ctx.node_id: {"inputs": dict(ctx.inputs)}})
    
    # Complex multi-store orchestration
    store_root = Path(ctx.config["store_root"])
    graph = CozoGraphStore(namespace="criterion1-graph", ...)
    await graph.upsert_node("n1", {"touched": True})
    
    return {"joined": sorted(ctx.inputs)}

# Fixture wiring built as a Part (databasise's component model)
_MULTI_ENGINE_TOUCH_PART = Part(
    name="...",
    fn=_multi_engine_touch_body,
    ...
)
```

### Fixture Scope & Patterns

**v1 fixtures (v1/tests/conftest.py):**

- `_hermetic_mineru_env` (autouse): Strips parser routing env vars per test
  - Prevents .env file leaks affecting test isolation
  - Uses `monkeypatch.delenv()` to clear vars safely
  - Allows tests to `monkeypatch.setenv()` individually

**Databasise fixtures (databasise/tests/conftest.py):**

- `store_root` (function-scoped): Temp directory for all storage writes
  - Every test gets a fresh `tmp_path / "store_root"`
  - Allows inspection of storage layout after test runs

- `rig_trace_schema` (session-scoped): Parsed RIG run-record schema
  - Loaded once per test session from `docs/system-model/rig-trace.schema.json`
  - Reused across all tests

- `assert_valid_trace` (function-scoped): Callable validator
  - Validates run-record dict against rig-trace schema
  - Returns JSON-Schema error paths on failure
  - Used in conformance tests to verify emitted traces

## Test Markers

**v1 test markers (via `pytest_configure` in conftest.py):**
- `@pytest.mark.offline` — No external dependencies (default)
- `@pytest.mark.integration` — Requires external services
- `@pytest.mark.requires_db` — Database dependency
- `@pytest.mark.requires_api` — LightRAG API server dependency

**Run offline tests only:**
```bash
pytest tests/ -m offline
```

**Databasise** does not define custom markers; all tests run by default (no filtering by external service).

## Mocking & Test Doubles

**v1:**
- Minimal mocking (no external dependencies in base suite)
- Focuses on guard testing and utility functions
- When async is required: Uses `asyncio.run()` and `asyncio.new_event_loop()`
- ThreadPoolExecutor used in cross-thread tests to simulate real concurrency

**Example from v1/tests/test_sync_wrapper_guard.py:**
```python
def test_run_sync_raises_when_driven_from_a_different_loop():
    """Driving a sync wrapper from a thread with no event loop of its own..."""
    owning_loop = asyncio.new_event_loop()
    calls: list[bool] = []

    def factory():  # pragma: no cover - must never be reached
        calls.append(True)
        raise AssertionError("coro_factory must not run on the wrong loop")

    def call_off_thread():
        return _run_sync(
            factory,
            sync_name="insert",
            async_name="ainsert",
            owning_loop=owning_loop,
        )

    with ThreadPoolExecutor(max_workers=1) as executor:
        with pytest.raises(RuntimeError) as exc_info:
            executor.submit(call_off_thread).result()
```

**Databasise:**
- Uses reference implementations (fake LLM, fake retriever) from `databasise.parts_core`
- Complex fixture wirings built using the Part model itself
- Stores (graph, vector, KV) are real embedded backends, not mocked
- Validates actual serialization and schema conformance

**Example from databasise/tests/test_phase_success_criteria.py:**
```python
from databasise.parts_core.fake_llm_caller import FAKE_LLM_CALLER_PART
from databasise.parts_core.fake_retriever import FAKE_RETRIEVER_PART

# Wiring uses reference parts, not mocks
_TRANSPARENT_WIRING = {
    "producer": FAKE_RETRIEVER_PART,
    "retrieve_a": FAKE_RETRIEVER_PART,
    "retrieve_b": FAKE_RETRIEVER_PART,
    "join": _MULTI_ENGINE_TOUCH_PART,
}
```

## Fixtures and Factories

**v1:**
- Option flags: `keep_test_artifacts`, `stress_test_mode`, `parallel_workers` (via pytest options)
- Fixtures accessed via `request.config.getoption()` with fallback to env vars
- Autouse hermetic env fixture

**Databasise:**
- Store roots managed per test (auto-cleanup via tmp_path)
- Schema validation helper (assert_valid_trace)
- No global state; each test's stores are isolated to its own store_root
- Fixtures mirror the public API: `store_root`, `assert_valid_trace`, `rig_trace_schema`

**Example pytest options in v1/tests/conftest.py:**
```python
@pytest.fixture(autouse=True)
def _hermetic_mineru_env(monkeypatch):
    """Strip env vars that leak from .env into tests..."""
    monkeypatch.delenv("MINERU_API_MODE", raising=False)
    monkeypatch.delenv("MINERU_LOCAL_ENDPOINT", raising=False)
    # ... more vars stripped

def pytest_addoption(parser):
    """Add command-line options for stress test configuration."""
    parser.addoption(
        "--keep-artifacts",
        action="store_true",
        default=False,
        help="Keep test artifacts for inspection",
    )
    parser.addoption(
        "--stress-test",
        action="store_true",
        default=False,
        help="Enable stress test mode",
    )
    parser.addoption(
        "--test-workers",
        action="store",
        default=3,
        type=int,
        help="Number of parallel workers",
    )
```

## Coverage

**v1:**
- No explicit coverage requirements configured
- Pragma comments: `# pragma: no cover` marks guard failure paths (never reached on success)

**Databasise:**
- No explicit coverage requirements configured
- Comprehensive acceptance tests ensure public API paths are exercised

## Test Types

### Unit Tests

**v1:**
- Sync wrapper guards (`test_sync_wrapper_guard.py`)
- Utility functions (`test_strip_control_characters.py`, `test_create_prefixed_exception.py`)
- Scope: Single function or component
- No external services

**Databasise:**
- Storage backend tests (`tests/stores/test_*.py`)
- Identity and config hashing (`tests/identity/`)
- Validator logic (`tests/validator/`)
- Part registry and schemas (`tests/parts/`)

**Example v1 unit test:**
```python
@pytest.mark.offline
def test_run_sync_does_not_create_coroutine_when_it_raises():
    """The factory is invoked lazily, so a guard failure never leaves an
    un-awaited coroutine behind (which would emit a RuntimeWarning)."""
    calls: list[bool] = []

    def factory():
        calls.append(True)
        async def _coro():
            return None
        return _coro()

    async def _inside_loop():
        return _run_sync(factory, sync_name="query", async_name="aquery")

    with pytest.raises(RuntimeError):
        asyncio.run(_inside_loop())

    assert calls == [], "coro_factory should not run when the guard rejects"
```

### Integration Tests

**v1:**
- Marked with `@pytest.mark.integration` (skipped by default)
- Not present in current test suite (focused on guards)

**Databasise:**
- End-to-end wiring tests (`test_phase_success_criteria.py`)
- Traced execution (`test_tracer_end_to_end.py`)
- Trusted source invariants (`test_trusted_source_invariant.py`)
- All tests run against real embedded stores (Cozo, Faiss, file-based KV)

**Example databasise integration test:**
```python
async def test_all_four_success_criteria():
    """Assert all four ROADMAP.md Phase 1 criteria through the public entry point."""
    # 1. Transparent multi-engine wiring (fan-out + join)
    transparent_wiring = _transparent_wiring()
    run_transparent = await databasise.run_wiring(
        wiring=transparent_wiring,
        config={...},
    )
    assert run_transparent.success
    assert run_transparent.trace["effects"][...] # validate effects
    
    # 2. Arms wiring with artifact scope
    arms_wiring = _arms_wiring()
    run_arms = await databasise.run_wiring(wiring=arms_wiring, config={...})
    assert run_arms.success
```

### E2E Tests

**v1:** Not present in codebase

**Databasise:** See integration tests above (e2e wiring conformance is the primary test type)

## Async Testing Patterns

**Pattern: Async test function**
```python
async def test_store_upserts_and_queries():
    """Async test runs on the auto-created event loop."""
    store = FaissVectorStore(namespace="test", workspace="", store_root=store_root)
    await store.upsert(["v1"], [[1.0, 0.0, 0.0]])
    results = await store.query([[1.0, 0.0, 0.0]], top_k=1)
    assert results == ["v1"]
```

**Pattern: Wrapping sync code with async**
```python
@pytest.mark.asyncio
def test_sync_function_from_async_context():
    """Manually mark if asyncio_mode != 'auto'."""
    async def _run():
        result = _run_sync(factory, ...)
        return result
    
    result = asyncio.run(_run())
    assert result == 42
```

## Error Testing

**v1 pattern: Guard failure assertions**
```python
def test_run_sync_raises_clear_error_inside_running_loop():
    """Inside a running loop the guard raises RuntimeError with actionable message."""
    def factory():  # pragma: no cover
        raise AssertionError("must not be called")

    async def _inside_loop():
        return _run_sync(factory, sync_name="insert", async_name="ainsert")

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(_inside_loop())

    message = str(exc_info.value)
    assert "insert()" in message
    assert "await ainsert(" in message
    assert "deadlock" not in message.lower()
```

**Databasise pattern: Schema validation**
```python
def test_invalid_trace_fails_validation(assert_valid_trace):
    """Traces not matching rig-trace.schema.json raise with full error path."""
    invalid_record = {"trace": "malformed"}  # Missing required fields
    
    with pytest.raises(AssertionError) as exc_info:
        assert_valid_trace(invalid_record)
    
    assert "failed rig-trace.schema.json validation" in str(exc_info.value)
```

## Common Test Utilities

**v1:**
- `_hermetic_mineru_env` — Test isolation via env var stripping
- `pytest_configure()` — Marker registration
- `pytest_addoption()` — CLI option setup

**Databasise:**
- `store_root` — Isolated storage directory
- `rig_trace_schema` — Cached schema for validation
- `assert_valid_trace()` — JSON-Schema validator callable
- Repository root detection (`_repository_root()`) — Walk up from test file

## Running Tests

**v1:**
```bash
# Run all offline tests
pytest tests/ -m offline

# Run with coverage report
pytest tests/ --cov=lightrag --cov-report=html

# Run specific test function
pytest tests/test_sync_wrapper_guard.py::test_run_sync_runs_coroutine_when_no_loop_running

# Run with verbosity
pytest tests/ -vv

# Keep test artifacts for inspection
pytest tests/ --keep-artifacts

# Stress test mode
pytest tests/ --stress-test --test-workers=8
```

**Databasise:**
```bash
# Run all tests
pytest tests/

# Run specific module
pytest tests/stores/

# Run specific test file
pytest tests/stores/test_graph.py

# Run with verbosity
pytest tests/ -vv

# Run with coverage
pytest tests/ --cov=databasise --cov-report=html
```

## Test Configuration Summary

| Aspect | v1 | Databasise |
|--------|--|----|
| Framework | pytest 8.4.2+ | pytest 8.4.2+ |
| Async support | pytest-asyncio 1.2+ | pytest-asyncio 1.2+ |
| Async mode | `auto` | `auto` |
| Loop scope | `function` | default |
| Test directory | `v1/tests/` | `databasise/tests/` |
| Organization | Flat (5 files) | Modular (30+ files, mirrored structure) |
| Markers | offline, integration, requires_db, requires_api | None (all run by default) |
| Fixtures | Env var hermeting, CLI options | Store root, schema validation |
| Coverage | No requirements | No requirements |

---

*Testing analysis: 2026-09-08*

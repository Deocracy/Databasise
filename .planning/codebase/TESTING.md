<!-- refreshed: 2026-09-03 -->
# Testing Patterns

**Analysis Date:** 2026-09-03

## Test Framework

**Runner:**
- Python: pytest 8.4.2+
- Config: `[tool.pytest.ini_options]` in pyproject.toml (both v1 and databasise)
- Async support: pytest-asyncio 1.2.0+
- Mode: `asyncio_mode = "auto"` (fixtures and tests auto-run in event loop)

**Assertion Library:**
- Built-in pytest assertions: `assert result == expected`
- Schema validation: `jsonschema.Draft7Validator` for run-record validation (databasise)

**Run Commands:**
```bash
pytest tests/                           # Run all tests
pytest --run-integration tests/         # Run integration tests (skipped by default)
pytest --keep-artifacts tests/          # Keep temp files for inspection
pytest --stress-test --test-workers 5   # Run stress tests with 5 workers
pytest databasise/tests/                # Run databasise tests
```

## Test File Organization

**Location (v1):**
- Root-level tests directory: `v1/tests/`
- Mirrors source structure: `tests/pipeline/`, `tests/kg/`, `tests/api/`, etc.

**Location (databasise):**
- Co-located with source: `databasise/tests/`
- Organized by feature: `stores/`, `identity/`, `parts/`, `validator/`, `registry_artifact/`, `ledger/`

**Naming:**
- Test files: `test_*.py` (e.g., `test_sync_wrapper_guard.py`)
- Test classes: `Test*` (pattern specified in pyproject.toml)
- Test functions: `test_*` (pattern specified in pyproject.toml)

**Structure (v1):**
```
tests/
├── conftest.py                         # Global fixtures (45+ lines)
├── test_sync_wrapper_guard.py          # Sync/async wrapper guards (197 lines)
├── test_create_prefixed_exception.py   # Exception creation tests
├── test_strip_control_characters.py    # Utility tests
├── pipeline/                           # Feature-organized subsystem tests
│   └── test_*.py
├── kg/                                 # Knowledge graph subsystem tests
│   └── test_*.py
└── api/                                # API subsystem tests
    └── routes/test_*.py
```

**Structure (databasise):**
```
databasise/tests/
├── conftest.py                         # Global fixtures (schema, store_root, validators)
├── test_conftest_fixtures.py           # Smoke tests for fixtures
├── test_tracer_end_to_end.py           # End-to-end wiring execution
├── test_embed_startup.py               # Initialization tests
├── test_import_boundary.py             # Import boundary tests
├── test_phase_success_criteria.py      # Gate criteria validation
└── stores/                             # Storage adapter tests
    ├── test_blob.py
    ├── test_kv.py
    ├── test_vector.py
    ├── test_graph.py
    └── test_*.py
```

## Test Structure

**Test Layout (v1):**
```python
@pytest.mark.offline
def test_run_sync_runs_coroutine_when_no_loop_running():
    """With no running loop, the coroutine runs to completion and returns."""
    # Arrange
    def factory():
        async def _coro():
            return 42
        return _coro()

    # Act
    result = _run_sync(factory, sync_name="insert", async_name="ainsert")

    # Assert
    assert result == 42
```

**Patterns (v1):**
1. **Docstring-as-specification** — Every test documents expected behavior in past tense
2. **Arrange-Act-Assert (AAA)** — Clear setup, execution, validation phases (often implicit)
3. **Descriptive names** — `test_run_sync_runs_coroutine_when_no_loop_running()` tells scenario + expectation
4. **Pytest markers** — `@pytest.mark.offline`, `@pytest.mark.integration` for selective runs
5. **Guard-first assertions** — Factory calls tracked; asserts guard prevents unwanted execution

**Test Layout (databasise):**
```python
async def test_tracer_runs_end_to_end_and_produces_a_schema_valid_run_record(
    store_root, assert_valid_trace
):
    """End-to-end run produces a schema-valid run record."""
    import databasise

    wiring_doc = _load_fixture()
    record = await databasise.run_wiring(
        wiring_doc,
        store_root=store_root,
        determinism_setting="cache-bypassed",
    )

    assert_valid_trace(record)
    assert record["partial"] is False
```

**Patterns (databasise):**
1. **Native async tests** — `async def test_*()` with `await` calls
2. **Schema-driven validation** — Fixtures return validator callables
3. **Fixture-injected parameters** — `store_root`, `assert_valid_trace` provide setup

## Mocking

**Framework:**
- Built-in: `pytest.fixture` with `monkeypatch` for environment isolation
- JSON Schema: `jsonschema.Draft7Validator` (no traditional mocks)
- No external mocking library in core tests

**Patterns (v1):**
```python
@pytest.fixture(autouse=True)
def _hermetic_mineru_env(monkeypatch):
    """Make every test start with parser-routing env vars in their unset state."""
    monkeypatch.delenv("MINERU_API_MODE", raising=False)
    monkeypatch.delenv("MINERU_API_TOKEN", raising=False)
    monkeypatch.delenv("LIGHTRAG_PARSER", raising=False)
    # ... strips 7+ more parser-related env vars
```

**What to Mock:**
- External service endpoints: `MINERU_API_TOKEN`, `MINERU_LOCAL_ENDPOINT`, `DOCLING_ENDPOINT`
- Environment-dependent modes: `MINERU_API_MODE`, parser options
- Reason: Hermetic tests; developer `.env` leakage breaks test isolation

**What NOT to Mock:**
- Built-in functions (use real asyncio loops)
- Library implementations (test real behavior, not stubs)
- Reason: Mock creep hides real bugs

## Fixtures and Factories

**Test Data Factories (v1):**
```python
def factory():
    async def _coro():
        return 42
    return _coro()

result = _run_sync(factory, sync_name="insert", async_name="ainsert")
```

**Session-scope Fixtures (v1):**
```python
@pytest.fixture(scope="session")
def keep_test_artifacts(request):
    """Determine whether to keep test artifacts."""
    if request.config.getoption("--keep-artifacts"):
        return True
    return os.getenv("LIGHTRAG_KEEP_ARTIFACTS", "false").lower() == "true"

@pytest.fixture(scope="session")
def parallel_workers(request):
    """Number of parallel workers for stress tests."""
    cli_workers = request.config.getoption("--test-workers")
    if cli_workers != 3:  # Non-default
        return cli_workers
    return int(os.getenv("LIGHTRAG_TEST_WORKERS", "3"))
```

**Pattern:** CLI option > Environment variable > Default value

**Fixtures (databasise):**
```python
@pytest.fixture
def store_root(tmp_path: Path) -> Path:
    """Per-test directory for storage adapters."""
    root = tmp_path / "store_root"
    root.mkdir()
    return root

@pytest.fixture(scope="session")
def rig_trace_schema() -> dict[str, Any]:
    """Load RIG run-record schema."""
    schema_path = _repository_root() / "docs" / "system-model" / "rig-trace.schema.json"
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def assert_valid_trace(rig_trace_schema: dict[str, Any]) -> Callable:
    """Return callable that validates run-record against schema."""
    def _assert_valid_trace(record: dict[str, Any]) -> None:
        validator = Draft7Validator(rig_trace_schema)
        errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
        if errors:
            messages = "\n".join(
                f"  - {'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
                for e in errors
            )
            raise AssertionError(f"Schema validation failed:\n{messages}")
    return _assert_valid_trace
```

**Location:**
- Global: `tests/conftest.py` (v1), `databasise/tests/conftest.py` (databasise)
- Subsystem: Implied in subsystem-specific conftest files

## Coverage

**Requirements:**
- Not explicitly enforced in pyproject.toml (no pytest-cov config)
- Best practice: >80% coverage for modified code (assumed convention)

**View Coverage:**
```bash
pytest --cov=lightrag --cov-report=term-missing tests/
pytest --cov=lightrag --cov-report=html tests/
# Open htmlcov/index.html in browser
```

## Test Types

**Unit Tests:**
- Scope: Single function/method behavior in isolation
- Pattern: One scenario per test function
- Example: `test_run_sync_runs_coroutine_when_no_loop_running()` tests success path only
- Guard conditions tested separately

**Integration Tests:**
- Scope: Multiple components/systems interacting
- Markers: `@pytest.mark.integration`, `@pytest.mark.requires_db`, `@pytest.mark.requires_api`
- Skipped by default; run with `pytest --run-integration`
- Requires: External services (DB, API server, parser endpoints)

**E2E Tests:**
- Example (databasise): `test_tracer_runs_end_to_end_and_produces_a_schema_valid_run_record()`
- Exercises full `run_wiring()` path with schema validation

**Offline Tests:**
- Marker: `@pytest.mark.offline`
- Scope: No external dependencies
- Default: Run offline, skip integration tests

## Common Patterns

**Async Testing (v1):**
```python
@pytest.mark.offline
def test_run_sync_raises_clear_error_inside_running_loop():
    """Inside a running loop the guard raises a RuntimeError."""
    def factory():  # pragma: no cover - must never be reached
        raise AssertionError("coro_factory must not be called inside a loop")

    async def _inside_loop():
        return _run_sync(factory, sync_name="insert", async_name="ainsert")

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(_inside_loop())

    message = str(exc_info.value)
    assert "insert()" in message
    assert "await ainsert(" in message
```

**Pattern:**
- Wrap async code in `async def` function
- Call with `asyncio.run()` from sync test
- Use `pytest.raises()` to validate exception type and message

**Async Testing (databasise):**
```python
async def test_upsert_and_query_returns_nearest_neighbours(store_root):
    store = FaissVectorStore(namespace="vec", workspace="ws", store_root=store_root)
    await store.upsert(
        ids=["a", "b"],
        embeddings=[_vec(1.0, 0.0), _vec(0.0, 1.0)],
    )
    await store.index_done_callback()

    results = await store.query(_vec(1.0, 0.0), top_k=2)

    assert [r["id"] for r in results] == ["a", "b"]
```

**Pattern:**
- Native `async def test_*()` (pytest-asyncio auto-runs in event loop)
- Fixtures injected and work with async tests
- Call async functions with `await` directly

**Error Testing:**
```python
with pytest.raises(RuntimeError) as exc_info:
    executor.submit(call_off_thread).result()

message = str(exc_info.value)
assert "insert()" in message
assert "await ainsert(" in message
assert "deadlock" not in message.lower()  # Regression guard
assert calls == [], "factory should not run"
```

**Pattern:**
- Check exception type with `pytest.raises()`
- Validate error message substrings
- Verify side effects (factory was not called)
- Document regression fix

**pytest Configuration:**
```python
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "offline: marks tests as offline (no external dependencies)")
    config.addinivalue_line("markers", "integration: marks tests requiring external services (skipped by default)")
    config.addinivalue_line("markers", "requires_db: marks tests requiring database")
    config.addinivalue_line("markers", "requires_api: marks tests requiring LightRAG API server")

def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption("--keep-artifacts", action="store_true", default=False,
        help="Keep test artifacts (temporary directories and files) after test completion for inspection")
    parser.addoption("--stress-test", action="store_true", default=False,
        help="Enable stress test mode with more intensive workloads")
    parser.addoption("--test-workers", action="store", default=3, type=int,
        help="Number of parallel workers for stress tests (default: 3)")
    parser.addoption("--run-integration", action="store_true", default=False,
        help="Run integration tests that require external services (database, API server, etc.)")

def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip integration tests by default."""
    if config.getoption("--run-integration"):
        return
    skip_integration = pytest.mark.skip(
        reason="Requires external services(DB/API), use --run-integration to run"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
```

**Pattern:**
- Register custom markers in `pytest_configure()`
- Add CLI options in `pytest_addoption()`
- Implement test filtering in `pytest_collection_modifyitems()`
- Allows dynamic skip/run based on flags

---

*Testing analysis: 2026-09-03*

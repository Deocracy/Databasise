---
last_mapped_commit: 9160a53de8976defcfb11b138253156fd5050ecd
last_mapped_at: 2026-08-31
---
# Testing Patterns

**Analysis Date:** 2026-08-31

## Test Framework

**Runner:**

- pytest 8.4.2+
- Config file: `v1/pyproject.toml` section `[tool.pytest.ini_options]`
- Async support: pytest-asyncio 1.2.0+

**Assertion Library:**

- Built-in pytest assertions (no external library needed)
- Pattern: `assert result == expected`
- Schema validation: `jsonschema.Draft7Validator` for validating run records against `rig-trace.schema.json`

**Run Commands:**

```bash

# Run all tests

pytest tests/

# Watch mode (requires pytest-watch; not in config)

pytest-watch tests/

# Coverage report (pytest-cov plugin; not in pyproject.toml but standard pattern)

pytest --cov=lightrag tests/

# Run only offline tests (skip integration tests by default)

pytest tests/

# Run integration tests

pytest --run-integration tests/

# Run stress tests with custom worker count

pytest --stress-test --test-workers 5 tests/

# Keep test artifacts for inspection

pytest --keep-artifacts tests/

# Run specific test file

pytest tests/test_sync_wrapper_guard.py

# Run specific test function

pytest tests/test_sync_wrapper_guard.py::test_run_sync_runs_coroutine_when_no_loop_running

# Run databasise tests

pytest databasise/tests/

# Run databasise end-to-end tests with fixture

pytest databasise/tests/test_tracer_end_to_end.py
```

## Test File Organization

**Location:**

- Pattern: Separate `tests/` directory at repo root (v1)
- Pattern: Separate `databasise/tests/` directory co-located with source code (databasise/)
- Structure mirrors source layout: `tests/pipeline/`, `tests/kg/`, `tests/api/routes/`, etc. (v1)
- Structure in databasise: `databasise/tests/`, `databasise/tests/stores/` (feature-organized)
- Co-location not used in v1; tests live in dedicated directory tree
- Co-location used in databasise (tests are inside the package, closer to source)

**Naming:**

- Test files: `test_*.py` (e.g., `test_sync_wrapper_guard.py`, `test_strip_control_characters.py`, `test_tracer_end_to_end.py`)
- Test classes: `Test*` (e.g., `TestClass`)
- Test functions: `test_*` (e.g., `test_run_sync_runs_coroutine_when_no_loop_running()`)

**Structure (v1):**

```
tests/
├── conftest.py                                 # Global pytest config and fixtures
├── test_create_prefixed_exception.py           # Unit tests (root level)
├── test_strip_control_characters.py            # Unit tests
├── test_sync_wrapper_guard.py                  # Unit tests for sync/async wrapper guards
├── pipeline/                                   # Feature-specific test packages
│   ├── test_content_hash_normalization.py
│   ├── test_document_file_path_normalization.py
│   ├── test_pipeline_analyze_multimodal.py
│   └── ...
├── kg/                                         # Knowledge graph subsystem tests
│   ├── test_degree_return_type.py
│   └── ...
└── api/                                        # API subsystem tests
    └── routes/
        └── test_graph_routes_pipeline_busy.py
```

**Structure (databasise):**

```
databasise/tests/
├── conftest.py                                 # Global pytest config and fixtures
├── fixtures/
│   └── wiring-tracer.json                      # JSON test fixtures for wiring inputs
├── test_conftest_fixtures.py                   # Tests for conftest fixtures themselves
├── test_tracer_end_to_end.py                   # End-to-end wiring execution tests
├── test_embed_startup.py                       # Startup and initialization tests
├── test_import_boundary.py                     # Import boundary enforcement tests
├── test_phase_success_criteria.py              # Phase gate criteria validation tests
└── stores/
    ├── __init__.py
    └── test_blob.py                            # Storage adapter tests
```

## Test Structure

**Suite Organization:**

```python

# From test_sync_wrapper_guard.py — basic function-level tests

@pytest.mark.offline
def test_run_sync_runs_coroutine_when_no_loop_running():
    """Test name is a complete sentence describing expected behavior."""
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

**Patterns:**

1. **Docstring-as-specification:** Every test has a docstring explaining what it validates
   - Example: `"With no running loop, the coroutine runs to completion and returns."`
   - Phrased as assertion of expected behavior, not test name repetition

2. **Arrange-Act-Assert (AAA):** Tests follow clear phases (often implicit via comments)
   - Setup phase creates fixtures/factories
   - Action phase executes the code under test
   - Assertion phase validates results

3. **Descriptive function names:** Names are predicates of expected behavior
   - `test_run_sync_runs_coroutine_when_no_loop_running()` — tells you the scenario and expectation
   - `test_run_sync_raises_clear_error_inside_running_loop()` — names both the action and expected error behavior
   - Not: `test_run_sync()` (too generic)

4. **Marker-based categorization:** Tests tagged with pytest markers for selective runs
   - Example: `@pytest.mark.offline` — test has no external dependencies
   - Example: `@pytest.mark.integration` — requires external services (skipped by default)
   - Custom markers: `requires_db`, `requires_api`

5. **Guard-first assertions:** Guard conditions checked before creating objects
   - Example from `test_run_sync_does_not_create_coroutine_when_it_raises()`:
     - Factory tracks if it was called (via list append)
     - Guard validates factory was NOT called on error path
     - Prevents un-awaited coroutine warnings

**Patterns (databasise):**

```python

# From databasise/tests/test_tracer_end_to_end.py — async test with fixture-driven inputs

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
        concurrency_setting="sequential",
    )

    assert_valid_trace(record)
    assert record["partial"] is False
    assert record["degraded"] is False
```

6. **Schema validation in fixtures:** Fixtures return callable validators that check output against JSON Schema
   - Example: `assert_valid_trace` validates run records against `rig-trace.schema.json`
   - Fixture provides diagnostic error output naming each failed validation path

## Mocking

**Framework:**

- Built-in: `pytest.fixture` with `monkeypatch` for environment manipulation
- No external mocking library (e.g., unittest.mock) in core tests
- Pattern: Monkeypatch used for environment variable isolation
- JSON Schema validation: `jsonschema.Draft7Validator` for schema-driven assertions (no mocking)

**Patterns:**

```python

# From conftest.py — fixture-based environment isolation

@pytest.fixture(autouse=True)
def _hermetic_mineru_env(monkeypatch):
    """Make every test start with parser-routing env vars in their unset state."""
    monkeypatch.delenv("MINERU_API_MODE", raising=False)
    monkeypatch.delenv("MINERU_API_TOKEN", raising=False)
    monkeypatch.delenv("LIGHTRAG_PARSER", raising=False)
    # ... strip 7 more parser-related env vars
```

**What to Mock:**

- External service endpoints: `MINERU_API_TOKEN`, `MINERU_LOCAL_ENDPOINT`, `DOCLING_ENDPOINT`
- Environment-dependent parser modes: `MINERU_API_MODE`, `LIGHTRAG_PARSER`, parser options
- Reason: Tests must be hermetic; developer `.env` leakage breaks test isolation

**What NOT to Mock:**

- Built-in functions (use real asyncio loops for async tests)
- Library implementations (test real behavior, not mocked stubs)
- Reason: Mock creep hides real bugs; test fixtures set up real state instead

## Fixtures and Factories

**Test Data:**

```python

# From test_sync_wrapper_guard.py — factory pattern for test data

def factory():
    async def _coro():
        return 42
    return _coro()

result = _run_sync(factory, sync_name="insert", async_name="ainsert")
```

**Session-scope fixtures:**

```python

# From conftest.py — configuration flags passed as session-scope fixtures

@pytest.fixture(scope="session")
def keep_test_artifacts(request):
    """Determine whether to keep test artifacts."""
    if request.config.getoption("--keep-artifacts"):
        return True
    return os.getenv("LIGHTRAG_KEEP_ARTIFACTS", "false").lower() == "true"

@pytest.fixture(scope="session")
def parallel_workers(request):
    """Determine number of parallel workers for stress tests."""
    cli_workers = request.config.getoption("--test-workers")
    if cli_workers != 3:  # Non-default value provided
        return cli_workers
    return int(os.getenv("LIGHTRAG_TEST_WORKERS", "3"))
```

**Pattern: CLI option fallback to environment**

- Priority: CLI option > Environment variable > Default value
- Allows test configuration via command line or CI environment

**Fixtures (databasise):**

```python

# From databasise/tests/conftest.py — schema and storage fixtures

@pytest.fixture
def store_root(tmp_path: Path) -> Path:
    """A tmp_path-derived directory every store adapter writes under during a test."""
    root = tmp_path / "store_root"
    root.mkdir()
    return root

@pytest.fixture(scope="session")
def rig_trace_schema() -> dict[str, Any]:
    """Load and return the parsed RIG run-record (trace) schema."""
    schema_path = _repository_root() / "docs" / "system-model" / "rig-trace.schema.json"
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def assert_valid_trace(
    rig_trace_schema: dict[str, Any],
) -> Callable[[dict[str, Any]], None]:
    """Return a callable that validates a run-record dict against rig_trace_schema."""
    def _assert_valid_trace(record: dict[str, Any]) -> None:
        validator = Draft7Validator(rig_trace_schema)
        errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
        if errors:
            messages = "\n".join(
                f"  - {'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
                for e in errors
            )
            raise AssertionError(
                f"run-record failed rig-trace.schema.json validation:\n{messages}"
            )
    return _assert_valid_trace
```

**Location:**

- Global fixtures: `tests/conftest.py` (v1), `databasise/tests/conftest.py` (databasise)
- Subsystem fixtures: Implied to be in subsystem-specific conftest files (e.g., `tests/pipeline/conftest.py`)
- Factories: Defined inline within test file or via fixture

## Coverage

**Requirements:**

- Not explicitly enforced in `pyproject.toml` (no pytest-cov config)
- Best practice: Maintain >80% coverage for modified code (assumed convention, not enforced)

**View Coverage:**

```bash

# Generate and display coverage report

pytest --cov=lightrag --cov-report=html tests/

# Open htmlcov/index.html in browser

# Terminal-based report

pytest --cov=lightrag --cov-report=term-missing tests/
```

## Test Types

**Unit Tests:**

- Scope: Single function or method behavior in isolation
- Approach: Test one scenario per test function
- Example: `test_run_sync_runs_coroutine_when_no_loop_running()` tests only the success path
- Pattern: Guard conditions tested separately (not bundled into single test)

**Integration Tests:**

- Scope: Multiple components or systems interacting
- Marked with: `@pytest.mark.integration`
- Marked with: `@pytest.mark.requires_db`, `@pytest.mark.requires_api`
- Skipped by default; run with `pytest --run-integration`
- Reason: Require external services (database, API server, parser endpoints)
- Example: `test_kv_node_write_is_readable_back_from_the_sqlite_store()` tests wiring → storage → retrieval

**E2E Tests:**

- Not detected in v1 codebase
- Inferred from config: API integration tests may serve this role
- Example in databasise: `test_tracer_runs_end_to_end_and_produces_a_schema_valid_run_record()` exercises the full `run_wiring` path

**Offline Tests:**

- Marked with: `@pytest.mark.offline`
- Scope: Tests that have no external dependencies
- Opposite: `@pytest.mark.integration` tests require external services
- Default behavior: Run offline tests, skip integration tests

## Common Patterns

**Async Testing:**

```python

# From test_sync_wrapper_guard.py — async test with event loop

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

- Wrap async test code in an `async def` function
- Call it with `asyncio.run()` from sync test context
- Use `pytest.raises()` to validate exception type and message

**pytest-asyncio mode:**

- Config: `[tool.pytest.ini_options]` sets `asyncio_mode = "auto"`
- Effect: Test functions marked `async def` automatically run in event loop
- Fixture scope: `asyncio_default_fixture_loop_scope = "function"` — each test gets a fresh loop

**Async Testing (databasise):**

```python

# From databasise/tests/test_tracer_end_to_end.py — native async tests

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
        concurrency_setting="sequential",
    )

    assert_valid_trace(record)
    assert record["partial"] is False
```

**Pattern:**

- Use native `async def test_*()` (pytest-asyncio runs it in event loop automatically)
- Fixtures like `store_root` are injected and work with async tests
- Call async functions with `await` directly (no need to wrap in `asyncio.run()`)

**Error Testing:**

```python

# From test_sync_wrapper_guard.py — validate error messages are actionable

with pytest.raises(RuntimeError) as exc_info:
    executor.submit(call_off_thread).result()

message = str(exc_info.value)
assert "insert()" in message
assert "await ainsert(" in message
assert "deadlock" not in message.lower()  # Confirm old misleading wording removed
assert calls == [], "coro_factory should not run on a mismatched loop"
```

**Pattern:**

- Check exception type with `pytest.raises(ExceptionType)`
- Validate error message content with substring assertions
- Verify side effects (e.g., factory was not called)
- Document expected behavior change if fixing a regression

**pytest markers and configuration:**

```python
def pytest_configure(config):
    """Register custom markers for LightRAG tests."""
    config.addinivalue_line("markers", "offline: marks tests as offline (no external dependencies)")
    config.addinivalue_line("markers", "integration: marks tests requiring external services (skipped by default)")
    config.addinivalue_line("markers", "requires_db: marks tests requiring database")
    config.addinivalue_line("markers", "requires_api: marks tests requiring LightRAG API server")

def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip integration tests by default."""
    if config.getoption("--run-integration"):
        return
    skip_integration = pytest.mark.skip(reason="Requires external services(DB/API), use --run-integration to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
```

**Pattern:**

- Register custom markers in `pytest_configure()`
- Implement test filtering in `pytest_collection_modifyitems()`
- Allows dynamic skip/run decisions based on CLI flags

## Documentation Validation (Gate Scripts)

**Pattern (non-code, but important convention):**

- Location: `docs/system-model/` contains markdown gate scripts (`*-check.sh`)
- Files: `anatomy-check.sh`, `catalog-check.sh`, `model-check.sh`, `parts-check.sh`, `rig-check.sh`
- Scope: Structural and content validation of design documents
- Output: `FAIL: <check-name> — <diagnosis>` for each failure; `OK <n> checks` on success

**Example checks (from `model-check.sh`):**

- Structural extraction: Section headings present and in correct order
- Vocabulary closure: Table cells use only allowed values (e.g., `holds`, `does-not-hold`)
- Pointer discipline: Marked sections carry proper citations
- Table completeness: Exactly 26 scoring rows with no gaps or duplicates

**Pattern:**

- Exit code 0: All checks pass
- Exit code 1: At least one check failed (with diagnostic printed)
- Guard-class failures: Missing structural anchors fail loudly (CR-01 class)
- Legitimate zeros: Empty filtered result sets (e.g., no "written" sections yet) pass legitimately

---

*Testing analysis: 2026-08-31*

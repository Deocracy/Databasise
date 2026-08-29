# Coding Conventions

**Analysis Date:** 2026-08-29

## Naming Patterns

**Files (Python):**
- Lowercase with underscores: `addon_params.py`, `base.py`, `chunk_schema.py`, `constants.py`, `exceptions.py`
- Pattern: `module_name.py` for single logical units
- Test files: `test_*.py` or `*_test.py` (test directory structure mirrors source)

**Files (JavaScript/TypeScript):**
- Component files: PascalCase without spaces
- Example: `lightrag_webui/` subdirectories and component files follow consistent naming
- Test files: `.test.tsx`, `.test.ts` (co-located with source)

**Functions (Python):**
- camelCase for private/internal: `_run_sync()`, `_owning_loop`
- snake_case for public: `insert()`, `query()`, `delete_by_entity()`, `initialize_rag()`
- Async variants prefixed with `a`: `ainsert()`, `aquery()` (matching sync alternatives)
- Test functions: `test_*()` pattern (e.g., `test_run_sync_runs_coroutine_when_no_loop_running()`)

**Variables (Python):**
- snake_case throughout: `owning_loop`, `test_artifacts`, `run_integration_tests`
- Private/internal: leading underscore `_hermetic_mineru_env`
- Boolean fixtures/flags: descriptive names like `keep_test_artifacts`, `stress_test_mode`, `parallel_workers`

**Types/Classes (Python):**
- PascalCase: `LightRAG`, `RuntimeError`, `ThreadPoolExecutor`
- Exception classes suffix with `Error` or `Exception`: `RuntimeError`

**Types (TypeScript):**
- Interfaces and Types: PascalCase
- Enums: PascalCase
- Example from eslint config: React version `19.0` implies typed component props

## Code Style

**Formatting (Python):**
- Tool: None explicitly configured (inferred from pyproject.toml defaults)
- Line length: Not specified in config
- Indent: Python default (4 spaces assumed)
- Convention: Follows PEP 8 style guide (observed from test structure)

**Formatting (JavaScript/TypeScript):**
- Tool: Prettier
- Config file: `v1/lightrag_webui/.prettierrc.json`
- Settings:
  - `semi: false` — No semicolons
  - `tabWidth: 2` — 2-space indentation
  - `singleQuote: true` — Single quotes for strings
  - `printWidth: 100` — Max 100 characters per line
  - `trailingComma: "none"` — No trailing commas
  - `endOfLine: "crlf"` — Windows-style line endings
  - `plugins: ["prettier-plugin-tailwindcss"]` — Tailwind CSS class sorting

**Linting (Python):**
- Tool: ruff
- Config: `pyproject.toml` section `[tool.ruff]`
- Target version: `py310` (Python 3.10)
- Scope: Code quality and style checks (specific rules configured via ruff)

**Linting (JavaScript/TypeScript):**
- Tool: ESLint (flat config format)
- Config file: `v1/lightrag_webui/eslint.config.js`
- Parser: TypeScript ESLint (`typescript-eslint`)
- Environment: Browser globals
- React version: 19.0
- Key rules:
  - `@stylistic/indent: ['error', 2]` — Enforce 2-space indentation
  - `@stylistic/quotes: ['error', 'single']` — Enforce single quotes
  - `@typescript-eslint/no-explicit-any: ['off']` — Disable `any` type restrictions (intentionally permissive)
  - React Hooks rules enabled
  - React Refresh rules enabled
  - JSX runtime rules from React 19 enabled

## Import Organization

**Order (Python):**
1. Standard library imports (`asyncio`, `sys`, etc.)
2. Third-party imports (`pytest`, `aiohttp`, etc.)
3. Relative imports from the package (`.` and `..`)

**Order (JavaScript/TypeScript):**
1. External packages (`react`, `@eslint/js`, etc.)
2. Local/relative imports
- Example from eslint.config.js shows imports grouped before re-export

**Path Aliases:**
- Python: Package-relative imports using `lightrag.*` namespace
- TypeScript: Inferred alias for `@` (common React pattern); verify in `tsconfig.json`
- Example: `from lightrag.lightrag import _run_sync`

## Error Handling

**Patterns (Python):**
- Async context: Errors in event-loop validation are raised eagerly before coroutine creation
- Example from `test_sync_wrapper_guard.py`: `_run_sync()` raises `RuntimeError` with actionable messages pointing to async alternatives
- Pattern: Guard checks run *before* lazy factory invocation, preventing dangling un-awaited coroutines
- Async-safe: Use try/finally blocks to ensure cleanup in async context managers

**Patterns (JavaScript/TypeScript):**
- React context: Error boundaries implied by plugin configuration
- API patterns (inferred from FastAPI backend): HTTP error responses with clear status codes
- Guard against error states with early validation (same pattern as Python)

## Logging

**Framework (Python):**
- Assumed: `logging` module (standard library)
- Pattern: Used implicitly in test fixtures for environment setup messages
- No external log aggregation dependency in pyproject.toml

**Framework (JavaScript/TypeScript):**
- Not explicitly configured in web UI config
- Browser console logging assumed (standard `console.*`)
- No structured logging dependency detected

**Patterns:**
- Tests log setup state via pytest fixtures (informational level)
- Example: `_hermetic_mineru_env` fixture documents why each env var is stripped (self-documenting monkeypatch)

## Comments

**When to Comment (Python):**
- Document non-obvious guard conditions
- Example from conftest: Multi-line comments explain why environment variables are stripped across tests (prevents test isolation leaks)
- Example from test_sync_wrapper_guard.py: Detailed module-level docstring explains event-loop synchronization rules and two misuse modes
- Pragma comments used for test coverage: `# pragma: no cover` marks code never reached on success path

**When to Comment (JavaScript/TypeScript):**
- Not explicitly documented in config; assume React conventions
- JSDoc for component props inferred from React 19 setup

**JSDoc/TSDoc:**
- Python: Module-level and class-level docstrings expected (seen in test files)
- TypeScript: Inferred JSDoc comments for function signatures and types

## Function Design

**Size (Python):**
- Test functions: Focused on a single guard or behavior (e.g., `test_run_sync_raises_clear_error_inside_running_loop` tests one error condition)
- Helper functions: Named clearly to express intent (e.g., `side_body()` in gate scripts extracts structured sections)
- Anti-pattern: Avoid monolithic test functions; prefer one assertion per test or grouped assertions with clear section comments

**Parameters (Python):**
- Async functions: Parameters passed through wrapper functions (`_run_sync(factory, sync_name="insert", async_name="ainsert", owning_loop=loop)`)
- Fixtures: Named to describe their role (`keep_test_artifacts`, `stress_test_mode`, `parallel_workers`)
- CLI option forwarding: Via `request.config.getoption()` with fallback to environment variables

**Return Values (Python):**
- Async wrappers: Return same type as inner coroutine
- Test fixtures: Return boolean (mode flags) or integer (worker counts)
- Early validation: Functions return or raise early, no sentinel values for success (fail-fast principle)

**Size (JavaScript/TypeScript):**
- Components: Assume modular, single-responsibility pattern (inferred from plugin configuration for React Hooks)
- Functions: Leverage TypeScript for type safety instead of runtime checks

## Module Design

**Exports (Python):**
- Pattern: Package-level `__all__` declarations (assumed from structure)
- Example: `lightrag.lightrag` exports `_run_sync` for public use in wrappers
- Async/sync pairing: Public API exposes both sync and async variants

**Exports (JavaScript/TypeScript):**
- ESLint rule: `react-refresh/only-export-components` enforced with warning level
- Pattern: React components are default exports or named exports
- Rule allows `allowConstantExport: true` for constants alongside components

**Barrel Files:**
- Not explicitly configured; assume standard pattern (index files re-export from subdirectories)
- Example inferred: `lightrag/api/webui/` likely has index.ts/index.js

---

*Convention analysis: 2026-08-29*

<!-- refreshed: 2026-09-03 -->
# Coding Conventions

**Analysis Date:** 2026-09-03

## Naming Patterns

**Files:**
- Lowercase with underscores: `addon_params.py`, `base.py`, `chunk_schema.py`, `exceptions.py`
- Pattern: `module_name.py` for single logical units
- Test files: `test_*.py` (co-located in tests/ directory, mirrors source structure)
- Component files (TypeScript): PascalCase, e.g., `App.tsx`, `GraphViewer.tsx`

**Functions:**
- Python public: snake_case, e.g., `insert()`, `query()`, `delete_by_entity()`, `initialize_rag()`
- Python async variants: prefix with `a`, e.g., `ainsert()`, `aquery()` (matching sync alternatives)
- Python private/internal: leading underscore, e.g., `_run_sync()`, `_owning_loop()`, `_hermetic_mineru_env()`
- TypeScript: camelCase, e.g., `handleApiKeyAlertOpenChange()`, `performHealthCheck()`
- Test functions: `test_*()` pattern

**Variables:**
- Python: snake_case throughout, e.g., `chunk_tokens`, `parallel_workers`, `keep_test_artifacts`
- TypeScript: camelCase, e.g., `apiKeyAlertOpen`, `isMountedRef`, `enableHealthCheck`
- Boolean fixtures/flags: descriptive, e.g., `keep_test_artifacts`, `stress_test_mode`, `parallel_workers`

**Types/Classes:**
- Python classes: PascalCase, e.g., `LightRAG`, `RuntimeError`, `APIStatusError`
- Python exceptions: suffix with `Error` or `Exception`, e.g., `StorageNotInitializedError`, `PipelineNotInitializedError`
- TypeScript: PascalCase interfaces, types, enums

## Code Style

**Formatting (Python):**
- Tool: ruff (linter)
- Target version: `py310` (v1) or `py311` (databasise)
- Indent: 4 spaces
- Convention: PEP 8 style guide (inferred from test structure)
- Line length: Not explicitly specified

**Formatting (TypeScript/JavaScript):**
- Tool: Prettier
- Config: `v1/lightrag_webui/.prettierrc.json`
- Settings:
  - `tabWidth: 2` (2-space indent)
  - `singleQuote: true` (single quotes)
  - `semi: false` (no semicolons)
  - `printWidth: 100`
  - `trailingComma: "none"`
  - `endOfLine: "crlf"` (Windows line endings)
  - Plugin: prettier-plugin-tailwindcss

**Linting (Python):**
- Tool: ruff
- Config: `[tool.ruff]` in pyproject.toml
- Target version: `py310` (v1) or `py311` (databasise)

**Linting (TypeScript/JavaScript):**
- Tool: ESLint (flat config)
- Config: `v1/lightrag_webui/eslint.config.js`
- Parser: typescript-eslint
- Key rules:
  - `@stylistic/indent: ['error', 2]` — 2-space indentation
  - `@stylistic/quotes: ['error', 'single']` — single quotes
  - `@typescript-eslint/no-explicit-any: ['off']` — `any` allowed
  - React Hooks rules enabled
  - React Refresh rules enabled
  - `react-refresh/only-export-components: ['warn', { allowConstantExport: true }]`

## Import Organization

**Python:**
- Start with `from __future__ import annotations`
- Order: stdlib → third-party → local
- Example (v1/lightrag/lightrag.py:1-78):
  - Lines 1-8: future, stdlib (traceback, asyncio, os, time, warnings, copy)
  - Lines 10-13: optional dependency (httpx) in try/except
  - Lines 14-32: stdlib types and dataclass
  - Lines 34-78: local lightrag.* imports
- No blank lines within groups; one blank line between groups

**TypeScript:**
- Path alias: `@/*` → `./src/*` (tsconfig.json:25-26)
- Import pattern: `import { named } from '@/path/to/module'`
- Group: external → feature → utils
- Example (App.tsx:1-20):
  - React/library imports first
  - Then `@/components`, `@/contexts`, `@/stores`, `@/api`, `@/features`

## Error Handling

**Strategy:**
- Custom exception classes with descriptive messages
- Guard checks run **before** lazy factory invocation (prevents un-awaited coroutines)
- RuntimeError raised eagerly with actionable error messages

**Patterns:**
- Exception classes carry context: `APIStatusError` stores response, status_code, request_id
- Example: `StorageNotInitializedError` includes initialization code snippet in message
- Async guards: validate loop matches before coroutine creation
  - `test_run_sync_raises_clear_error_inside_running_loop` — guard runs before factory
  - `test_run_sync_does_not_create_coroutine_when_it_raises` — factory never invoked if guard fails
- Multi-line error messages name both sync and async method signatures for clarity

**Anti-Pattern:**
- Do not create coroutines inside guards (causes un-awaited warning if guard rejects)
- Do not defer validation beyond guard check

## Logging

**Framework:**
- Python: standard `logging` module
- TypeScript: browser `console.*` (no external dependency)

**Patterns:**
- Test fixtures log setup reasoning (self-documenting)
- _hermetic_mineru_env fixture documents why env vars are cleared (45-line comment explaining test isolation)
- No structured logging library; plain text logs assumed

## Comments

**When to Comment:**
- Document non-obvious guard conditions and invariants
- Multi-line comments explain state management (e.g., conftest.py lines 11-44)
- Module docstrings reference governing specifications
- Complex async synchronization rules: test_sync_wrapper_guard.py lines 1-30 explain event-loop lifetime and two misuse modes

**Pragma Comments:**
- `# pragma: no cover` marks unreachable paths (test factory functions that must never execute)

**JSDoc/TSDoc:**
- Python: module-level docstrings expected; class-level for contracts
- TypeScript: JSDoc for function signatures (inferred from React 19 setup)

## Function Design

**Size:**
- Focused on one guard/behavior (e.g., `test_run_sync_raises_clear_error_inside_running_loop`)
- Test functions: one assertion or grouped assertions with clear comments
- Helper functions: named to express intent

**Parameters:**
- Async wrappers pass via factory: `_run_sync(factory, sync_name="insert", async_name="ainsert", owning_loop=loop)`
- Fixtures named descriptively: `keep_test_artifacts`, `stress_test_mode`, `parallel_workers`
- CLI options via `request.config.getoption()` with env var fallback

**Return Values:**
- Async wrappers return same type as inner coroutine
- Test fixtures return boolean or integer
- Early validation: return or raise early; no sentinel success values (fail-fast)

## Module Design

**Exports:**
- Async/sync pairing in public API (e.g., `insert()` + `ainsert()`)
- Example: `from lightrag.lightrag import _run_sync` (public wrapper)
- Package-level `__all__` (assumed)

**Barrel Files:**
- Pattern: index files re-export from subdirectories
- Example: `lightrag/api/webui/` structure

---

*Convention analysis: 2026-09-03*

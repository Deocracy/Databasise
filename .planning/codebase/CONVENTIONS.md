---
last_mapped_commit: 8044f9a
---
# Coding Conventions

**Analysis Date:** 2026-09-08

## Overview

This codebase contains two distinct Python projects with shared conventions:

- **v1/** — LightRAG fork monolith (Python + React frontend)
- **databasise/** — Databasise 2.0 agnostic machine rebuild (Python only)

Both follow PEP 8 style with snake_case for files and functions, and are linted via ruff with pre-commit hooks (excluding the React frontend).

## Naming Patterns

### Files

**Python:**
- Pattern: `snake_case.py` — lowercase with underscores
- Examples: `addon_params.py`, `base.py`, `chunk_schema.py`, `constants.py`, `exceptions.py`
- One logical unit per file (v1 and databasise both follow this)

**Test files:**
- Pattern: `test_*.py` — prefix with `test_`
- Location: Parallel directory structure to source (e.g., `v1/tests/` mirrors `v1/lightrag/`)
- Databasise applies this more strictly; test dirs mirror source module hierarchy

**Frontend (v1 only):**
- React components: PascalCase (e.g., `GraphViewer.tsx`)
- Styles: Component-adjacent or in `styles/`
- Tests: `.test.tsx` or `.test.ts` (co-located with source)

### Functions

**Public API:**
- Pattern: `snake_case`
- Examples: `insert()`, `query()`, `delete_by_entity()`, `initialize_rag()`
- Return types and parameters documented in docstrings or type hints

**Private/Internal:**
- Pattern: Leading underscore `_function_name()`
- Examples: `_run_sync()`, `_owning_loop`, `_hermetic_mineru_env` (fixture)
- Used for implementation details not part of public interface

**Async pairs:**
- Async variants prefixed with `a`: `ainsert()`, `aquery()` (matching sync alternatives)
- Example: `insert()` (sync) vs `ainsert()` (async coroutine)
- This pattern is used throughout v1 (`_run_sync` wraps async into sync)

**Test functions:**
- Pattern: `test_<component>_<behavior>`
- Examples: `test_run_sync_runs_coroutine_when_no_loop_running()`, `test_phase_success_criteria()`
- Descriptive names (v1 and databasise both enforce this)

### Variables

**Regular variables:**
- Pattern: `snake_case`
- Examples: `owning_loop`, `test_artifacts`, `parallel_workers`
- Boolean names descriptive: `keep_test_artifacts`, `stress_test_mode`

**Type annotations:**
- PascalCase: `LightRAG`, `RuntimeError`, `ThreadPoolExecutor`
- Exceptions suffix with `Error` or `Exception`: `IndexFlushError`, `RuntimeError`

**Constants:**
- UPPERCASE_WITH_UNDERSCORES: `DEFAULT_CHUNK_P_SIZE`, `DEFAULT_MAX_GLEANING`
- Location: `v1/lightrag/constants.py`, corresponding module constants in databasise

### Modules & Packages

**Databasise 2.0 structure:**
- `databasise.identity` — Configuration identity and hashing
- `databasise.parts` — Component registry and schemas
- `databasise.parts_core` — Reference implementations (fake LLM, retriever)
- `databasise.stores` — Storage backends (graph, vector, KV, blob)
- `databasise.runner` — Execution engine (trace, budget, scheduler)
- `databasise.validator` — Wiring validation (cycles, depth, blast radius)
- `databasise.seam` — Public contract boundary (REST or MCP)

**v1 structure:**
- `lightrag.lightrag` — Main facade (`LightRAG` class)
- `lightrag.base` — Abstract storage interfaces
- `lightrag.kg` — Graph storage implementations + factory
- `lightrag.llm` — LLM provider integrations
- `lightrag.parser` — File format dispatch
- `lightrag.chunker` — Text segmentation
- `lightrag.api` — FastAPI server + WebUI

## Code Style

### Formatting

**Python:**
- Tool: **ruff** (format and lint)
- Config files: `v1/pyproject.toml`, `databasise/pyproject.toml`
- Target versions: v1 = `py310`, databasise = `py311`
- Line length: Not explicitly set (defaults to 88)
- Indent: 4 spaces (PEP 8 default)
- Pre-commit hooks: `ruff-format` and `ruff --fix` (excluding React frontend)

**JavaScript/TypeScript (v1 frontend only):**
- Tool: **Prettier**
- Config: `v1/lightrag_webui/.prettierrc.json`
- Settings:
  - 2-space indent (`tabWidth: 2`)
  - Single quotes (`singleQuote: true`)
  - No trailing commas (`trailingComma: "none"`)
  - Print width: 100
  - End of line: `crlf`
  - Plugin: `prettier-plugin-tailwindcss`

### Linting

**Python:**
- Tool: **ruff** (via pre-commit)
- Scope: All Python code except v1's webui frontend
- Key settings: `--fix` enabled, `--ignore=E402` (import after code)

**JavaScript/TypeScript:**
- Tool: **ESLint** (flat config)
- Config: `v1/lightrag_webui/eslint.config.js`
- Parser: TypeScript ESLint
- Environment: Browser globals
- React version: 19.0
- Key rules:
  - `react-refresh/only-export-components`: warn with `allowConstantExport: true`
  - `react-hooks`: recommended rules enabled
  - `@stylistic/indent`: 2 spaces
  - `@stylistic/quotes`: single quotes
  - `@typescript-eslint/no-explicit-any`: off

## Import Organization

**Order (Python):**
1. `__future__` imports (`from __future__ import annotations`)
2. Standard library (`asyncio`, `os`, `time`, `dataclasses`)
3. Third-party packages (`pydantic`, `pytest`)
4. Local package imports (`from lightrag.base import ...` or `from databasise.stores import ...`)
5. Relative imports (rarely used; absolute preferred)

**Path aliases:**
- v1: Uses absolute `lightrag.*` namespace (e.g., `from lightrag.llm import ...`)
- Databasise: Uses absolute `databasise.*` namespace
- Frontend: Path alias `@` for `src/` (inferred from tsconfig.json)

**Example from v1/lightrag/lightrag.py:**
```python
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from pydantic import BaseModel

from lightrag.base import BaseGraphStorage
from lightrag.kg import verify_storage_implementation
from lightrag.utils import logger
```

## Error Handling

### Pattern

**Guard checks run before lazy evaluation:**
- Errors raised eagerly before coroutine creation (prevents un-awaited coroutines)
- Example: `_run_sync()` in v1 validates loop state before creating the inner coroutine
- If guard fails, the coroutine factory is never called

**Async errors:**
- Try/finally blocks ensure cleanup in async context managers
- Errors propagate via exception, not sentinel return values

**Extraction/query errors:**
- Parser failures: Document marked `PARSE_FAILED`, no further processing
- LLM failures: Logged, stored in `doc_status.error_msg`, ingest continues (partial KG better than none)
- Query failures: Return empty context; LLM generates response from history alone, or raise with fallback prompt

**Example from v1/tests/test_sync_wrapper_guard.py:**
```python
def factory():  # pragma: no cover - must never be reached
    raise AssertionError("coro_factory must not be called inside a loop")

async def _inside_loop():
    return _run_sync(factory, sync_name="insert", async_name="ainsert")

# Guard fires before factory() is called:
with pytest.raises(RuntimeError) as exc_info:
    asyncio.run(_inside_loop())
```

## Logging

**Framework:** Python `logging` module (standard library)

**Patterns:**
- Used in test fixtures to document environment setup (informational level)
- Logger instance: `from lightrag.utils import logger`
- No external log aggregation in base dependencies (optional via langfuse)
- Frontend: Browser `console.*` (standard)

**No explicit logging config in codebase** — assumes development defaults plus external aggregation layer (optional).

## Comments

### When to Comment

- Document non-obvious guard conditions
- Explain why an error state is handled a certain way
- Multi-line comments for complex decisions (e.g., why env vars are stripped in fixtures)

**Example from v1/tests/conftest.py:**
```python
"""Make every test start with parser-routing env vars in their unset state.

``lightrag/api/{auth,config}.py`` call ``load_dotenv(override=False)``
at import time, leaking the developer's local ``.env`` into the test
process. The MinerU test fixtures assume ``MINERU_API_MODE`` is unset...
"""
```

### JSDoc/TSDoc (Frontend only)

- Component props documented inline
- Function signatures typed via TypeScript
- Not explicitly enforced; inferred from React 19 setup

### Module docstrings

**Python:**
- Module-level docstring required for:
  - Test files (explaining test fixtures and acceptance criteria)
  - Modules with non-obvious behavior (e.g., `_run_sync` explanation in test file)
  - Public API modules
- Format: Plain text, may span multiple paragraphs
- Example: databasise/tests/conftest.py describes the role of each fixture

## Function Design

### Size

- Focused on a single guard or behavior
- Test functions: One assertion per test (or grouped with clear comments)
- Helper functions: Named to express intent

**Anti-pattern:** Monolithic test functions bundling multiple concerns

### Parameters

- Async functions: Parameters passed through wrapper functions
- Example: `_run_sync(factory, sync_name="insert", async_name="ainsert", owning_loop=loop)`
- Fixtures: Named to describe role (`keep_test_artifacts`, `stress_test_mode`, `parallel_workers`)

### Return Values

- Early validation: Functions return or raise early, no sentinel values for success (fail-fast principle)
- Sync/async pairs: Async variant returns same type as sync
- Test fixtures: Return boolean (mode flags) or integer (worker counts)

## Module Design

### Exports

**Barrel files:** `__all__` declarations at package level (assumed pattern)

**Async/sync pairing:**
- Public API exposes both sync and async variants
- Example: `lightrag.lightrag` exports `_run_sync` for public use in wrappers

**Frontend:**
- React components: Default or named exports
- ESLint rule enforced: `react-refresh/only-export-components` (warn level)
- Rule allows constants: `allowConstantExport: true`

### Circular Import Prevention

- Parser plugins loaded late (in `load_third_party_parsers()`) to avoid circular dependency
- No compile-time coupling to external parser libraries

## Architectural Patterns

### Storage Abstraction

All storage backends (graph, vector, KV) implement base interfaces:
- `BaseGraphStorage` — entity/relation queries, upsert, delete
- `BaseVectorStorage` — upsert, query, delete with embeddings
- `BaseKVStorage` — get, set, delete, optional filter_by_source

Factory pattern (`factory.py`) routes backend selection at runtime based on env vars.

### Modular LLM Layer

Each provider (OpenAI, Gemini, Ollama, Anthropic, Bedrock) is a separate subclass. Role-based config allows per-role LLM selection.

### Async-First Orchestration

- `pipeline.py` uses `_PipelineMixin` with queues and worker pools
- Concurrency via `asyncio.gather()`, `PriorityQueue`
- CPU-bound tokenization uses `loop.run_in_executor()` to avoid blocking

## Pragma Comments

### Test Coverage

- `# pragma: no cover` — marks code never reached on success path (e.g., guard failure factory in tests)
- Used in v1 tests to exclude error paths from coverage (fail-fast prevents normal execution)

---

*Convention analysis: 2026-09-08*

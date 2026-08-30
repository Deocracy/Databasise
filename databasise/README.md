# databasise

The agnostic machine: fitting contract + versioned components over machine-owned primitives
(graph, vector, KV databases; LLM/embedding/reranker clients). Implements the v1.0 system model
in `docs/system-model/` (CONTRACT.md, RIG.md). A modality (LightRAG, HippoRAG 2, future
paradigms) becomes a wiring of components over these primitives instead of a monolithic library.

## Boundary from v1 (D-14)

`databasise/` is a new top-level package beside `v1/`, and it is **never** a `uv` workspace
member of `v1/`. Nothing under `databasise/` imports from `v1` at any point in this phase —
no `import lightrag`, no `from lightrag...`. Where a v1 module has a proven pattern this
package needs, the pattern is **copied**, never imported, and attribution goes in the
component registry's `upstream_ref` field per CONTRACT.md §7.

Why independent rather than a shared workspace: a shared `uv` workspace with `v1/` would put
v1's server-backed dependency set (Neo4j, Milvus, Qdrant, asyncpg, OpenSearch, the React build
chain) on `databasise/`'s resolution graph — making EMBED-01's "no external DB servers" claim a
property of a resolver decision rather than a property of the dependency list itself. Kept
independent, the dependency list *is* the proof: `databasise/pyproject.toml` declares exactly
four runtime dependencies (`pycozo[embedded]`, `faiss-cpu`, `rfc8785`, `pydantic`), none of
which is a client for a database server.

## Python floor

`requires-python = ">=3.11"`, deliberately higher than v1's `>=3.10` (`v1/pyproject.toml:14`).
The runner uses stdlib `asyncio.TaskGroup`, which requires 3.11+, rather than taking an `anyio`
dependency purely to preserve a 3.10 floor nothing in this phase needs. This is legitimate
because D-14 makes `databasise/` a separate package that need not inherit v1's floor.

## Layout

```
databasise/
├── identity/     # config_hash, instance-hash, JCS canonicalization (D-12)
├── parts/        # explicit in-code part registry, NodeKind tagged sum (D-13)
├── validator/     # parse, cycle detection, depth, execution_mode
├── runner/        # TopologicalSorter + TaskGroup scheduler, budget, trace
├── stores/        # Cozo (graph), Faiss (vector), SQLite (KV/lexical) adapters
└── tests/         # pytest harness; conftest.py provides store_root, rig_trace_schema,
                    # assert_valid_trace fixtures for every later test in this phase
```

## Development

```bash
cd databasise
uv sync
uv run pytest
```

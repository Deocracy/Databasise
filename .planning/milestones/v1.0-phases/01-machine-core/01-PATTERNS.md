# Phase 1: Machine Core - Pattern Map

**Mapped:** 2026-08-30
**Files analyzed:** 17 (new, under `databasise/`)
**Analogs found:** 12 / 17 (v1 port-by-copy references; 5 have no analog)

**Constraint (CONTEXT.md D-14):** `databasise/` is a new top-level package. **Nothing in it imports
from `v1/`.** Every analog below is a **port-by-copy reference** — read the excerpt, re-implement it
in `databasise/`, record the source in the component registry's `upstream_ref` field. Never write
`from lightrag... import ...` inside `databasise/`.

**Anti-analog (CONTEXT.md D-11) — do NOT replicate:**
`v1/lightrag/kg/shared_storage.py` module-level singletons: `_manager` (line 66), `_storage_keyed_lock`
(line 98), `_global_concurrency_limits` (line 111), `class UnifiedLock` (line 175), the
`initialize_share_data()` function that populates them via `multiprocessing.Manager()` (lines
1285-1396). This is v1's hybrid `asyncio.Lock` + `multiprocessing.Manager.Lock` process-wide
concurrency model. D-09 replaces it with a per-node semaphore whose size enters `config_hash`; D-11
forbids importing or re-deriving the singleton shape at all, even in new code, because a process-wide
cap would throttle one arm's fan-out against an unrelated arm, contaminating Phase 6's comparison.

## File Classification

| New File (`databasise/...`) | Role | Data Flow | Closest v1 Analog | Match Quality |
|---|---|---|---|---|
| `identity/canon.py` | utility | transform | *(none — new primitive)* | no analog |
| `identity/instance.py` | utility | transform | *(none — new primitive)* | no analog |
| `parts/schema.py` | model | transform | `v1/lightrag/base.py` (`QueryParam` dataclass shape, `TextChunkSchema` TypedDict) | partial |
| `parts/registry.py` | config/service | CRUD (in-memory dict) | `v1/lightrag/kg/factory.py` (`get_storage_class`) | role-match |
| `validator/parse.py` | service | transform | `v1/lightrag/base.py` (ABC + dataclass validation shape) | partial |
| `validator/cycles.py` | utility | transform | *(none — no stdlib/v1 Tarjan; hand-roll per RESEARCH Pattern 2)* | no analog |
| `validator/depth.py` | utility | transform | *(none — new primitive)* | no analog |
| `validator/execution_mode.py` | service | request-response (refusal) | `v1/lightrag/kg/factory.py` (name→impl dispatch, refusal-by-name shape) | partial |
| `runner/scheduler.py` | service | event-driven (DAG exec) | *(none in v1 — v1 has no structured-concurrency runner; use RESEARCH.md Pattern 1 stdlib shape)* | no analog |
| `runner/budget.py` | service | event-driven | *(none — new primitive)* | no analog |
| `runner/trace.py` | service | event-driven | `v1/lightrag/base.py:DocProcessingStatus` (status/progress dataclass shape) | partial |
| `stores/graph.py` (Cozo adapter) | model/storage | CRUD | `v1/lightrag/kg/cozo_impl.py` (`CozoGraphStorage`) | exact |
| `stores/vector.py` (Faiss adapter) | model/storage | CRUD | `v1/lightrag/kg/faiss_impl.py` (`FaissVectorDBStorage`) | exact |
| `stores/kv.py`, `stores/lexical.py` | model/storage | CRUD | `v1/lightrag/base.py:BaseKVStorage` (interface shape only; SQLite/FTS5 body is new — no KV/lexical incumbent) | role-match |
| `stores/blob.py` | model/storage | file-I/O | *(none — new primitive, D-06)* | no analog |
| `registry_artifact/index.py`, `ledger/ledger.py` | model/storage | CRUD + event-driven (append-only) | *(none — new primitives, CONTRACT §7)* | no analog |
| `parts_core/*.py` (D-04 reference parts) | service | request-response | `v1/lightrag/base.py:StorageNameSpace` (`initialize`/`finalize`/`drop` lifecycle ABC shape) | partial |

## Pattern Assignments

### `databasise/stores/graph.py` (model/storage, CRUD)

**Analog:** `v1/lightrag/kg/cozo_impl.py` (`CozoGraphStorage`, 977 lines) — `upstream_ref: v1/lightrag/kg/cozo_impl.py`

**Imports pattern** (lines 68-89) — note the `shared_storage` import (line 81) is the one thing to
NOT port; everything else travels:
```python
from __future__ import annotations
import asyncio, json, os
from collections import deque
from dataclasses import dataclass, field
from typing import Any, final

from lightrag.base import BaseGraphStorage           # DO NOT port — no v1 import (D-14)
from lightrag.types import KnowledgeGraph, ...        # DO NOT port
from .shared_storage import get_namespace_lock, ...   # DO NOT port — anti-analog (D-11)

try:
    from pycozo.client import Client as CozoClient
except ImportError as _cozo_import_err:
    raise ImportError(
        "cozo-embedded is required for CozoGraphStorage. "
        "Install with: pip install 'pycozo[embedded]'"
    ) from _cozo_import_err
```
Port `pycozo.client.Client` import and the `ImportError`-with-actionable-message pattern; drop the
`lightrag.*` imports and rebuild the interface locally (see `stores/kv.py` note below on the ABC
shape, ported separately from `base.py`).

**Core pattern — deferred-write buffer discipline** (docstring lines 25-46, MUST travel verbatim as
design constraint, not just as text):
```
Cozo commits each :put/:rm immediately in its own transaction, but the caller
buffers writes in-memory and flushes at index_done_callback. Four in-process buffers:
    _pending_node_puts  : dict[id, attrs]
    _pending_edge_puts  : dict[(src,tgt), attrs]   # canonical order
    _pending_node_rms   : set[id]
    _pending_edge_rms   : set[(src,tgt)]           # canonical order
Reads consult these buffers FIRST (read-your-writes before flush).
All four cleared on index_done_callback (commit) or drop_pending_index_ops (abort).
```

**Sync-to-async dispatch pattern** (docstring lines 40-45): `pycozo.Client.run()` is synchronous —
every call MUST go through `asyncio.get_running_loop().run_in_executor(None, ...)`.

**Security pattern** (docstring lines 47-52): all node IDs, edge endpoints, and query values are
**bound parameters**, never string-interpolated into CozoScript. Entity names containing Datalog
metacharacters (`{`, `}`, `?`, `*`) must not alter query structure.

**Helper excerpts to port** (lines 96-120):
```python
def _cozo_rows(result: Any) -> list[list]:
    """Normalise a pycozo run() result to list[list].
    pycozo 0.7.6 returns {"headers": [...], "rows": [...]} when pandas is not
    importable, or a pandas DataFrame when it is. Handle both."""
    if hasattr(result, "to_dict"):
        return result.values.tolist()
    return result.get("rows", [])

def _canonical_edge_key(src: str, tgt: str) -> tuple[str, str]:
    """(src, tgt) lexicographically ordered so A-B and B-A are the same key."""
    if src > tgt:
        return tgt, src
    return src, tgt
```

**Frozen-bug mitigations (Pitfall 2, non-negotiable — port forward, do not re-derive)**: avoid
`count()` aggregation (bug #244, silent 0-rows); store all keys as `String`, never `UUID` (bug
#296/#269, sort/coercion); consume JSON as dict, never rely on key order (bug #253); assert types on
round-trip (bug #275, wrong `DataValue` types). Regression shapes live in
`v1/tests/kg/test_cozo_graph_storage.py` — port that suite forward against the new adapter, not just
keep it running against the old one.

---

### `databasise/stores/vector.py` (model/storage, CRUD)

**Analog:** `v1/lightrag/kg/faiss_impl.py` (`FaissVectorDBStorage`, 1192 lines) — `upstream_ref: v1/lightrag/kg/faiss_impl.py`

**Core pattern:** deferred-embedding + pending-buffer symmetry with the Cozo adapter — `upsert()` at
line 332, `query()` at line 383. A `_PendingFaissDoc` dataclass (line 26) buffers docs awaiting
embedding before they enter the Faiss index; failures **raise**, they do not silently drop (lines
185, 550, 692-695, 742-744, 932-954 all document "if X raises, the pending buffer stays intact / no
partial write").

**Error handling pattern** (lines 734-744, `upsert`):
```python
except Exception as e:
    ...
    raise
...
# Explicit raise (not a log): a mismatch would mis-pair vectors
raise RuntimeError(
    ...
)
```
The house rule this demonstrates: an embedding-count mismatch or index-add failure raises before any
mutation — never a logged-and-continued partial write. Carry this into the new adapter; it matches
CONTEXT.md's stated house style ("refusals over silent fallbacks").

**Metadata sidecar pattern:** Faiss index + a separate `.meta.json` sidecar file; both must be
written together or neither commits (lines 932-954 document the two-phase raise discipline). Relevant
to `stores/vector.py`'s per-namespace directory layout under D-07 — the sidecar and index both live
inside the same namespace directory.

---

### `databasise/stores/kv.py`, `databasise/stores/lexical.py` (model/storage, CRUD)

**Analog for interface shape only:** `v1/lightrag/base.py:BaseKVStorage` (lines 382-437) —
`upstream_ref: v1/lightrag/base.py` (interface shape, not implementation — v1 has no SQLite/FTS5
backend to port; `lexical` is a new primitive per D-06).

**ABC method shape to reproduce** (lines 383-437, method signatures only — reimplement bodies against
SQLite, do not import):
```python
@dataclass
class BaseKVStorage(StorageNameSpace, ABC):
    async def get_by_id(self, id: str) -> dict[str, Any] | None: ...
    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]: ...
    async def filter_keys(self, keys: set[str]) -> set[str]: ...
    async def upsert(self, data: dict[str, dict[str, Any]]) -> None: ...
    async def delete(self, ids: list[str]) -> None: ...
    async def is_empty(self) -> bool: ...
```

**Lifecycle ABC to reproduce** (`StorageNameSpace`, lines 160-219):
```python
@dataclass
class StorageNameSpace(ABC):
    async def initialize(self): ...
    async def finalize(self): ...
    async def index_done_callback(self) -> None: ...
    async def drop_pending_index_ops(self) -> None: ...
    async def drop(self) -> dict[str, str]: ...
```
This four-method lifecycle (`initialize` / `finalize` / `index_done_callback` (commit) /
`drop_pending_index_ops` (abort) / `drop`) is the shape every `databasise/stores/*.py` adapter should
share — it is what makes the Cozo/Faiss deferred-write buffering above pluggable behind one interface.

---

### `databasise/parts/registry.py` (config/service, CRUD in-memory dict)

**Analog:** `v1/lightrag/kg/factory.py` (46 lines, read in full) — `upstream_ref: v1/lightrag/kg/factory.py`

**Core pattern — explicit dict-backed resolution with named fast paths** (lines 17-46):
```python
def get_storage_class(storage_name: str) -> Callable[..., Any]:
    if storage_name == "JsonKVStorage":
        from lightrag.kg.json_kv_impl import JsonKVStorage
        return JsonKVStorage
    if storage_name == "CozoGraphStorage":
        from lightrag.kg.cozo_impl import CozoGraphStorage
        return CozoGraphStorage
    # Fallback to dynamic import for other storage implementations.
    import_path = STORAGES[storage_name]
    module = importlib.import_module(import_path, package="lightrag")
    return getattr(module, storage_name)
```
D-13 wants a pure explicit dict (`name@version -> Part`), no dynamic-import fallback (that fallback is
exactly the `entry_points`-style extensibility D-13 explicitly rejects for Phase 1). Port the shape
(name-keyed lookup, lazy import inside each branch to avoid import-time cost for unused parts), drop
the `importlib.import_module` fallback branch entirely.

---

### `databasise/validator/execution_mode.py` (service, request-response/refusal)

**Analog for refusal-by-name shape:** `v1/lightrag/kg/factory.py` pattern of name-keyed dispatch,
inverted — D-08 requires refusing `subprocess`/`confined-unit`/`long-lived-service` **by name**, so the
shape to port is "known keys map to real work, everything else raises with the specific unmet name
mentioned in the message" — same shape as `cozo_impl.py`'s `ImportError` message pattern (lines 86-89
above): a specific, actionable message naming exactly what's missing, not a generic `NotImplementedError`.

---

### `databasise/runner/trace.py` (service, event-driven — D-10's run-record stamping)

**Analog for status/progress dataclass shape:** `v1/lightrag/base.py:DocProcessingStatus` (line 809) —
`upstream_ref: v1/lightrag/base.py` (shape only; fields are new per D-10).

```python
@dataclass
class DocProcessingStatus:
    ...
```
Read full field list at `v1/lightrag/base.py:808-`. Pattern to reuse: one dataclass carrying every
status/progress field a downstream consumer reads, populated incrementally during execution — apply
the same shape to D-10's field set (`cache_hit`, `arm_execution_order`, `realised_budget_share`,
`guards_fired`, determinism/concurrency setting) rather than inventing a different container shape.

---

## Shared Patterns

### Async dispatch for synchronous native clients
**Source:** `v1/lightrag/kg/cozo_impl.py` docstring lines 40-45
**Apply to:** `stores/graph.py` (pycozo), any other native-client adapter with a sync API
```python
result = await asyncio.get_running_loop().run_in_executor(None, client.run, query, params)
```

### Bound-parameter query construction (never string interpolation)
**Source:** `v1/lightrag/kg/cozo_impl.py` docstring lines 47-52
**Apply to:** `stores/graph.py`, any store adapter accepting LLM-extracted or user-controlled strings
as query input.

### Lifecycle ABC (`initialize`/`finalize`/`index_done_callback`/`drop_pending_index_ops`/`drop`)
**Source:** `v1/lightrag/base.py:StorageNameSpace` lines 160-219
**Apply to:** All four `stores/*.py` adapters (graph, vector, kv, lexical) — gives the runner one
uniform commit/abort contract regardless of backend.

### Raise-don't-silently-drop on write failure
**Source:** `v1/lightrag/kg/faiss_impl.py` lines 734-744, 932-954
**Apply to:** All store adapters and `runner/budget.py` — matches CONTEXT.md's stated house style
("refusals over silent fallbacks," specifics section) and D-10's point that a meter with nowhere to
write is not a meter.

### Explicit, actionable refusal messages naming the missing capability
**Source:** `v1/lightrag/kg/cozo_impl.py` lines 83-89 (`ImportError` message)
**Apply to:** `validator/execution_mode.py` (D-08's named refusals for `subprocess`/`confined-unit`/
`long-lived-service`).

## No Analog Found

Files with no close match in `v1` — planner should build these from `RESEARCH.md`'s Architecture
Patterns section (Pattern 1 for the runner, Pattern 2 for depth, Pattern 3 for artifact
registry/ledger, Pattern 4 for namespace derivation), not from a v1 port:

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `identity/canon.py`, `identity/instance.py` | utility | transform | `config_hash`/RFC 8785 canonicalisation is a new primitive; no v1 equivalent (v1 has no identity/versioning layer) |
| `validator/cycles.py`, `validator/depth.py` | utility | transform | Tarjan SCC + taint min-reduce is new; RESEARCH.md explicitly rejects pulling in `networkx` for this one algorithm (would reopen D-14's import boundary) — hand-roll per RESEARCH.md Pattern 2 |
| `runner/scheduler.py`, `runner/budget.py` | service | event-driven | v1 has no structured-concurrency wiring-graph runner at all — build from RESEARCH.md Pattern 1 (`graphlib.TopologicalSorter` + `asyncio.TaskGroup`), stdlib only |
| `stores/blob.py` | model/storage | file-I/O | Content-addressed blob store is a new primitive (D-06); v1 has no blob store |
| `registry_artifact/index.py`, `ledger/ledger.py` | model/storage | CRUD / event-driven | Artifact registry and append-only ledger are new primitives (CONTRACT §7); no v1 equivalent |

## Metadata

**Analog search scope:** `v1/lightrag/base.py`, `v1/lightrag/kg/cozo_impl.py`,
`v1/lightrag/kg/faiss_impl.py`, `v1/lightrag/kg/factory.py`, `v1/lightrag/kg/shared_storage.py`,
`v1/lightrag/namespace.py`
**Files scanned:** 6 (all explicitly named in CONTEXT.md's canonical_refs / code_context sections)
**Pattern extraction date:** 2026-08-30

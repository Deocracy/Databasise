---
phase: 16-gui-connectors
lane: C
reviewed: 2026-10-22T00:00:00Z
depth: deep
diff_base: d608162
files_reviewed: 6
files_reviewed_list:
  - databasise/stores/vector.py
  - databasise/stores/probes.py
  - databasise/stores/graph.py
  - databasise/parts_core/__init__.py
  - docs/gui/refusals.json
  - databasise/tests/fixtures/selector-resolution.json
findings:
  critical: 1
  warning: 2
  info: 5
  total: 8
status: issues_found
---

# Phase 16: Code Review Report (Lane C)

**Reviewed:** 2026-10-22
**Depth:** deep (callers traced into databasise/seam/engine.py `chunk_page`, `graph_nodes`, `graph_node`, `info`)
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Lane C covers the store-level read helpers for the operator graph and chunk browsers (`graph_node_page`, `graph_node_edges`, `FaissVectorStore.list_ids`, `held_graph_paths`), the `_ENGINE_ONLY` addition, and the two generated catalogue files.

What was checked:

- **Cozo scripts.** Each claim was run against pycozo 0.7.6 in the project venv, using scratch stores under the session scratchpad.
- **Generated files.** Both were checked against an independent re-derivation from the live code, not only through their sync tests.

Verified as correct:

- Self-loops count once, both in the page degree and in the node degree.
- `next_offset` has no off-by-one error.
- An offset past 2^63 returns an empty page, not a fault.
- Client release happens in `finally` on every path, including the early `return` in `graph_node_edges`.
- The busy path maps to 409 and the not-a-database path maps to 502.
- Edges are projected to `{src, tgt, edge_types, weight}`, so `description` stays behind the seam.
- `list_ids` creates no directory.

`docs/gui/refusals.json` matches the code:

- The live tree has 51 `SeamRefusalError` subclasses and the catalogue has 51 entries, with the same names and modules.
- Every `http_status` agrees with `rest._status_for`.
- `attribute_keys` equal the public `vars()` keys. The four constructor parameters that are missing are stored with a leading underscore, as intended.

`selector-resolution.json` matches the code: all 23 non-alias rows reproduce exactly through `resolve_selector(default_registry())`, with the same wiring, node count and outcome.

The main defect is a Cozo 0.7.6 key-prefix pushdown bug. It drops the node whose id equals the prefix. The existing phase tests pass (7 passed, `-k "graph_node or graph_nodes or chunk_page or graph_busy or list_ids"`), so this case is untested.

## Critical Issues

### CR-01: The prefix filter drops the node whose id equals the prefix (Cozo key-range pushdown bug)

**File:** `databasise/stores/probes.py:154` and `databasise/stores/probes.py:159`

**Issue:** In Cozo 0.7.6, `starts_with(id, $p)` on the key column `id` of `*nodes{id}` is turned into a key-range scan whose lower bound is exclusive. As a result, the key equal to the prefix is never returned. Measured in the project venv:

- With nodes `a, ab, b`, the prefix `"a"` returns only `ab`.
- With nodes `Al, Alice, Alice Smith`, the prefix `"Al"` returns `Alice, Alice Smith` (no `Al`), and the prefix `"Alice"` returns only `Alice Smith`.
- Through the real function, `graph_node_page(d, "a", 50, 0)` on a graph with nodes `a, b, c, d` returned `([], 0)`.

Failure scenario: the operator types an entity's full id into the GET /graph/nodes prefix box. The page reports `total: 0` and no rows, even though `GET /graph/nodes/{id}` for the same id returns the node. The page rows and `total` are wrong for any prefix that is itself a node id. The empty prefix is not affected, because every key is greater than `""`.

**Fix:** Bind the id to a variable before the filter, so Cozo cannot push the prefix into the key scan (verified to return `a, ab` for `"a"` and `Al` for `"Al"`). Add a regression test with an exact-id prefix, and record the bug next to #244 in the frozen-bug list in the graph.py docstring and in `test_graph_frozen_bugs.py`.

```python
"?[id] := *nodes{id}, x = id, starts_with(x, $p) :order id :limit $l :offset $o"
...
"?[id] := *nodes{id}, x = id, starts_with(x, $p)"
```

## Warnings

### WR-01: Every graph read opens RocksDB read-write and adds files to `graph.cozo/data/` without limit

**File:** `databasise/stores/probes.py:148`, `databasise/stores/probes.py:190`

**Issue:** `graph_node_page` and `graph_node_edges` copy `probe_graph`: they open a full `CozoClient("rocksdb", ...)` whenever no in-process holder exists. Each open rotates RocksDB's own files:

- One `graph_node_page` call created `000083.log`, `MANIFEST-000084`, two `OPTIONS-*` files and a `LOG.old.<ts>`.
- Ten consecutive calls raised the file count in `data/` from 8 to 29, including 10 new `LOG.old.*` files. RocksDB's `keep_log_file_num` default is 1000.

A GUI that polls the graph browser or node view therefore writes to the store on every refresh, and leaves up to roughly 1000 log files in each graph namespace. Each open also takes the RocksDB process lock for the length of the read. During a GUI read, a second Databasise process or the CLI on the same `store_root` gets `GraphStoreBusyError`.

Phase 10 accepted this for the one-shot health probe. The operator browser makes it a per-request cost, which conflicts with the phase's rule that a read path creates no file.

**Fix:** At minimum, record the accepted cost where it happens:

```python
# shortcut: pycozo 0.7.6 has no read-only open; each read rotates RocksDB LOG/MANIFEST under data/, revisit if the GUI polls
```

A real fix has two steps:

- Have the engine keep one registry reference for the life of the operator server, so reads share a held client and do not reopen it.
- Or pass RocksDB options through pycozo, if it allows that, to set `keep_log_file_num` low.

Either way, list `data/` churn as a documented exception in the D-15 read-path statement.

### WR-02: Health reports a graph as ok while the graph browser reports it as corrupted (marker present, no relations)

**File:** `databasise/stores/probes.py:150-163`, `databasise/stores/probes.py:192-193`

**Issue:** The marker check proves only that a RocksDB database exists. It does not prove the `nodes` and `edges` relations exist. `CozoGraphStore.__init__` opens the client and then runs `_ensure_relations` as a separate step. A crash between the two leaves a valid database with no relations. Reproduced by opening and closing a raw `Client("rocksdb", ...)`:

- `probe_graph` returns `"ok"`, because `::relations` succeeds.
- Both `graph_node_page` and `graph_node_edges` raise `pycozo.client.QueryException: Cannot find requested stored relation 'nodes'`. `_is_store_error` classifies that as a store error, so the engine maps it to the 502 `StoreCorrupted` fault.

GET /health and the graph browser then disagree about the same store. The next ingest would repair it by creating the relations, so the store was never corrupted.

**Fix:** Treat a missing relation as an empty graph, without creating anything. Run `::relations` immutably once, inside the same acquire:

```python
names = {r[0] for r in _run_immutable(shared.client, "::relations", {})}
if "nodes" not in names:
    return [], 0          # graph_node_page; graph_node_edges returns (False, 0, [])
```

## Info

### IN-01: `refusals.json` omits the dynamic `trace_token` key and the 503 status

**File:** `docs/gui/refusals.json` (whole file)

**Issue:** `attribute_keys` lists the attributes set in `__init__` only. The engine also adds a public `trace_token` to a query refusal raised after dispatch (refusals.py:31-34, 848, 924, 985), and `refusal_body` emits it. `ForeignEngineRefusalError` is recorded only as 502, but `_status_for` returns 503 for `_ENGINE_UNAVAILABLE` failure classes (rest.py:154). API-INVENTORY.md:779 documents the 503 case. The file itself does not, so a mockup that reads only the JSON will show the wrong banner for both cases.

**Fix:** Add an optional `"conditional_keys": ["trace_token"]` (or a top-level note), and `"http_status_alt": {"503": [...failure classes]}` on `ForeignEngineRefusalError`.

### IN-02: Separate queries in the page and node reads can disagree under a concurrent in-process flush

**File:** `databasise/stores/probes.py:150-163`, `databasise/stores/probes.py:192-201`

**Issue:** The ids, `total` and degree queries (and in `graph_node_edges`, the `degree` and edge-page queries) are separate `run` calls on a shared client. A `CozoGraphStore` flush in the same process, on the same client, can commit between them. `total` or `degree` can then disagree with the returned rows, so `next_offset` may point one page too far or stop one page early. The window is narrow and the effect is cosmetic.

**Fix:** Accept it with a one-line comment, or derive `degree` from the same query as the page in `graph_node_edges`.

### IN-03: `list_ids` ignores the snapshot the constructor already loaded

**File:** `databasise/stores/vector.py:293-299`

**Issue:** `FaissVectorStore.__init__` already calls `load_committed` through `_read_committed`, which sets `self._entries`. `list_ids` calls `load_committed` again. That costs two `stat` calls on a cache hit, and on a miss it reads the full index and checksum a second time. The method is also not on `VectorNamespaceRouter`, so it only works on a selected namespace store (which is how `engine.chunk_page` uses it).

**Fix:** `ids = sorted(self._entries)`

### IN-04: `list_ids` is classed as engine-only under a "commit, abort and teardown" comment

**File:** `databasise/parts_core/__init__.py:91-101`

**Issue:** `list_ids` is a pure read. It was added to `_ENGINE_ONLY` (commit 016e0f1) so the store-proxy drift guard passes. Now a part's write-mode vector handle refuses it with "store method 'list_ids' is engine-only", and the comment on the set no longer describes what is in it. This is harmless today, but anyone reading the proxy later will misread the set.

**Fix:** Change the comment above the set to "lifecycle methods and engine-only reads", or keep a separate `_ENGINE_READS` set that the proxy checks the same way.

### IN-05: `held_graph_paths` returns absolute store paths where only a boolean is needed

**File:** `databasise/stores/graph.py:176-180`

**Issue:** The only caller (`engine.info`, engine.py:2129) wraps the result in `bool(...)`. Returning resolved `<store_root>/...` paths from a public helper invites a later caller to put them into an operator response, which would leak `store_root` (one of the phase's leak rules). Also, `graph_busy` includes the operator's own short-lived reads and health probes, so it flickers true during GUI refreshes. That matches the documented "in use in this process" meaning, but it is worth stating in the console label.

**Fix:** `def graph_held_under(prefix: str) -> bool: return any(k.startswith(prefix) for k in list(_ClientRegistry._entries))`

---

_Reviewed: 2026-10-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_

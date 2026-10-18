---
phase: 10-stores-locking-data-integrity
plan: 07
subsystem: stores-and-seam-engine
tags: [health, read-only-probe, d-14, q3, stor-04, healthreport]
status: complete

requires: ["10-06"]
provides:
  - "databasise/stores/probes.py: probe_kv, probe_graph, probe_vector (each returns ok/absent/corrupted/busy, creates nothing, never raises); ProbeState literal"
  - "databasise/seam/engine.py: _HEALTH_PROBES (ten (kind, namespace) pairs), _PROBES dispatch; health() constructs no store and runs all probes in one asyncio.to_thread call"
  - "databasise/seam/corpus.py: HealthReport.stores is dict[str, Literal['ok', 'absent', 'corrupted', 'busy']] keyed '<kind>:<namespace>'"
  - "databasise/tests/seam/test_health_probe.py (new, 9 cases: 6 STOR-04 behaviours, 2 drift tests, 1 REST shape)"
affects: [LRAG-13, LRAG-14, HIPP-15, GUI phases 16-18]

actuals:
  tokens: 6839
  tasks: 2
  commits: 2
plan_head_before: 4ccabaca2c519d626e809caab3560b240ec7d1c4
plan_head_after: 782134d8aac08cd0a9508d2e7fcc808d792e7f5d

tech-stack:
  added: []
  patterns:
    - "Read-only store probe: existence check first, then sqlite ?mode=ro (immutable=1 when no -wal file), the shared Cozo client with an immutable ::relations read, or load_committed for the Faiss pair"

key-files:
  created:
    - databasise/stores/probes.py
    - databasise/tests/seam/test_health_probe.py
  modified:
    - databasise/seam/corpus.py
    - databasise/seam/engine.py
    - databasise/tests/seam/test_corpus_status.py
    - databasise/tests/stores/test_graph_lock.py
    - docs/gui/API-INVENTORY.md

key-decisions:
  - "probe_kv picks ?mode=ro only when kv.sqlite3-wal already exists (a writer is open) and ?mode=ro&immutable=1 otherwise, so the probe never leaves -wal/-shm sidecars"
  - "Every probe failure other than a lock maps to corrupted; probes catch Exception broadly because a health check must never raise"
  - "The status note at API-INVENTORY.md line 75, and the What it does, Refusals and GUI display lines of section 3.4.1, were updated with the stores bullet and Live check, because they described the removed constructor behaviour; no other section was edited"

requirements-completed: [STOR-04]

duration: 20min
completed: 2026-10-17
---

# Phase 10 Plan 07: Read-only health probe Summary

`GET /health` now probes all ten shipped LightRAG and HippoRAG namespaces without constructing a store or creating a file. It reports each one as `"<kind>:<namespace>": ok | absent | corrupted | busy` (D-14, Q3), so a fresh install is all `absent` and `degraded`.

## What was built

- `databasise/stores/probes.py`: three probe functions.
  - `probe_kv` checks that `kv.sqlite3` exists, then runs `SELECT 1 FROM kv LIMIT 1` with `timeout=0.1`. A `locked` error gives `busy`; any other error gives `corrupted`.
  - `probe_graph` checks that `graph.cozo` exists, then calls `_ClientRegistry.acquire`. `GraphStoreBusyError` gives `busy`. It then runs `client.run("::relations", {}, True)` and always releases. It never calls `_ensure_relations`.
  - `probe_vector` returns `absent` when `load_committed` returns `None`, `ok` for a snapshot, and `corrupted` for any exception, including `VectorStoreCorruptedError`.
- `engine._HEALTH_PROBES` holds the static list: kv:text_chunks, graph:chunk_entity_relation, vector:chunks/entities/relationships, kv:hipporag-text-chunks, graph:hipporag-graph, vector:hipporag-chunks/entities/facts.
- `health()` builds `stores` in one worker thread. `status` is `ok` only when every store is `ok` and every engine field is true. The `engine` and `clients` blocks are unchanged.
- REST `GET /health` and MCP `status` (scope `health`) return the model unchanged, so both carry the new map. No route or tool code changed.

## TDD evidence

**RED (Task 1, before any source change):** `pytest -q tests/seam/test_health_probe.py` gave `6 failed`. On the fresh-root test, the tree after `health()` had 15 extra paths under `health-probe/`, starting with `health-probe/chunk_entity_relation/graph.cozo/data` and `text_chunks/kv.sqlite3`. The other five tests failed with `KeyError: 'graph:chunk_entity_relation'` and similar, because the old report used the keys `kv`/`vector`/`graph` with value `True`.

**GREEN:** `pytest -q tests/seam/test_health_probe.py tests/seam/test_corpus_status.py tests/stores/test_graph_lock.py` gave `24 passed`. Then `pytest -q tests/seam tests/mcp tests/launcher tests/stores` gave `917 passed, 1 skipped`.

**Task 2 drift test:** it passed on its first run, because Task 1 had already set the list to the shipped values. To check that it can fail, I renamed `hipporag-facts` to `hipporag-fact` in `_HEALTH_PROBES` temporarily. Three tests failed, including `test_the_vector_probes_match_the_part_modules_namespace_constants`. I then restored the file with `git checkout -- seam/engine.py`.

## Verification

- `pytest -q tests/seam/test_health_probe.py`: 9 passed.
- Full gate `python tools/check_offline_suite.py`: exit 0, `1685 passed, 1 skipped, 4 deselected` (both pytest invocations).
- Acceptance greps: `_HEALTH_PROBES` appears 3 times in engine.py, `immutable=1` appears on 2 lines of probes.py instead of the planned 1 (the module docstring's recorded measurement and the URI line; only the URI line is code), and the `Literal["ok", "absent", "corrupted", "busy"]` line appears once in corpus.py. `D-14` appears in section 3.4.1 of API-INVENTORY.md.
- The vector constants are all named `*_NAMESPACE`, as the plan expected: `_CHUNKS_NAMESPACE`, `_ENTITIES_NAMESPACE`, `_RELATIONSHIPS_NAMESPACE`, `_FACTS_NAMESPACE`. No collection by explicit name was needed.

## Deviations from Plan

None to the behaviour. Two scope notes:
- In API-INVENTORY.md section 3.4.1, I also rewrote the "What it does", "Refusals" and GUI "Display" lines, alongside the `stores` bullet and the Live check line. The old text described health constructing stores, `finalize()` raising a 500, and `vector` "not probed", which is now false. All edits are inside 3.4.1 plus the line-75 note.
- Section 1 ("Latency and concurrency", line 41) and docs/gui/CODEBASE-MAP.md still mention `stores.graph: false` and health holding the graph lock. The plan forbids editing other sections, so they are left as they were. A later doc refresh should update them.

## Known Stubs

None.

## Threat Flags

None. The keys carry only namespace names (T-10-23 accepted). The probes use `timeout=0.1` and run off the event loop (T-10-24). The tree-unchanged test covers T-10-22.

## Self-Check: PASSED

- FOUND: databasise/stores/probes.py
- FOUND: databasise/tests/seam/test_health_probe.py
- FOUND: c64ac1a, 782134d (both ancestors of HEAD)

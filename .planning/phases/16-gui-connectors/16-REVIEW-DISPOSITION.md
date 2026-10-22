---
phase: 16
review: 16-REVIEW-A.md, 16-REVIEW-B.md, 16-REVIEW-C.md, 16-REVIEW-ITER2.md
open_critical: 0
open_warning: 0
recorded: 2026-10-22T00:00:00Z
---

# Phase 16: Code Review Disposition

## Lanes and iterations

The review ran in three parallel lanes at deep depth over d608162..HEAD:
- Lane A: the operator REST module, rest.py, the launcher, COVERAGE.md and the GUI docs.
- Lane B: the engine operator methods and the promote extraction, the trace store, the ledger and refusals.
- Lane C: the vector, probe and graph stores, plus the two generated files.

The lanes found 1 critical, 11 warning and 18 info findings. Three lane-A findings duplicated lane-B ones:
- A-WR-01 = B-WR-03;
- A-WR-02 = B-WR-04;
- A-IN-01 = B-WR-05.

The fix rounds:
1. Iteration 1 fixed every critical and warning finding except C-WR-01. That fix broke the protected CONN-11 test.
2. The owner granted that edit at ledger v839, and C-WR-01 landed in 587feda.
3. 16-REVIEW-ITER2 re-reviewed iteration 1's fixes and found 1 warning plus 4 info. Iteration 2 fixed the warning.

No critical or warning finding is open. 16-REVIEW-FIX.md records each fix with its commit and its covering test.

## Findings

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| C-CR-01 | critical | fixed | b85c7ed. The prefix filter is written `x = id, starts_with(x, $p)`, so a prefix equal to a node id now returns that node. This adds a fifth frozen Cozo bug to the graph.py docstring. |
| C-WR-01 | warning | fixed (owner grant) | 587feda. An operator-mode engine holds one graph client, so graph reads stop rotating RocksDB LOG/WAL files: 40 reads leave graph.cozo/data/ unchanged, where 200 reads before gave 409 files and 8.5 MB. `graph_busy` excludes the engine's own hold. Grant v839 inserted 4 lines into test_console_graph.py, and plants CONN-11/CONN-12 were killed (v840/v841). |
| C-WR-02 | warning | fixed | 12f9dce. A marker with no relations reads as an empty graph, which agrees with probe_graph's "ok". |
| B-WR-01 | warning | fixed | 7ebbf66, refined by 38663d7 (ITER2-WR-01). A read-only ledger handle decides at close whether to checkpoint: it checkpoints only when the -wal is absent or empty. Overlapping reads leave only ledger.db, and a reader never checkpoints a writer's frames. Residual: after a writer's frames reach the WAL, -wal and -shm stay until a writer closes last. |
| B-WR-02 | warning | fixed | 32a247a. Ledger history and the trace list each read one snapshot. graph_node_edges still runs two statements, because pycozo 0.7.6 has no read snapshot; this is documented. |
| B-WR-03 = A-WR-01 | warning | fixed | 48e53ba. A corrupted trace or ledger row answers the StoreCorrupted 502. |
| B-WR-04 = A-WR-02 | warning | fixed | fabe7d9. An unreadable or vanished log answers the StoreFault 502. |
| B-WR-05 | warning | fixed | 83b642c. Log lines are capped at 4096 characters, and the cut happens before redaction. |
| A-WR-03 | warning | fixed | 07a4b7a. A bad `--log-file` is refused in one line before the store lock is taken. |
| A-WR-04 | warning | fixed (residual) | fd55fc1. Only /graph/nodes and /graph/node declare 409. The declared but never-raised 503 stays, because the D-01 OpenAPI line in 16-CONTEXT and the protected CONN-11 corrupted-graph node pin it. The inventory documents this. Recorded as info. |
| ITER2-WR-01 | warning | fixed | 38663d7, with tests in tests/ledger/test_ledger_read_only_close.py. |
| ITER2-IN-01 | info | fixed | 02ec36c. snapshot() docstring wording. |
| ITER2-IN-02..04 | info | open | IN-02 is removed by 38663d7. IN-03 is the 503 declaration (owner amendment of the D-01 OpenAPI line). IN-04: list_page's BEGIN/rollback is safe only while it shares persist()'s thread, so do not move list_traces to a worker thread. |
| A-IN-02..06, B-IN-01..07, C-IN-01..05 | info | open | Advisory: a --log-file file is unredacted on disk with default permissions; `_write_in_flight` briefly takes the gates guard; /traces sorts on the event loop; stale counts in API-INVENTORY rows 713/741/842; the COVERAGE D-02 bullet does not mention the debug=true precedent; graph_busy also counts /health's reads; next_offset is copied five times; the log redaction misses some key shapes; refusals.json has no trace_token or 503 entries; list_ids reloads the snapshot; held_graph_paths returns absolute paths. |

Dispositions used: `open` (recorded, not yet triaged), `fixed`, `fixed (residual)`, `fixed (owner grant)`.

## Recorded limits

- The manual check that a real 500 traceback reaches the `--log-file` file has not been run. The tests cover only the shape of the logging config.
- `graph_busy` sees in-process holders only (D-17).
- Preview's `next_version` can go stale under a concurrent write.

---
phase: 16
---

# Phase 16: Review Fix Report

## Lane C

Source: `16-REVIEW-C.md`. Fixed in the main checkout (no worktree). Tests ran in the main checkout.

| Finding | Status | Commit | Covering test | Reason / note |
|---------|--------|--------|---------------|---------------|
| CR-01 | fixed | b85c7ed | `databasise/tests/stores/test_graph_read_review_c.py::test_prefix_equal_to_a_node_id_returns_that_node` | Both prefix queries in `graph_node_page` now bind `x = id` before `starts_with(x, $p)`. The bug is listed in the graph.py frozen-bug docstring. The test uses exact ids `a`, `Al` and `Alice Smith` as prefixes. It failed before the fix (`[('ab', 0)]` for `"a"`). `test_graph_frozen_bugs.py` was not edited because it may be protected; the regression lives in the new file. |
| WR-01 | not-fixed | none | none | pycozo 0.7.6 has no read-only RocksDB open. `Client(engine, path, options)` passes `options` to `CozoDbPy`, but only the `http` engine reads them. The one tuning route is a RocksDB OPTIONS file named `options` inside `graph.cozo/` (the native library logs "RockDB storage engine will use options file"). Using it means writing a store file and replacing the builder options Cozo sets (prefix extractor, bloom filter). That is a design change, not a fix. Measured on a one-node graph with `graph_node_page`: each read adds 2 files to `graph.cozo/data/` (one `LOG.old.*`, one WAL `*.log`) and about 42 KB. Results: 8 files / 47 KB after seed, 29 / 350 KB after 10 reads, 109 / 1.7 MB after 50, 409 / 8.5 MB after 200. `LOG.old` is capped by `keep_log_file_num` (default 1000). The WAL `*.log` files were not deleted at any count measured. The engine-held client option the reviewer named (one registry reference for the operator server's life) remains the real fix. D-15's read-path statement should list `data/` churn as an exception. |
| WR-02 | fixed | 12f9dce | `databasise/tests/stores/test_graph_read_review_c.py::test_marker_without_relations_reads_as_an_empty_graph` | New `_has_graph_relations` runs `::relations` immutably inside the same acquire. When `nodes`/`edges` are missing, `graph_node_page` returns `([], 0)` and `graph_node_edges` returns `(False, 0, [])`. It creates nothing, and the test asserts that no relation exists afterwards. `probe_graph` stays `ok`, so health and the browser agree, and there is no 502. The test failed before the fix with `QueryException`. |

Tests: `databasise/tests/stores/` and `databasise/tests/seam/` gave 1336 passed (after WR-02). `databasise/tests/stores/` plus `test_docstring_currency.py` gave 188 passed (after CR-01). No protected test failed.

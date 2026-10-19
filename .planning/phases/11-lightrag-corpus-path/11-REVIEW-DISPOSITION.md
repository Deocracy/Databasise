---
phase: 11
review: 11-REVIEW.md
titles: json
open: 11
total: 26
recorded: 2026-10-18T00:00:00Z
---

# Phase 11: Code Review Disposition

The review was split into two parts: A (write path) and B (query path and v1 fidelity). The two part reports were merged into 11-REVIEW.md. The review ran three iterations: the iteration-2 and iteration-3 re-reviews returned structured findings and wrote no file. 11-REVIEW-FIX.md records every fix.

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| A-CR-01 | critical | fixed | 937c640, regression fixes 0ee22ce, 3571afd |
| A-CR-02 | critical | fixed | 86da892, heal follow-up e580f41 |
| A-WR-01 | warning | fixed | e06bd0b |
| A-WR-02 | warning | fixed | 347316f |
| A-WR-03 | warning | fixed | 91ffcc2 |
| A-WR-04 | warning | fixed | d1daff2 |
| A-WR-05 | warning | fixed (partial, accepted) | 0cee44e. In-process HippoRAG provider errors stay unredacted, because the protected test_foreign_engine_refusal.py pins the raw exception on the log record. |
| B-CR-01 | critical | fixed | 7e1ebad |
| B-CR-02 | critical | fixed | c42dc38 |
| B-WR-01 | warning | fixed | d843ed0 |
| B-WR-02 | warning | fixed | 9f7acb9, 9a63474 |
| B-WR-03 | warning | fixed | 8e651ef, 987a292 |
| B-WR-04 | warning | fixed | e2c43a5 |
| B-WR-05 | warning | fixed | 780b9b6 |
| B-WR-06 | warning | deferred | 2b7f609 adds a `shortcut:` marker. chunk_top_k stays at 10 (v1: 20), because changing it would change the parity evidence. |
| A2-WR-01 | warning | fixed | 0ee22ce |
| A2-WR-02 | warning | fixed | ca230ac |
| A3-WR-01 | warning | fixed | e580f41. Requires human verification: a re-ingest of a held id now runs one full-corpus mirror. |
| A3-WR-02 | warning | fixed | 3571afd |
| A3-WR-03 | warning | fixed | dc5eea9 |
| B3-WR-01 | warning | fixed | 72e9c3b |
| A-IN-01..05, B-IN-01..06 | info | open | Recorded and advisory. These include the stale "six listed edits" comment in parity/run_arm.py and the retry of a raw upload still in `parsing` state, which is unproven with the stub server. |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.

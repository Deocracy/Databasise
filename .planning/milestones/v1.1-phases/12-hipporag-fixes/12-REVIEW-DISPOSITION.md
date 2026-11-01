---
phase: 12
review: 12-REVIEW.md
titles: json
open: 15
total: 26
recorded: 2026-10-19T00:00:00Z
---

# Phase 12: Code Review Disposition

The review was split into two lanes, run in parallel at deep depth: A covered the HippoRAG parts and wirings, and B covered the seam, stores, runner, foreign and MCP code. The two lane reports (12-REVIEW-A.md and 12-REVIEW-B.md) were merged into 12-REVIEW.md, and it ran three `--auto` iterations. Iteration 3 left 0 critical, 0 warning and 15 info findings. 12-REVIEW-FIX.md records each fix.

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| A-CR-01 | critical | fixed | 26ca959. Requires human verification: an orphan's synonymy edges are restored by synonymy-edges. |
| B-CR-01 | critical | fixed | f4ef3ba |
| A-WR-01 | warning | fixed | 27dd16d |
| A-WR-02 | warning | fixed | 27dd16d. Requires human verification: empty PPR falls back to the dpr-fallback items. |
| A-WR-03 | warning | fixed | 25ea962 |
| A-WR-04 | warning | fixed | e869d26 (`declared_capability` removed; allowlist test of read keys) |
| B-WR-01 | warning | fixed | 76441a9 |
| B-WR-02 | warning | fixed | 76441a9 |
| B-WR-03 | warning | fixed | 0d42188. Requires human verification: a pre-Phase-12 13-node trace matches, and an unknown shape gets a 404. |
| B-WR-04 | warning | fixed (partial) | edd4883 adds strict replacement tests in new files. The lax assertions in protected test_hipporag_write_path.py:310-316 and :394-399, and in test_hipporag_query_path.py:230-240, remain. Tightening them needs an owner grant-check-edit (B-IN-08). |
| A-WR-05 (iteration 2) | warning | fixed | e85c3fc (the per-query guard `empty_ppr_dpr_stand_in` on assemble-result; under D-21 the run reads `degraded`) |
| IN-06 (iteration 2) | info | fixed | f69256e |
| B-IN-07 (iteration 2) | info | fixed | f886e2c |
| IN-01..05, IN-07..09, B-IN-01..06, B-IN-08 | info | open | Advisory. IN-08 and IN-09 are port-record wording items. IN-07 records D-08's higher refusal rate with real providers. B-IN-08 is the owner-grant item above. |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.

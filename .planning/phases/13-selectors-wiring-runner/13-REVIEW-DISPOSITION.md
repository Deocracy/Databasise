---
phase: 13
review: 13-REVIEW.md
titles: json
open: 20
total: 31
recorded: 2026-10-20T00:00:00Z
---

# Phase 13: Code Review Disposition

The review ran in two lanes in parallel, both at deep depth:
- Lane A covered seam, identity, evidence and the API inventory.
- Lane B covered runner, validator, parts and wirings.

The two lane reports, 13-REVIEW-A.md and 13-REVIEW-B.md, were merged into 13-REVIEW.md, which has 0 critical, 8 warning and 14 info findings. Fix iteration 1 fixed all 8 warnings. A re-review of those fix commits, 13-REVIEW-ITER2.md, found 3 warnings where fixes were incomplete, plus 6 new info findings. Fix iteration 2 fixed those 3 warnings. No warning or critical finding is still open. 13-REVIEW-FIX.md records each fix.

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| A-WR-01 | warning | fixed | 84a538b. The public `component` is `mutates_store`, and the part name stays private. The unprotected test_mutable_store_exclusion.py had its assertions updated: its own name pins are gone and nothing else changed (checked in iteration 2). |
| A-WR-02 | warning | fixed | d421d06 and 8427350 (WR-02 in iteration 2): a malformed `items` value, item or `score` is MalformedDriverOutput (502) and carries `trace_token`. A string score is refused, not coerced. |
| A-WR-03 | warning | fixed | 7651a34. Any collection failure is EnvironmentDigestError, which maps to the 503 (D-22). |
| A-WR-04 | warning | fixed | 4c8394f, f31fbca (WR-03 in iteration 2), and 2096270 for the HippoRAG `qa` answer and the 14-node count. The pre-Phase-13 live checks were not re-run live. |
| B-WR-01 | warning | fixed | dbb34bf (parse_wiring) and cb93354 (WR-01 in iteration 2, `without_recipe_only_nodes` on the engine query path). |
| B-WR-02 | warning | fixed | 133272d. A malformed guard declaration is the named 422 InvalidGuardDeclarationError. |
| B-WR-03 | warning | fixed | 8067e25. A failed node keeps the spend already metered. Requires human verification: a failed node that reports `counted_by: "unbudgetable"` now refuses the query with UnbudgetableParticipantError (Phase 4 D-08, RUN-02). Iteration 2 judged this consistent. |
| B-WR-04 | warning | fixed | 888f972. On the query path, a guard signal missing at run time is a 422 that carries `trace_token`. Ingest and delete keep the 502 ForeignEngineRefusalError so staged writes are dropped. That is still a refusal and never a fire (D-19). No shipped corpus wiring declares a guard. |
| A-IN-01..08, B-IN-01..06 | info | open | Advisory: dead code, docstring and schema wording, the retry operation label, the orphan job row on a pre-dispatch ingest refusal, cancelled-node causes, `concurrency_setting` echo, the base wiring identity, non-boolean signals, and KG `score: null`. |
| IN-01..06 (iteration 2) | info | open | Advisory: the inventory does not record the ingest/delete 502 for a missing signal, refusal wording, the `spent` schema description and deviation D7, IN-04 (a body that raises after an unbudgetable call still reads `none`), a falsy `config.guards` accepted silently, and stale comments. |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.

---
phase: 14
review: 14-REVIEW.md
titles: json
open: 21
total: 27
recorded: 2026-10-21T00:00:00Z
---

# Phase 14: Code Review Disposition

The review ran in two parallel lanes at deep depth:
- Lane A covered the engine, promotion, refusals, REST, MCP and the API inventory.
- Lane B covered the ledger, selectors, wiring resolution, registry, falsifier2 and F-07.

The two lanes were merged into 14-REVIEW.md: 0 critical, 4 warning and 14 info findings. Fix iteration 1 fixed all 4 warnings. A re-review of those fix commits (14-REVIEW-ITER2.md) found 2 warnings and 7 info findings. Fix iteration 2 fixed both warnings. No critical or warning finding is open. 14-REVIEW-FIX.md records each fix.

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| A-WR-01 | warning | fixed | 75f9d59 and 6ab36cd (WR-02 in iteration 2). The alias read opens the ledger with `PRAGMA query_only = ON`, and the close checkpoint is disabled (`SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE`). A missing, zero-byte or tableless file refuses by name. The writer migration creates the unique index first and keeps the old one if duplicates block it, instead of raising a raw IntegrityError. **This narrows D-08 for the read path:** an old file is migrated by the next promote, rollback or retire, never by a consumer query. The plain-path open is kept, not the `mode=ro` URI, because the protected LEDG-06 lifecycle test identifies ledger connections by path. Hot-journal recovery, and a Python without the constant, can still write the file; both are documented. |
| A-WR-02 | warning | fixed | 49b2ee9. Promote repairs an alias whose active row names a wiring that no longer resolves, by minting a MAJOR bump from the row's version. Rollback and retire still refuse by name. Requires human verification: a repaired alias is always MAJOR-bumped, even when the lost wiring had the same surface. |
| A-WR-03 | warning | fixed | ccd4fdb (API-INVENTORY lines 246, 352, 570, 678, and nearby sentences) |
| B-WR-01 | warning | fixed | a1420be. The Falsifier-2 evidence names `probe_registry()`; FALSIFIER-2-EVIDENCE.md was regenerated, with prose lines only changed. |
| WR-01 (iteration 2) | warning | fixed | de86d65 (`lineage` is `ORDER BY id DESC LIMIT 1`, so a duplicates file follows the active row) |
| WR-02 (iteration 2) | warning | fixed | 6ab36cd (no checkpoint on close for the read handle) |
| A-IN-01..06, B-IN-01..08 | info | open | Advisory: `zip` without `strict=True` in `refuse_partial_evidence`; the "promotion evidence" wording on rollback and retire; truthiness for the engine-level trace flag; stale verb docstrings; an unreachable fallback message naming node ids; stale inventory citations; history rows carrying internal hashes before the Phase 16 routes; leftover "known arms" and "registered parts" texts; stale counts in CODEBASE-MAP. |
| IN-01..07 (iteration 2) | info | open | Advisory: a garbage-bytes or old-shape ledger.db still raises a raw sqlite error (pre-existing); a dead generation cannot be tombstoned while rollback and retire refuse; the API-INVENTORY 678-680 live-check sequence; `_REGISTRY_TEXT` hard-codes part names; duplicates files log on every writer open; test gaps; lint (I001). |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.

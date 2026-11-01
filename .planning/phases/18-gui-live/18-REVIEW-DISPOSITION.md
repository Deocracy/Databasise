---
phase: 18
review: 18-REVIEW.md
disposed: 2026-10-31
fixed: 8
open: 7
---

# Phase 18 review disposition

Fixes were applied by gsd-code-fixer on 2026-10-31 (eight commits, `phase/18` trailer); the live suite
`databasise/tests/gui_live/` passed 140/140 afterwards and `mockups/operator-console.html` kept the
owner-approved digest (bf98e79e…4d20).

| ID | Severity | Disposition | Commit / note |
|----|----------|-------------|---------------|
| R18-01 | warning | fixed | a490b489 — Compare.hideStates() hides the Run spinner; test extended in test_live_02 |
| R18-02 | warning | fixed | bc67406e — history entries store `partial`/`degraded`; Ledger partial-run blocker now fires; test added in test_live_07 |
| R18-03 | warning | fixed | 62d5460c — `Object.create(null)` for `retrying`, `arms`, `caps`, `aliases`; test added in test_live_06 |
| R18-04 | warning | fixed (owner glance requested) | a957b3d5 — shared `isEnvelope()`; malformed 2xx shows the generic banner and leaves `running` on query, stream-final and compare paths; test covers the plain POST path only |
| R18-05 | warning | open — owner decision | `family()` assumes LightRAG for alias selectors because the alias arm is not in the picker data; needs a product rule (fetch the arm via the alias catalogue, or word the Delete dialog arm-neutrally for aliases) |
| R18-06 | warning | fixed | 2174af2f — Graph clears previous node/chunk lists before a new selector read; test added in test_live_08 |
| R18-07 | info | open — advisory | streamed query leaves InFlight at headers; harmless with Run disabled during writes (D-13) |
| R18-08 | info | fixed | 055ca845 — loadHealth dedupes while a load is pending |
| R18-09 | info | fixed | 9acbbb81 — Evidence cache cleared on `corpus-changed` |
| R18-10 | info | open — advisory | raw selector JSON bypasses picker blockers; server still refuses by name |
| R18-11 | info | fixed | a87f1951 — Picker.attach local renamed; no longer shadows `api` |
| R18-12 | info | open — advisory | build.py path check / non-atomic write; build tool only |
| R18-13 | info | open — advisory | start-up traceback instead of refuse() for a bad console page; packaging-time condition |
| R18-14 | info | open — advisory | full query text in sessionStorage unused; remove in a later tidy |
| R18-15 | info | open — advisory | IN-BLD-03 `<!--` escaping in embedded fixtures; no `<!--` present in the current build |

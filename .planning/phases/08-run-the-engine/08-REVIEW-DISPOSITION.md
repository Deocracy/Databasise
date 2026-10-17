---
phase: 08
review: 08-REVIEW.md
titles: json
findings:
  - id: IN-01
    severity: info
    disposition: open
    title: "MCP transport security accepts any loopback page on any port, while REST uses an exact-origin list (carried forward, unchanged)"
  - id: IN-02
    severity: info
    disposition: open
    title: "Stale-PID race and fd leak in `acquire_store_lock` (carried forward, unchanged)"
  - id: IN-03
    severity: info
    disposition: open
    title: "Launcher refusals reuse parity wording, and the launcher imports the parity package for a default (carried forward, unchanged)"
  - id: IN-04
    severity: info
    disposition: open
    title: "Lint violations in phase-08 files (carried forward; re-confirmed with `.venv/bin/ruff`)"
  - id: IN-05
    severity: info
    disposition: open
    title: "The origin guard matches only literal same-origin forms (carried forward; part (a) of the old IN-05)"
  - id: IN-06
    severity: info
    disposition: open
    title: "`_is_wildcard` raises `UnicodeEncodeError` for an argv host with undecodable bytes"
  - id: IN-07
    severity: info
    disposition: open
    title: "The `run_comparison` per-query catch is untested and repeats a config refusal for every query"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "`math.isfinite` raises `OverflowError` for very large integer scores"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "builder refusals still escape as tracebacks from the other CLIs"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "`--allow-remote-unauthenticated` is unusable for wildcard binds"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Rerank identity and scores are not type-checked"
open: 7
total: 11
recorded: 2026-10-17T02:35:24.537Z
---

# Phase 08: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| WR-01 | warning | fixed | 08-REVIEW-FIX.md (not in the current review) |
| WR-02 | warning | fixed | 08-REVIEW-FIX.md (not in the current review) |
| WR-03 | warning | fixed | 08-REVIEW-FIX.iter2.md (not in the current review) |
| WR-04 | warning | fixed | 08-REVIEW-FIX.iter2.md (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.

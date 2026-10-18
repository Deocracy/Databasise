---
phase: 10
review: 10-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "probe_kv and probe_graph raise PermissionError when the namespace directory is not searchable"
  - id: IN-01
    severity: info
    disposition: open
    title: "Accepted limits (proxy threat model, node ids in stop_reason, RocksDB data/ rotation, store-module classification)"
  - id: IN-02
    severity: info
    disposition: open
    title: "The no-such-table plus -wal leniency can hide a database that lost its kv table; kv busy state unreachable"
  - id: IN-03
    severity: info
    disposition: open
    title: "A directory named kv.sqlite3 is reported absent"
  - id: IN-04
    severity: info
    disposition: open
    title: "The new drift test is weaker than its comment"
  - id: IN-05
    severity: info
    disposition: open
    title: "The finalize loop in the tracer composer stops at the first failing finalize"
  - id: IN-06
    severity: info
    disposition: open
    title: "Carry-overs from iteration 2 (snapshot log text, _committed_signature catches only FileNotFoundError)"
open: 6
total: 7
recorded: 2026-10-17T00:00:00Z
---

# Phase 10: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | da2101d (orchestrator, after iteration 3) |
| IN-01 | info | open | Accepted limits, recorded on purpose |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Finding IDs are reused across the three --auto iterations. Every Critical and Warning from earlier iterations was fixed. The iteration backups (10-REVIEW.iterN.md, 10-REVIEW-FIX.iterN.md) keep each list.

- **Iteration 1:** CR-01 and WR-01 to WR-10, commits fa4dcfe..76c17a1.
  - CR-01: query-path store faults leaked paths.
  - WR-01: registry close race.
  - WR-02: proxy bypass.
  - WR-03: not_allowed delete committed.
  - WR-04: shared .tmp abort.
  - WR-05: snapshot retry.
  - WR-06: shared snapshot dicts.
  - WR-07: health created files.
  - WR-08: corrupt kv/graph gave a 500.
  - WR-09: store leaks.
  - WR-10: vacuous graph staging tests.
- **Iteration 2:** WR-01 to WR-04 plus IN-02 and IN-03, commits ed705b7..1356fb1.
  - WR-01: snapshot reported absent on vanish (also flagged by the automated security review).
  - WR-02: relative store_root.
  - WR-03: health created -shm and manifest.
  - WR-04: proxy threat model documented.
- **Iteration 3:** WR-01, health raised on a mode-000 directory, fixed in da2101d.

Deferred to later phases:
- Node ids in consumer-visible `stop_reason` and `degradation_reason` (Phase 13 WIRE, node-free consumer text).

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.

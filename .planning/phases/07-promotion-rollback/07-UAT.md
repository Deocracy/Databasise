---
status: diagnosed
phase: 07-promotion-rollback
source: [07-VERIFICATION.md]
started: 2026-09-12T06:53:47Z
updated: 2026-09-12T08:23:39Z
---

## Current Test

[testing complete]

## Tests

### 1. Concurrent promote/rollback/retire against the same alias

expected: Either true serialization (one call fully completes before the other starts reading prior state) or a clean refusal for the loser — never two rows minting the same semver, and never `retire()`'s `ActiveGenerationRetirementError` guard passing on a generation that becomes active only after the guard's own read.
result: issue
reported: "Converted from pass after the pre-seal audit reproduced the failure. retire(v) raced
  against rollback(v) — two concurrent calls, exactly this test's stated procedure — accepted a
  rollback committed AFTER the tombstone on that same generation in 134/200 trials, with both
  calls returning ok and no refusal for the loser. The duplicate-semver half of the expectation
  does hold at two-call concurrency (0/300); it surfaces only at six-way concurrency (13/300)."
severity: major

**How to run it:** fire two concurrent calls against the same alias — e.g. `asyncio.gather()` over
two `promote()` calls, or a `promote()` racing a `retire()`; equivalently two REST or MCP
requests hitting the same alias at once.

**Why it is human-verified, not automated:** a genuine concurrency race needs real parallel
dispatch to trigger, and it triggers non-deterministically. Static analysis already establishes the
precondition — there is no `asyncio.Lock` or `threading.Lock` anywhere in `engine.py`
(re-confirmed this run) — but only a live concurrent run shows the actual outcome.

**Provenance:** carried forward from the previous verification as WR-01 (also in `07-REVIEW.md`).
Plan 07-04 did not touch `_promote_sync` / `_rollback_sync` / `_retire_sync`, so this is
pre-existing and was out of that plan's scope — not a regression introduced by the gap closure.

## Summary

total: 1
passed: 0
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-07-1
  truth: "Concurrent promote/rollback/retire against one alias either serializes or cleanly refuses the loser — never two rows minting the same semver, and never a guard passing on state that changes after its own read"
  status: failed
  reason: "Reproduced: retire(v) vs rollback(v) at two-call concurrency accepted a post-tombstone rollback in 134/200 trials, both calls returning ok. Six-way promote concurrency minted duplicate semvers in 13/300 trials."
  severity: major
  test: 1
  root_cause: "Check-then-act across separate autocommit statements on a per-call sqlite3 connection. No transaction spans the guard read and the append, there is no lock anywhere in the package, and the ledger's (alias, minted_version) index is non-UNIQUE — so a concurrent writer can commit between any guard's read and its own append."
  artifacts:
    - path: "databasise/seam/engine.py"
      issue: "_rollback_sync reads generation_state (1321) and refuses a tombstoned target (1325) but appends at 1370 with no transaction spanning the two"
    - path: "databasise/seam/engine.py"
      issue: "_retire_sync's active-generation guard (1461->1463) and append (1493) have the same check-then-act shape"
    - path: "databasise/seam/engine.py"
      issue: "_promote_sync read-mint-append (1197 / 1225 / 1249) is three separate statements, so two racers mint the same semver"
    - path: "databasise/ledger/ledger.py"
      issue: "ix_ledger_generation on (alias, minted_version) is CREATE INDEX, not UNIQUE — nothing at the schema level refuses a duplicate published (alias, version) key"
    - path: "databasise/tests/"
      issue: "no committed concurrency test for promote/rollback/retire — every guard test is strictly sequential"
  missing:
    - "Make read-derive-append atomic for all three operator verbs, so a guard's decision and its append commit together"
    - "Refuse a duplicate published (alias, version) at the schema level rather than relying on the read"
    - "A committed concurrency regression test covering both races, so this cannot silently reopen"
  debug_session: "pre-seal audit (workflow wf_158ddc30-ad3) + independent reproduction; diagnosis established to the line, no separate debug session needed"

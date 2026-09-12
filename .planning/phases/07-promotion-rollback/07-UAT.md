---
status: testing
phase: 07-promotion-rollback
source: [07-VERIFICATION.md]
started: 2026-09-12T06:53:47Z
updated: 2026-09-12T06:53:47Z
---

## Current Test

number: 1
name: Concurrent promote/rollback/retire against the same alias serializes or cleanly refuses
expected: |
  Either true serialization (one call fully completes before the other starts reading prior
  state) or a clean refusal for the loser — never two rows minting the same semver, and never
  `retire()`'s `ActiveGenerationRetirementError` guard passing on a generation that becomes
  active only after the guard's own read.
awaiting: user response

## Tests

### 1. Concurrent promote/rollback/retire against the same alias

expected: Either true serialization (one call fully completes before the other starts reading prior state) or a clean refusal for the loser — never two rows minting the same semver, and never `retire()`'s `ActiveGenerationRetirementError` guard passing on a generation that becomes active only after the guard's own read.
result: [pending]

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
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps

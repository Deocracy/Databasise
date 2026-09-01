---
status: testing
phase: 03-lightrag-query-side
source: [03-VERIFICATION.md]
started: 2026-09-01T22:36:05Z
updated: 2026-09-01T22:36:05Z
---

## Current Test

number: 1
name: Live five-arm parity comparison after rebuilding the v1 environment
expected: |
  Each arm's comparison status flips from `inconclusive` to `completed`, with a real N=5 keyword variance band and real chunk/entity/relation sym_diff numbers recorded, or every excursion outside tolerance recorded individually in DECLARED-DEVIATIONS.md.
awaiting: user response

## Tests

### 1. Live five-arm parity comparison after rebuilding the v1 environment
expected: Rebuild the v1 pinned environment (v1/README-PARITY.md), re-run v1's real ingest to produce v1/.venv, v1/.parity_working_dir, v1/.parity_v2_store, v1/.env.parity, then re-run `databasise.parity.run_comparison` for all five arms and `databasise.evidence.parity_report` to render PARITY-EVIDENCE.md. Each arm's status flips from `inconclusive` to `completed` with a real N=5 keyword variance band and real sym_diff numbers, or every out-of-tolerance excursion is named in DECLARED-DEVIATIONS.md.
result: [pending]

### 2. Human spot-check of answer substance for the two corpus queries
expected: With the v1 environment and imported index present, run q1 and q2 through `databasise.parity.run_comparison --arm hybrid` and through v1 directly, read both answers side by side, and record a match / no-match judgment with notes for each query pair.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

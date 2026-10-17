---
status: testing
phase: 08-run-the-engine
source: [08-VERIFICATION.md]
started: 2026-10-16T20:10:00Z
updated: 2026-10-16T20:10:00Z
---

## Current Test

number: 1
name: Confirm the post-review behaviour changes match intent
expected: |
  Owner agrees with the stricter refusals added after code review: wildcard binds (0.0.0.0, ::, 0, empty)
  refused even with --allow-remote-unauthenticated; state-changing requests carrying a foreign Origin get 403;
  every client-building CLI refuses a bad env file by name instead of a traceback.
awaiting: user response

## Tests

### 1. Post-review behaviour changes match intent (WR-01, WR-02, WR-03, IN-05 b)
expected: Owner agrees these stricter refusals are wanted (08-REVIEW-FIX.md)
result: [pending]

### 2. RUN-11 live measurement and measured threshold
expected: Five -m live runs give the same verdict; _SIMILARITY_THRESHOLD set from the observed minimum with date and model recorded
result: [pending — owner-deferred to .planning/TESTING-PLAN.md §2]

### 3. Parity-env builder compatibility (no spend)
expected: build_clients(load_env_file(v1/.env.parity)) prints ['embedding', 'llm']
result: [pending — owner-deferred to .planning/TESTING-PLAN.md §2]

### 4. Live rerank client (optional, D-10)
expected: Live rerank call against a real cohere/jina/aliyun endpoint returns a ranking in index order
result: [pending — owner-deferred to .planning/TESTING-PLAN.md §2]

### 5. Ledger test_refs (BAK)
expected: RUN-01..RUN-12 carry test_refs from the 08-10-SUMMARY "Owner ledger steps (pending)" lines (RUN-11 after its live runs)
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps

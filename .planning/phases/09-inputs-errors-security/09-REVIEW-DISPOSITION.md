---
phase: 09
review: 09-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "delete_document removes the staged upload when v1 answered not_allowed or fail"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "A corrupt, truncated or empty owner record fails the delete or makes the id undeletable"
  - id: WR-02
    severity: warning
    disposition: deferred
    title: "A crash between the exclusive create and the owner-record write leaves an orphan no delete releases"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "scrub_error_message mangles and leaks non-listed URL schemes"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "Non-Real and huge-int scores from a store take the wrong failure path"
  - id: IN-03
    severity: info
    disposition: open
    title: "DuplicateDocumentIdError is a 422 caller refusal and the OpenAPI document does not declare it"
  - id: IN-04
    severity: info
    disposition: open
    title: "Every node and read-route exception is reported as the foreign engine failed"
  - id: IN-05
    severity: info
    disposition: open
    title: "UnknownDocumentError can never be raised and stays in __all__; stale MalformedSelectorPayloadError docstring"
  - id: IN-06
    severity: info
    disposition: open
    title: "Refusals echo unbounded caller input"
  - id: IN-07
    severity: info
    disposition: open
    title: "Compare envelope-rule text copied in three places; mid-run arm failure leaves earlier traces"
  - id: IN-08
    severity: info
    disposition: open
    title: "Accepted design limits, listed for the record"
open: 6
total: 11
recorded: 2026-10-17T00:00:00Z
---

# Phase 09: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | 09-REVIEW-FIX.md iteration 3 (185e0f1) |
| WR-01 | warning | fixed | 09-REVIEW-FIX.md iteration 3 (dccac1e) |
| WR-02 | warning | deferred | Accepted limit, documented in the `ingest` docstring (8943a8a). A record-first order needs a lock or link-based create. A crash orphan is removed by hand. |
| IN-01 | info | fixed | 21f40ad; scheme bounded in 2da7ad9 |
| IN-02 | info | fixed | 54dabda (OverflowError). String and Decimal scores are left as they are. |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |

Ids are reused across the three --auto iterations. Earlier iterations' Critical and Warning findings were all fixed:

- **Iteration 1:** CR-01 NaN refusal body, WR-01 read-route catch, WR-02 write-path parse, WR-03 error_message leak, WR-04 upload staging. Commits bdecc6c..f357d24.
- **Iteration 2:** CR-01 burned raw-upload id, WR-01 store-minted NaN, WR-02 scrub forms, WR-03 DeletionOutcome scrub, WR-04 cleanup scope. Commits 5bbb776..be65af3.
- **Iteration 3:** handled as recorded above.
- **Post-loop verification:** two regressions, both fixed in 2da7ad9.
  - WR-A: owner-record temp name over NAME_MAX.
  - WR-B: quadratic URL regex.

Each iteration's backups are kept in 09-REVIEW.iterN.md and 09-REVIEW-FIX.iterN.md.

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.

---
phase: 15
review: 15-REVIEW.md
titles: json
open_critical: 0
open_warning: 1
owner_decision: 1
recorded: 2026-10-21T00:00:00Z
---

# Phase 15: Code Review Disposition

The review ran in three parallel lanes at deep depth:
- Lane A covered the offline CLIs, the parity harnesses, `import_index`, `remint`, `corpus_ingest`, the client builder and the v1 corpus adapter.
- Lane B covered the TOOL-12 floor store and two-stage gate, `aa_run`, calibration, the bundle, admission at load and the API inventory.
- Lane C covered the codebase-memory-mcp part and adapter, the MCP server, the evidence renderers, the import-boundary checker, packaging, the README and CODEBASE-MAP.

The lanes were merged into 15-REVIEW.md: 3 critical, 24 warning and 19 info findings. B-WR-05 merged into A-WR-01. There were four fix iterations, each followed by a re-review of its own fix commits:

| Fix iteration | Fixed | Next re-review found |
|---------------|-------|----------------------|
| 1 | every critical and warning finding (26 distinct) | 15-REVIEW-ITER2-A/B/C: 1 critical, 9 warning |
| 2 | all of those except A-ITER2-WR-03, which is owner-gated | 15-REVIEW-ITER3-A/B/C: 5 warning, one of them the same owner-gated residual |
| 3 | the 4 fixable warnings | 15-REVIEW-ITER4: 2 warning |
| 4 | both warnings, committed by the orchestrator | none run |

15-REVIEW-FIX.md records each fix with its commit and covering test.

No critical finding is open. One warning is open, and it waits on an owner decision (below). No protected test was edited in any iteration.

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| A-CR-01 | critical | fixed | a8dae39 (`--limit` below one exits 2) |
| B-CR-01 | critical | fixed | 0869ea4, refined by 7806e4e (ITER2-B-WR-01). The verdict must open the reply. The parser reads the option lines from the committed judge prompt, so each option's own definition is not counted as a second verdict. Requires human verification: it has not been run against a real judge. |
| C-CR-01 | critical | fixed | e808a88. Validator violations in the named wirings fire Falsifier 2's verdict and exit code. Requires human verification. |
| A-WR-01..10 | warning | fixed | 8d68406, 9bc6c3e, 7b3379e, 77e5da3, bca102f, eef7173, d6db78d, e75f04e, 0d0eb19, 79125b5 |
| B-WR-01..04, 06, 08 | warning | fixed | 11eeba8, 9c4f337, 2e0fe3e, 1e1b196, 1a2e13b, d00e8ec |
| B-WR-07 | warning | fixed (narrowed) | c0cb857 and 2d3138b (ITER2-B-WR-03). `open_sealed` refuses a second opening. `remint` refuses a mint that resolves to an opened version. A fresh mint refuses when it would re-seal opened questions. `mint_bundle`'s dedup return still hands back an opened version with its flag set, because the protected TOOL-13 test pins that return. |
| C-WR-01..06 | warning | fixed | 3bf4704, 72cf2c1, 2c3ec8e (WR-03 and WR-04), a5a6662 (WR-05 and WR-06) |
| ITER2-A-WR-01, 02, 04, 05 | warning | fixed | ecdaa5a, b48c2b4, 4fa6bf6, 2d328f9. `import_index` now exits 3 for an inconclusive verification (D-03). |
| ITER2-B-WR-02 | warning | fixed | 13ecfa8. A floors.db fault is `ForeignEngineRefusalError(failure_class="StoreFault")`, so no new refusal class is added (D-13). |
| ITER2-C-CR-01, WR-01 | critical, warning | fixed | 4a57dca, e6e381f |
| ITER3-A-WR-01, B-WR-01, C-WR-01, C-WR-02 | warning | fixed | 057da4a, 5c5a1d6, 17ce530, afdf521 |
| ITER4-WR-01, WR-02 | warning | fixed | ef06e42, 114f1f4. Tests are in `test_review_fix_15_lane_c.py`; both failed before the fix. The committed PARITY-EVIDENCE.md renders byte-identical. |
| **A-ITER2-WR-03** (= ITER3-A-WR-02) | warning | **owner decision** | A HippoRAG workspace refused before eef7173 carries no unverified marker, so the `run_cross_modality` preflight still accepts it. The code fix is for preflight to check all three HippoRAG namespaces. That fix fails the protected TOOL-09 node `test_cross_modality_isolation.py::test_tool09_preflight_leaves_the_store_root_listing_unchanged`, which builds only `hipporag-chunks`. The owner chooses one of: (a) grant an edit so that the test also commits non-empty `hipporag-entities` and `hipporag-facts`, and the check lands; (b) rebuild the existing HippoRAG workspace, which is paid; (c) accept it as a recorded residual. Until then the preflight behaves as it did before Phase 15. |
| A-IN-01..04, B-IN-01..07, C-IN-01..08 | info | open | Advisory. A-IN-01: the cross-modality estimate overstates the LightRAG arm. A-IN-02: `remint` from a wheel pays for the probe call before it finds the bundle root unwritable. A-IN-03: empty pinned keywords unpin the v1 arm. A-IN-04: the result write inside the refusal handler can mask the refusal. B-IN-01: the seam imports the `aa_run` CLI module for two constants. B-IN-02: the stage-2 gate does sync sqlite I/O on the event loop. B-IN-03: the index probe runs after the env file is read. B-IN-04: refusal docstrings describe the pre-TOOL-12 gate. B-IN-05: the executor version is hardcoded. B-IN-06: the condition-10 message is wrong for inferred scopes. B-IN-07: admission skips declaration-only opaque parts that have no record. C-IN-01: the admission evidence cites `index_repository`. C-IN-02: the `functools.cache` builders are not synchronised. C-IN-03: the f07 verdict renders "()" with no part. C-IN-04: import-boundary scan gaps. C-IN-05: the adapter turns interrupts into transport faults. C-IN-06: a stale `mcp` docstring. C-IN-07: the cbm records carry raw engine output. C-IN-08: the provenance check is skipped silently with no `v1/`. |
| ITER2/ITER3/ITER4 IN items | info | open | Advisory, listed in each re-review file. Among them: the `V1IndexLockedError` text for a same-process lock; the seam's `v1-index-sync` not mapping that error to `StoreBusyError`; a stale `<arm>.refused.json` surviving a complete run; `run_arm --arm hipporag` and `storage_audit` not checking the unverified marker; the `DatabaseError` catch also absorbing sqlite programming errors; a malformed `w3` wiring still failing at import time, outside `main()`; and stale docstrings. |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`, `owner decision`.

## Recorded limits (from execution, not review)

- No production part reports `cache_hit`. A real `aa_run --spend` is therefore refused with `UnusableFloorError`. Since B-WR-04 that refusal comes after one question, not after both full passes, so no real floor is persisted yet (15-16).
- The `--spend` paths and the new judge-verdict, Falsifier-2 and v1 status-less fail-handling logic have not been run against real v1 or a real provider. D-24 forbids spend in this phase.

---
phase: 14-promotion-ledger
verified: 2026-10-21T06:01:21Z
status: passed
score: 5/5 roadmap success criteria verified (14/14 LEDG requirements satisfied in code)
covered_files:
  - ".planning/phases/14-promotion-ledger/14-01-PLAN.md"
  - ".planning/phases/14-promotion-ledger/14-01-SUMMARY.md"
  - ".planning/phases/14-promotion-ledger/14-02-PLAN.md"
  - ".planning/phases/14-promotion-ledger/14-02-SUMMARY.md"
  - ".planning/phases/14-promotion-ledger/14-03-PLAN.md"
  - ".planning/phases/14-promotion-ledger/14-03-SUMMARY.md"
  - ".planning/phases/14-promotion-ledger/14-04-PLAN.md"
  - ".planning/phases/14-promotion-ledger/14-04-SUMMARY.md"
  - ".planning/phases/14-promotion-ledger/14-05-PLAN.md"
  - ".planning/phases/14-promotion-ledger/14-05-SUMMARY.md"
  - ".planning/phases/14-promotion-ledger/14-06-PLAN.md"
  - ".planning/phases/14-promotion-ledger/14-06-SUMMARY.md"
  - ".planning/phases/14-promotion-ledger/14-07-PLAN.md"
  - ".planning/phases/14-promotion-ledger/14-07-SUMMARY.md"
  - ".planning/phases/14-promotion-ledger/14-08-PLAN.md"
  - ".planning/phases/14-promotion-ledger/14-08-SUMMARY.md"
  - ".planning/phases/14-promotion-ledger/14-09-PLAN.md"
  - ".planning/phases/14-promotion-ledger/14-09-SUMMARY.md"
  - ".planning/phases/14-promotion-ledger/14-10-PLAN.md"
  - ".planning/phases/14-promotion-ledger/14-10-SUMMARY.md"
  - ".planning/phases/14-promotion-ledger/14-11-PLAN.md"
  - ".planning/phases/14-promotion-ledger/14-11-SUMMARY.md"
  - "databasise/evidence/ADMISSION-CODEBASE-MEMORY-MCP.md"
  - "databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md"
  - "databasise/evidence/FALSIFIER-2-EVIDENCE.md"
  - "databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md"
  - "databasise/evidence/f07_report.py"
  - "databasise/evidence/falsifier2.py"
  - "databasise/ledger/ledger.py"
  - "databasise/mcp/tools.py"
  - "databasise/parts/registry.py"
  - "databasise/parts/schema.py"
  - "databasise/parts_core/declared_only.py"
  - "databasise/pyproject.toml"
  - "databasise/seam/engine.py"
  - "databasise/seam/promotion.py"
  - "databasise/seam/refusals.py"
  - "databasise/seam/rest.py"
  - "databasise/seam/selectors.py"
  - "databasise/tests/fixtures/codebase-memory-mcp.json"
  - "databasise/wirings/resolve.py"
  - "docs/gui/API-INVENTORY.md"
  - "docs/gui/CODEBASE-MAP.md"
covered_digest: "v3:sha256:8d655c3e7d71cca796bd28d6ec6facdb5160382b08e0983aeb162a3962d8264f"
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "An operator can read an alias's full history over REST and MCP (SC4 is met at the engine read, Ledger.history_for_alias)"
    addressed_in: "Phase 16"
    evidence: "CONN-06 GET /ledger/aliases and CONN-07 POST /ledger/history; 14-CONTEXT D-09: engine read only in Phase 14"
human_verification:
  - test: "A-WR-02 repair policy: seed an alias whose active row names a wiring that no longer resolves (for example `retired-arm` 2.0.0 over `naive` 1.0.0), then promote a naive trace"
    expected: "Owner confirms the intended outcome: promote mints 3.0.0 (always a MAJOR bump), the mutation class is derived from the new wiring alone as for a first promotion, `parent` records the vanished name, and rollback and retire on that alias still refuse with UnsatisfiableSelectorError"
    why_human: "Policy choice. No surface record of the vanished wiring exists, so the code takes the conservative reading (a MAJOR bump even when the lost wiring had the same surface). 14-REVIEW-FIX and 14-REVIEW-DISPOSITION flag it for human verification. Code: engine.py:2403-2436; test: test_review14_fixes.py::test_promote_repairs_an_alias_whose_active_row_names_a_retired_arm (passes)."
  - test: "D-08 read-path narrowing: open an alias query against a pre-07-05 ledger.db (old plain index, or duplicate (alias, minted_version) rows)"
    expected: "Owner confirms: the consumer read (`_resolve_alias`) opens with `PRAGMA query_only = ON` and no close checkpoint, never migrates, and leaves the file bytes and indexes unchanged; the file is migrated by the next promote, rollback or retire. The owner also accepts the plain-path open with query_only instead of the `file:...?mode=ro` URI the ruling named"
    why_human: "D-08 as written ran the migrating constructor on every open_existing; the A-WR-01 fix narrowed that to the writer verbs. The URI form failed the protected LEDG-06 check, which counts ledger connections by file path, so changing it needs a grant-check-edit. Residuals documented in ledger.py:163-206: a delete-then-connect race can create an empty file, hot-journal recovery can still write, and a Python without SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE keeps the close checkpoint."
  - test: "SC5 scope: compare ROADMAP SC5 'every registered part is reachable or unregistered' with default_registry().keys()"
    expected: "Owner confirms D-13's scope (admitted parts only). Four registered reference parts are reachable through no selector: parts-core/passthrough@1.0.0, parts-core/fake-retriever@1.0.0, parts-core/fake-llm-caller@1.0.0 and parts-core/fixpoint-body@1.0.0. None carries an admission record. Every part with an admission record (lightrag/full-ingest@0.2.0, full-delete@0.2.0, v1-index-sync@0.1.0) is reached through a corpus wiring"
    why_human: "LEDG-12's text says 'no admitted part', which is met. The ROADMAP SC5 shorthand says 'every registered part', which these four reference parts do not meet literally. 14-CONTEXT D-13 states reference parts are out of selector reach by design, but no owner decision records that the SC wording means the same thing."
---

# Phase 14: Promotion & Ledger Verification Report

**Phase Goal:** The operator verbs never fail with a 500 on any trace, every alias with a generation can be selected and resolves, and an alias's history is readable from the ledger
**Verified:** 2026-10-21T06:01:21Z
**Status:** passed. All five criteria are verified in code and by test. The three owner policy items were resolved on 2026-10-21; see the Human Verification Resolution section at the end.
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Promote, rollback and retire never 500 on any trace: partial or failed traces refused by name with no row (or accepted by rollback/retire under M-06 (b)); gate verbs refused up front with one named refusal for every arm | VERIFIED | `refuse_partial_evidence` (`promotion.py:161-175`) runs in `_resolve_operator_preconditions` (`engine.py:2316-2319`) for promote only (`refuse_partial=True`, `engine.py:2387`), keyed on `partial`, not `degraded`. `_arm_name_for_record` (`promotion.py:144-158`) takes `arm_id` first through `wiring_for_name`; the node-set fallback refuses a partial record it cannot identify as `PartialRunEvidenceError`, never as a false 404 or an `AssertionError`. The gate verbs raise `GateNotCalibratedError` at `engine.py:2384-2385`, before alias validation, trace resolution and any `Ledger()`. Own REST probe: promote of a new-format partial, an old-format partial (`arm_id` "seam") and a failed bypass trace each gave 422 `PartialRunEvidenceError` with no `ledger.db`; rollback accepted a new-format partial trace (200, option b); rollback and retire of an old-format partial gave 422 `PartialRunEvidenceError`; `promote-next` and `promote-now` gave 422 `GateNotCalibratedError` for all six arms with no `ledger.db` created. |
| 2 | Every promoted alias is selectable and every alias row resolves or refuses by name: empty and hash-shaped aliases refused by all three verbs; a HippoRAG alias resolves or is refused before a row; an unresolvable-arm row gives a named refusal on every selector-taking route | VERIFIED | The alias check is the first step of the shared prologue (`engine.py:2310-2311`, same `_INSTANCE_HASH_PATTERN` the Selector uses). `wiring_for_name` (`resolve.py:224-235`) resolves all six `all_wirings()` names, hipporag included, and returns None on a miss; `_resolve_alias` (`selectors.py:279-307`) maps None, a missing file and a tableless file to `UnsatisfiableSelectorError(selector_kind="alias", requested=alias)`. `_wiring_for_row` (`engine.py:1121-1132`) does the same on the verb paths. Own probe: `""`, 64-hex and `sha256:`+64-hex were refused 422 `InvalidPromotionAliasError` on promote, rollback and retire with no `ledger.db`; a HippoRAG trace promoted to 1.0.0, the alias resolved to `hipporag-base`, and `/query` under it returned 200; an alias row naming `ghost-arm` gave 422 `UnsatisfiableSelectorError` on `/query`, `/query/stream`, `/compare` and `/documents`, and no body contained `ghost-arm` or "known arms". |
| 3 | The ledger never keeps serving a tombstoned generation: retiring the version an active rollback targets is refused with ActiveGenerationRetirementError and appends nothing | VERIFIED | `Ledger.lineage` (`ledger.py:467-486`) follows `targets_version` through the latest minting row with a visited set. Retire refuses when the version is in the active row's lineage (`engine.py:2709-2711`); rollback refuses when any lineage version is tombstoned (`engine.py:2557-2560`). `by_alias` excludes tombstone rows (`ledger.py:443-449`), and the active generation cannot be retired, so the alias always points at a live generation. Own probe: naive 1.0.0, hybrid 2.0.0, rollback to 1.0.0 (3.0.0), then retire 1.0.0 gave 422 `ActiveGenerationRetirementError` and the row count was unchanged. After promoting local (4.0.0), retiring 1.0.0 succeeded; a rollback to 3.0.0, whose lineage reaches the tombstoned 1.0.0, was refused `TombstonedGenerationError`; the alias still served `lightrag-local`. |
| 4 | Alias history readable oldest first (ordinal, created_at, versions, record kind); connections close after every call; refused verbs on a fresh root create no ledger.db; trace debug accepts only a JSON boolean; tenancy follows G-35 | VERIFIED (REST/MCP history routes deferred to Phase 16) | `LedgerEntry(LedgerRecord)` adds `id` and `created_at` (`ledger.py:125-133`); `history_for_alias` orders by id ascending (`ledger.py:498-507`); `history(mutation_id)` is documented test-only. `close()`, `__enter__` and `__exit__` exist (`ledger.py:208-216`), and every verb closure and `_resolve_alias` use `with`. Rollback and retire use `open_existing` and raise `UnknownGenerationVersionError` on None (`engine.py:2547-2549, 2698-2700`). `StrictBool` at `rest.py:214` and `mcp/tools.py:200`. The tenancy rule is in the `Databasise` docstring (`engine.py:1140-1144`) and API-INVENTORY lines 13 and 828. Own probe: history rows `(1 promotion 1.0.0) (2 promotion 2.0.0) (3 rollback 3.0.0 -> 1.0.0) (4 promotion 4.0.0) (5 tombstone -> 1.0.0)`, all `LedgerEntry` with `created_at`. On a fresh root, rollback and retire gave `UnknownGenerationVersionError` (HTTP 404, its existing mapping), the gate verbs gave `GateNotCalibratedError`, and an alias query gave 422; no `ledger.db` existed afterwards. A trace flag of `"yes"`, `"true"`, `"1"`, `1` or `0` gave 422 with no `run_id` or `wiring_instance_hash`; `true` returned the full record. |
| 5 | Selection, validation and registry agree with the wirings: capability selection matches exercised effects; node-kind mismatches refused by name; every registered part reachable or unregistered; corpus wirings load through one path; docstrings current | VERIFIED (scope of "every registered part", see Human Verification 3) | `_match_capability` takes tokens over `without_recipe_only_nodes(candidate)` (`selectors.py:190`). Own probe: `[writes_artifact]`, `[writes_graph]`, `[writes_vector]` and `[writes_kv]` all refuse `UnsatisfiableSelectorError`, so none selects naive or hipporag. `kind-mismatch` (`parse.py:229-238`) names the node id, the node's kind, the component and the part's kind; all six `all_wirings()` entries parse ok. `codebase-memory-mcp@0.1.0` is absent from `default_registry()` and registered only in `falsifier2.probe_registry()` (`falsifier2.py:144-154`); `_parse` uses `probe_registry()` (`falsifier2.py:311`); the wiring moved to `tests/fixtures/codebase-memory-mcp.json`. `_corpus_wiring` calls `load_wiring(family, variant=f"corpus-{operation}")` and maps `FileNotFoundError` to `NoWritePathForModalityError` (`engine.py:678-692`); `_WIRINGS_ROOT` no longer appears in `engine.py`. Banned-phrase scan: none of 'registry is empty', 'every lookup refuses', 'five arms', '_ARM_NAMES', 'known arms' in `selectors.py`; no 'seven Phase-1', 'two declaration-only placeholders', 'five HippoRAG parts' or fixed part count in `registry.py`; no 'pending consumer' in `schema.py`; no 'stall' in `ledger.py`; the `test_alias_registry.py` docstring says the verbs exist. |

**Score:** 5/5 roadmap truths verified, 0 behavior-unverified.

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Alias history over REST and MCP (SC4 is met at the engine read only) | Phase 16 | CONN-06 `GET /ledger/aliases`, CONN-07 `POST /ledger/history`; 14-CONTEXT D-09 |

### Requirements Coverage

All 14 LEDG IDs are declared in Phase 14 plans; no orphaned LEDG ID. Every ledger row is `done` with a `test_ref`, and every row has a `check-fail` record in the ledger history (v694 to v712, exit 1 by assertion).

| Requirement | Status | Evidence |
|-------------|--------|----------|
| LEDG-01 | SATISFIED (M-06 option b, D-01) | REST probe above; test_partial_run_evidence.py |
| LEDG-02 | SATISFIED (G-18: promote only, keyed on `partial`, D-03) | REST probe (failed bypass); test_promote_refuses_partial.py |
| LEDG-03 | SATISFIED (M-07 option a, D-05) | hipporag and ghost-row probes; test_alias_resolution.py |
| LEDG-04 | SATISFIED (G-17: by version through lineage, D-06) | lineage probe; test_retire_lineage.py |
| LEDG-05 | SATISFIED | bad-alias probe on three verbs; test_operator_alias_validation.py; protected test_promote_alias_validation.py (SEAM-12) passes |
| LEDG-06 | SATISFIED (D-08 narrowed for the read path, see Human 2) | fresh-root probe; protected test_ledger_lifecycle.py passes; test_review14_fixes.py (8 tests) passes |
| LEDG-07 | SATISFIED (engine read; routes Phase 16) | history probe; test_ledger_history.py |
| LEDG-08 | SATISFIED (G-19, D-04) | six-arm gate probe; test_promotion_posture.py::test_gate_verbs_are_refused_up_front_for_every_arm; API-INVENTORY:586 |
| LEDG-09 | SATISFIED (G-35: one store_root is one tenant, D-10) | strict-flag probe; test_trace_resolve_strict_flag.py |
| LEDG-10 | SATISFIED (already met at 3fd6e4c, D-11) | writes_* probe; test_capability_effects.py |
| LEDG-11 | SATISFIED (reports a named violation, D-12) | parse.py:229-238; test_node_kind.py |
| LEDG-12 | SATISFIED (unregistered, D-13) | registry probe; test_registry_reachability.py; protected test_refusal_reachability.py (WIRE-17) passes under grant v706 |
| LEDG-13 | SATISFIED | engine.py:678-692; test_corpus_wiring.py |
| LEDG-14 | SATISFIED | banned-phrase scan; test_docstring_currency.py |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 14 LEDG row test files | pytest of the 14 test_ref files | 108 passed in 24.21s | PASS |
| Related tests: review-fix regressions, unresolvable-row verbs, WIRE-17, SEAM-04/12/14/16, alias registry, WIRE-01 selector reachability, REST transport, tests/evidence, tests/validator, tests/mcp, tests/ledger | pytest of those files and directories | 535 passed in 89.77s | PASS |
| SC1-SC5 REST probe (real `create_app`, `TraceStore`, `Ledger`, `default_registry()`, `all_wirings()`) | `probe14.py` and `probe14b.py` in the session scratchpad | 31/33 checks pass; the 2 misses were the probe's own wrong status expectation (422 instead of the existing 404 for `UnknownGenerationVersionError`), and the re-check confirmed no `ledger.db` was created | PASS |
| Full offline gate, both invocation styles | run separately by the orchestrator (not run here) | orchestrator to add (14-10 recorded 2598 passed in both styles at an earlier HEAD) | - |

### Probe Execution

Step 7c: SKIPPED. No `probe-*.sh` is declared by any Phase 14 PLAN or SUMMARY.

### Anti-Patterns Found

No TBD, FIXME, XXX, TODO or HACK marker in any of the 18 non-test files changed since the phase base bb52fbb. The review closed with 0 critical and 0 warning open; 21 info findings remain open as advisory (14-REVIEW-DISPOSITION.md).

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docs/gui/API-INVENTORY.md` | 586 | "500: `sqlite3.OperationalError` under ledger write contention" is still a listed promote outcome | Info | Concurrency, not trace input, so SC1 ("on any trace") holds. A raw 500 path remains on the verbs. |
| `databasise/seam/promotion.py` | 171 | `zip` without `strict=True` in `refuse_partial_evidence` (A-IN-01) | Info | `trace_ids` and the records come from the same list, so lengths match today |
| `databasise/ledger/ledger.py` | 163-206 | A garbage-bytes `ledger.db` still raises a raw sqlite error on the alias read (ITER2 IN-01) | Info | Not a LEDG case; pre-existing |
| `databasise/wirings/resolve.py` | 37 | comment says "LightRAG's five arms"; there are five LightRAG arms, so it is accurate | Info | No action |

### Human Verification Required

1. **A-WR-02 MAJOR-bump repair.** Seed an alias whose active row names a vanished wiring, then promote. Expect a MAJOR bump, the class derived as for a first promotion, `parent` holding the vanished name, and rollback and retire still refusing by name. The owner confirms the always-MAJOR policy.
2. **D-08 read-path narrowing.** The consumer alias read opens with `query_only`, does not checkpoint on close, and never migrates; only the writer verbs migrate an old file. The owner confirms the narrowing and the plain-path open in place of the `mode=ro` URI, or grants a check edit to the LEDG-06 lifecycle test for the URI form.
3. **SC5 "every registered part".** Four reference parts with no admission record are registered and reachable through no selector. The owner confirms that SC5 means LEDG-12's "admitted part" (D-13), or asks for them to be unregistered or reachable.

### Gaps Summary

No goal-blocking gap. Every success criterion and every LEDG row was checked against the code and by tests run here, and a separate REST probe confirmed each behavior. Notes for the orchestrator:

- `.planning/REQUIREMENTS.md` still shows LEDG-01..11, 13 and 14 as `[ ]` and "Pending" (lines 416-464, 935-948). Only LEDG-12 is Complete. Mark all 14 Complete when the phase closes. Per memory, a gaps_found result would revert every phase row, so do not record this result as gaps_found.
- The BAK start gate still reports every S3 trace part stale on a REQUIREMENTS.md hash mismatch and every row `not-checked at S3`. It also reports WIRE-10 and WIRE-17 as "check changed after its first failing run", which needs the owner's `lock-checks`. This affects all phases, not Phase 14 code.
- Phase 16 text amendments recorded in 14-CONTEXT Specifics (CONN-05, CONN-07, CONN-09) are still to be applied before Phase 16 plans.

---

_Verified: 2026-10-21T06:01:21Z_
_Verifier: Claude (gsd-verifier)_

## Human Verification Resolution (2026-10-21)

The owner said "continue" after Claude recommended an option for each item. Claude took that as accepting the recommendations; the owner may revise any of them.

| Item | Decision |
|------|----------|
| A-WR-02 repair policy | **Keep.** Repairing an alias whose active row names an unresolvable wiring always takes a MAJOR bump, because once the old wiring is gone nothing shows the new surface is compatible with it. Rollback and retire on that alias still refuse by name. |
| D-08 read-path narrowing | **Keep.** Consumer alias reads open with `PRAGMA query_only` and no checkpoint on close, and never migrate. Only promote, rollback and retire migrate an old file. The plain-path open stays, because the protected LEDG-06 lifecycle check identifies connections by path. |
| SC5 wording | **SC5 means LEDG-12's wording:** no *admitted* registered part is unreachable. The four parts that no selector reaches (`parts-core/passthrough`, `fake-retriever`, `fake-llm-caller`, `fixpoint-body`) carry no admission record. They are runner helpers and test doubles, not consumer parts. |

Final offline gate at the final code commit (`check_offline_suite.py`): 2608 passed, 4 deselected, in both styles; exit 0.

---
phase: 14-promotion-ledger
verified: 2026-11-01T00:39:04Z
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
covered_digest: "v3:sha256:0dd921d3ab7629758d2d0c02da12a18f8813c962359bc60775ce0cfb07cd1be4"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
deferred:
  - truth: "An operator can read an alias's full history over REST and MCP (SC4 is met at the engine read, Ledger.history_for_alias)"
    addressed_in: "Phase 16"
    evidence: "CONN-06 GET /ledger/aliases and CONN-07 POST /ledger/history; 14-CONTEXT D-09: engine read only in Phase 14. Phase 16 has since built both routes (commits cd758a8, aeb108c)."
---

# Phase 14: Promotion & Ledger Verification Report

**Phase Goal:** The operator verbs never fail with a 500 on any trace, every alias with a generation can be selected and resolves, and an alias's history is readable from the ledger
**Verified:** 2026-10-31
**Status:** passed
**Re-verification:** Yes. The earlier report (2026-10-21, status passed) went stale because Phases 15, 16 and 17 changed 15 covered files. Every moved file was re-read against the current code, and the Phase 14 tests were re-run.

## What moved since the last report

| Moved file | Changed by | Effect on Phase 14 truths |
|---|---|---|
| `seam/engine.py` | Phase 15 (TOOL-12 floors, TOOL-16), Phase 16 (preview, read-only opens, operator reads) | Promote prologue extracted to `_promotion_prologue`, shared with `preview_promotion`. Order and refusals unchanged. Gate verbs now lift in two stages (below). |
| `ledger/ledger.py` | Phase 16 (`aliases()`, `snapshot()`, read-only close checkpoint decided at close time) | `lineage`, `history_for_alias`, `close`, context manager and `open_existing` are intact. |
| `seam/promotion.py`, `seam/refusals.py`, `seam/rest.py`, `mcp/tools.py`, `parts/registry.py`, `parts_core/declared_only.py`, `evidence/*`, `pyproject.toml`, docs | Phase 15 and 16 | Docstring edits, new refusals (`UnknownGraphNodeError`, `InvalidPartFieldError`), registry load-time admission, lazy cbm part build. No Phase 14 behavior removed. `debug: StrictBool` is still on both transports. |

### Re-verification 2026-10-31 (Phase 18 staleness)

The report went stale a second time because Phase 18 (GUI Live) changed two covered files after the 2026-10-31 run: commits 6a36f2d (18-01) and 65dd699 (18-02). No file in the Phase 14 code scope changed; the last commit touching `seam/`, `mcp/`, `parts/`, `parts_core/`, `wirings/` or `evidence/` is still the Phase 16 fix 587feda, which the run above already covered.

| File | Change (`git diff f674eba HEAD`) | Effect on Phase 14 truths |
|---|---|---|
| `databasise/pyproject.toml` | Adds `"databasise.console"` to `[tool.setuptools] packages` and a `"databasise.console" = ["operator-console.html"]` package-data line. | Additive. `databasise.ledger`, `databasise.seam`, `databasise.mcp`, `databasise.wirings`, `databasise.parts` and `databasise.parts_core` remain listed; the `databasise-rest` and `databasise-mcp` entry points are unchanged. Import check from `databasise/`: `databasise.seam.engine`, `databasise.seam.rest`, `databasise.mcp.tools`, `databasise.wirings.resolve` and `databasise.parts.registry` import, and `default_registry()` lists 37 parts. |
| `docs/gui/API-INVENTORY.md` | One new paragraph at line 766 (section 5, operator routes) describing `databasise-rest --operator --console` and `GET /console`. | Additive. The cited line 588 (promote outcomes, two gate stages) is before the insertion and unchanged. No verb route, request shape or named refusal documented for promote, rollback, retire or the history reads was edited. |

No row of the tables above cites packaging or the console, so no test re-run was required. The five success criteria and the 14 LEDG requirements hold as recorded; the fingerprint was regenerated over the same covered files.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence (current code) |
|---|-------|--------|-------------------------|
| 1 | Promote, rollback and retire never 500 on any trace: partial or failed traces refused by name with no row (or accepted by rollback/retire under M-06 (b)); gate verbs refused up front with one named refusal for every arm | VERIFIED (gate stage 1 now sits under TOOL-12, see note) | `_resolve_operator_preconditions(..., refuse_partial=True)` is called by `_promotion_prologue` for promote only (`engine.py:2868-2870`); rollback and retire call it without the flag (`engine.py:3078, 3233`), which is option (b). `refuse_partial_evidence` raises `PartialRunEvidenceError` before arm matching (`engine.py:2751-2752`). `GateNotCalibratedError` for `promote-next` and `promote-now` is raised at `engine.py:2860-2866`, before alias validation, trace resolution and any `Ledger()`, identical for every arm. `tests/seam/test_partial_run_evidence.py`, `test_promote_refuses_partial.py`, `test_promotion_posture.py` pass. |
| 2 | Every promoted alias is selectable and every alias row resolves or refuses by name: empty and hash-shaped aliases refused by all three verbs; a HippoRAG alias resolves or is refused before a row; an unresolvable-arm row gives a named refusal on every selector-taking route | VERIFIED | Alias check is the first statement of the shared prologue (`engine.py:2744-2745`, `InvalidPromotionAliasError`). `wiring_for_name` (`wirings/resolve.py:224-235`) resolves all six `all_wirings()` names including `hipporag`, and returns None for `ghost` and `codebase-memory-mcp` (run live). Verb paths use `_wiring_for_row`; `_resolve_alias` maps None to `UnsatisfiableSelectorError`. `test_operator_alias_validation.py`, `test_alias_resolution.py`, protected `test_promote_alias_validation.py` pass. |
| 3 | The ledger never keeps serving a tombstoned generation: retiring the version an active rollback targets is refused with ActiveGenerationRetirementError and appends nothing | VERIFIED | `Ledger.lineage` (`ledger.py:500-519`) walks `targets_version` with a visited set. Retire refuses when `version in ledger.lineage(alias, active.minted_version)` inside the `BEGIN IMMEDIATE` span (`engine.py:3255-3257`); rollback refuses when any lineage version is tombstoned (`engine.py:3103-3106`). `by_alias` excludes tombstones (`ledger.py:476-480`). `test_retire_lineage.py` asserts the refusal type, an unchanged row count, and the active row's kind and version. |
| 4 | Alias history readable oldest first (ordinal, created_at, versions, record kind); connections close after every call; refused verbs on a fresh root create no ledger.db; trace debug accepts only a JSON boolean; tenancy follows G-35 | VERIFIED (REST/MCP history routes now built in Phase 16) | `LedgerEntry` adds `id` and `created_at` (`ledger.py:125-133`); `history_for_alias` orders `id ASC` (`ledger.py:541-550`). `close`, `__enter__`, `__exit__` (`ledger.py:215-237`); the verb closures use `with` (`engine.py:2968, 3097, 3248`). Rollback and retire use `open_existing` and raise `UnknownGenerationVersionError` on None (`engine.py:3093-3095, 3244-3246`); `_refuse_gate_verb` and the preview open read-only and create nothing. `debug: StrictBool` at `rest.py:215` and `mcp/tools.py:200`. `ledger/test_ledger_history.py`, `test_ledger_lifecycle.py` (protected), `test_ledger_read_only_close.py`, `test_trace_resolve_strict_flag.py` pass. |
| 5 | Selection, validation and registry agree with the wirings: capability selection matches exercised effects; node-kind mismatches refused by name; every registered part reachable or unregistered; corpus wirings load through one path; docstrings current | VERIFIED (scope as resolved on 2026-10-21, see below) | Live check of `default_registry().keys()`: `codebase-memory-mcp@0.1.0` is absent; the part is built lazily in `declared_only.py` (`__getattr__`) and registered only in `falsifier2.probe_registry()`. Phase 15 added load-time `admit_registry` to `default_registry()` and it still loads. `test_capability_effects.py`, `validator/test_node_kind.py`, `parts/test_registry_reachability.py`, `test_corpus_wiring.py`, `evidence/test_docstring_facts.py`, protected `test_refusal_reachability.py` pass. |

**Score:** 5/5 roadmap truths verified, 0 behavior-unverified.

**Note on SC1 and Phase 15 (TOOL-12).** Since the first report, a persisted floor under `<store_root>/floors.db` lifts the gate in a second stage (`engine.py:2766-2838`). The up-front `GateNotCalibratedError` is unchanged for the state the criterion describes: no floor persisted, the same refusal for every arm, no `ledger.db` created. With a valid floor the verbs still never append; they raise `GateVerbNotBuiltError` or `MeasurementPostureRefusalError`, both named 422 refusals. LEDG-08 already placed floor persistence in EVAL-10's scope, and `API-INVENTORY.md:588` describes both stages. This is a documented supersession, not a regression.

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Alias history over REST and MCP | Phase 16 (since built) | CONN-06 `GET /ledger/aliases`, CONN-07 `POST /ledger/history`; commits cd758a8, aeb108c |

### Requirements Coverage

All 14 LEDG IDs are declared in Phase 14 plans and appear in `.planning/REQUIREMENTS.md` (lines 416-464) as `[x]` and in the traceability table (lines 937-950) as Complete. No orphaned LEDG ID.

| Requirement | Status | Evidence |
|-------------|--------|----------|
| LEDG-01 | SATISFIED (M-06 option b) | `engine.py:2751, 3078, 3233`; test_partial_run_evidence.py |
| LEDG-02 | SATISFIED (G-18, promote only, keyed on `partial`) | test_promote_refuses_partial.py |
| LEDG-03 | SATISFIED (M-07 option a) | `resolve.py:224-235`; test_alias_resolution.py |
| LEDG-04 | SATISFIED (by version through lineage) | `engine.py:3255-3257`; test_retire_lineage.py |
| LEDG-05 | SATISFIED | `engine.py:2744-2745`; test_operator_alias_validation.py; protected test_promote_alias_validation.py |
| LEDG-06 | SATISFIED | `ledger.py:164-237`; protected test_ledger_lifecycle.py; test_review14_fixes.py |
| LEDG-07 | SATISFIED | `ledger.py:125-133, 541-550`; test_ledger_history.py |
| LEDG-08 | SATISFIED (stage 1 up front; stage 2 added by TOOL-12) | `engine.py:2860-2866`; test_promotion_posture.py; API-INVENTORY:588 |
| LEDG-09 | SATISFIED (one store_root is one tenant) | `rest.py:215`, `mcp/tools.py:200`; test_trace_resolve_strict_flag.py |
| LEDG-10 | SATISFIED | test_capability_effects.py |
| LEDG-11 | SATISFIED | validator/test_node_kind.py |
| LEDG-12 | SATISFIED (unregistered) | live registry listing; test_registry_reachability.py; protected test_refusal_reachability.py |
| LEDG-13 | SATISFIED | test_corpus_wiring.py |
| LEDG-14 | SATISFIED | evidence/test_docstring_facts.py |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 14 LEDG tests plus ledger/, registry reachability, node-kind, docstring facts, protected WIRE-17/SEAM-12/LEDG-06 checks | targeted `pytest` of 16 test files and `tests/ledger` | 163 passed in 88.7s | PASS |
| Registry and wiring resolution | `default_registry().keys()`; `wiring_for_name` over `naive`, `hipporag`, `ghost`, `codebase-memory-mcp` | no cbm part in registry; `naive` and `hipporag` resolve; `ghost` and `codebase-memory-mcp` give None; 6 wirings | PASS |
| Full offline gate | run by the orchestrator, not here | - | not run here |
| Packaged modules still import after the Phase 18 `pyproject.toml` edit (2026-10-31 re-check) | `.venv/bin/python -c "import databasise.seam.engine, databasise.seam.rest, databasise.mcp.tools, databasise.wirings.resolve, databasise.parts.registry"` | imports ok, 37 parts | PASS |

### Probe Execution

Step 7c: SKIPPED. No `probe-*.sh` is declared by any Phase 14 PLAN or SUMMARY.

### Anti-Patterns Found

No TBD, FIXME or XXX marker in `promotion.py`, `ledger.py`, `refusals.py`, `registry.py`, `selectors.py` or `resolve.py`.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docs/gui/API-INVENTORY.md` | 588 | "500: `sqlite3.OperationalError` under ledger write contention" remains a listed promote outcome | Info | Concurrency, not trace input; SC1 ("on any trace") holds. |
| `databasise/seam/promotion.py` | 268-276 | `enforce_gate_verb_posture` is no longer called by `promote` (15-16); kept for its pinned signature | Info | Docstring states it; dead from `promote`. |
| `databasise/seam/promotion.py` | 171 | `zip` without `strict=True` in `refuse_partial_evidence` (A-IN-01) | Info | Lengths match by construction. |

### Human Verification

None open. The three owner items from the first report (A-WR-02 always-MAJOR repair, D-08 read-path narrowing, SC5 scope meaning "admitted parts") were resolved on 2026-10-21 and are unchanged; see the resolution table below. The Phase 16 change to the read-only close (checkpoint decided at close time, `ledger.py:215-231`) refines the D-08 residuals and keeps the plain-path open that the protected LEDG-06 check requires.

### Gaps Summary

No goal-blocking gap. The code the 15 moved files touch still delivers all five criteria, and the Phase 14 tests pass against HEAD.

---

_Verified: 2026-10-31_
_Verifier: Claude (gsd-verifier)_

## Human Verification Resolution (2026-10-21, carried forward)

| Item | Decision |
|------|----------|
| A-WR-02 repair policy | **Keep.** Repairing an alias whose active row names an unresolvable wiring always takes a MAJOR bump. Rollback and retire on that alias still refuse by name. |
| D-08 read-path narrowing | **Keep.** Consumer alias reads open with `PRAGMA query_only` and never migrate. Only promote, rollback and retire migrate an old file. The plain-path open stays because the protected LEDG-06 lifecycle check identifies connections by path. |
| SC5 wording | **SC5 means LEDG-12's wording:** no *admitted* registered part is unreachable. The four runner helpers and test doubles (`parts-core/passthrough`, `fake-retriever`, `fake-llm-caller`, `fixpoint-body`) carry no admission record. |

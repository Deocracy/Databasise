---
phase: 01-machine-core
verified: 2026-08-31T00:00:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 2/4
  gaps_closed:
    - "Runner executes a wiring graph to completion under structured concurrency, metering spend at each node's declared boundary (ROADMAP Success Criterion 2 / MACH-05)"
    - "A wiring arm containing an opaque node writes quarantined and cannot reach shared KV (ROADMAP Success Criterion 4 / MACH-08)"
  gaps_remaining: []
  regressions: []
deferred: []
human_verification: []
---

# Phase 01: Machine Core Verification Report

**Phase Goal:** The machine executes a wiring graph over embedded stores with stable component identity, inside one local process tree
**Verified:** 2026-08-31T00:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (plan 01-10)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Owner installs Databasise as a library, starts with no external DB server/container — Cozo (graph), Faiss (vector), SQLite (KV/lexical/registry/ledger) embedded in one process tree | ✓ VERIFIED | Unchanged since prior verification; not touched by 01-10. `pyproject.toml` still declares exactly 4 runtime deps; `tests/test_embed_startup.py` still passes (confirmed in this run's full-suite pass). |
| 2 | Runner executes a wiring graph to completion under structured concurrency, metering spend at each node's declared boundary, with the intra-node concurrency mechanism decided and written down | ✓ VERIFIED | **Gap 2 closed.** `runner/scheduler.py:505` calls `meter(node_id, part.effects, token_allowances[node_id], tokens)` and `:506` calls `evaluate_guards(...)` — both real live call sites, confirmed by direct read (not grep alone). `tokens`/`cache_hit` are read from the node body's own return value via `_body_report()` (line 504), never a literal. `budget_state=token.state` and `realised_budget_share=realised_share(...)` (lines 517-518) are computed, not hardcoded — the four "real value: ..." placeholder comments named in the original Gap 2 finding are gone. A budget halt sets `partial=True`/`stop_reason="budget_halt"` and breaks further batch scheduling (lines 507-510, 526-532); `databasise/__init__.py` now threads `partial`/`degraded`/`stop_reason`/`degradation_reason` into `RunRecord(...)` (lines 99-102), so `RunRecord.__post_init__`'s honesty invariant (`runner/trace.py:146-152`, which refuses a record with a `halted` node under `partial=False`) is satisfiable and enforced. `tests/test_phase_success_criteria.py::test_criterion_2_...` was rewritten to distinguish a metered node (`llm-caller`, real `tokens["prompt_tokens"] > 0`, share strictly between 0 and 1) from unmetered nodes (share exactly `0.0`, all-zero tokens) — a hardcoded constant would now fail this test (confirmed by reading the assertions at lines 258-274, which assert exact zero for unmetered and strict inequality for the metered node). 12/12 tests in `tests/runner/test_live_metering.py` pass, including boundary/adjacency/empty/ordering/precision/guard-refusal edge cases (independently re-run as named single tests: boundary and adjacency both PASS). Intra-node concurrency mechanism (per-node `asyncio.Semaphore` sized from `config.max_concurrency`, D-09) unchanged and still real. |
| 3 | The same component wired twice with byte-identical config resolves to one instance identity and one cache partition; a changed config byte yields a different `config_hash`/partition; a wiring node id is never usable as an identity | ✓ VERIFIED | Unchanged since prior verification; not touched by 01-10. `test_criterion_3_identity_stability_and_separation` still passes. |
| 4 | A wiring arm containing an `opaque` node writes `quarantined` and cannot reach `shared` KV; per-part graph and vector namespaces are visibly separate after a run | ✓ VERIFIED | **Gap 1 residual closed.** The trusted-source fix itself (`scheduler.py` deriving `execution_mode`/store-scoping/`resumable` from `parsed.parts[node_id]`, `blast_radius.py` gating on `parsed.parts.items()`, `parse.py`'s `CODE_EFFECTS_EXCEED_PART` subset check) was independently re-confirmed by direct source read — matches 01-10-PLAN's cited file:line evidence exactly. The one missing regression test now exists and passes: `tests/validator/test_blast_radius.py::test_under_declaring_wiring_cannot_route_a_shared_artifact_write_around_the_rule` wires a Part declaring `writes_artifact`/`shared`/`opaque` with `WiringNode.effects` omitted (defaults to `[]`) through the real `parse_wiring` path and asserts the blast-radius refusal still fires; its discriminating sibling (`structural_depth="stage"`) asserts `report.ok is True`, proving the rule is not vacuous. Both independently re-run and PASS. A new AST-based structural test (`tests/test_trusted_source_invariant.py`) asserts no enforcement path in `scheduler.py`/`blast_radius.py` reads a wiring node's `effects`/`kind` — passes, and is non-vacuous (does not trip on the identical prose both modules' docstrings carry). **Caveat, not a blocker:** this AST check has a real, reproducible blind spot (see Anti-Patterns / WR-01 below) — it does not track a `for node_id, node in parsed.nodes.items():` loop-binding shape, which is the exact shape the original CR-01 bug used. Independently confirmed by direct source reading (not by relying on the incomplete test) that the CURRENT code does not use that shape anywhere in the two scanned modules, so the truth holds today; the gap is in the regression net's future coverage, not in present behavior. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/runner/scheduler.py` | Live dispatch stamping real `budget_state`/`realised_budget_share`/`tokens`/`guards_fired` | ✓ VERIFIED | `meter()`/`evaluate_guards()` live call sites confirmed at lines 505-506; `_body_report`, `_validated_guards`, `_validated_token_allowance`, `InvalidTokenAllowanceError`, `DEFAULT_TOKEN_ALLOWANCE` all present and wired |
| `databasise/runner/budget.py` | `meter()`, `realised_share()` | ✓ VERIFIED | Now has a live caller in `scheduler.py` (previously zero call sites outside its own test file) |
| `databasise/runner/guards.py` | `declare_guard()`, `evaluate_guards()` | ✓ VERIFIED | Now has live callers in `scheduler.py`'s pre-flight block and post-dispatch stamp |
| `databasise/__init__.py` | Threads honesty fields into `RunRecord` | ✓ VERIFIED | `partial`/`degraded`/`stop_reason`/`degradation_reason` now passed at lines 99-102 (previously dropped) |
| `databasise/validator/blast_radius.py` | Gates on registry `Part.effects`, never wiring `WiringNode.effects` | ✓ VERIFIED | `for node_id, part in parsed.parts.items()` (line 49), gates on `part.effects` (line 54) |
| `databasise/tests/runner/test_live_metering.py` | End-to-end metered run through the public seam, plus edge battery | ✓ VERIFIED | New file, 12 tests, all pass; independently re-run as named single tests |
| `databasise/tests/test_trusted_source_invariant.py` | AST assertion that no enforcement module reads a wiring node's effects/kind | ✓ VERIFIED (with caveat) | New file, 2 tests, both pass; non-vacuous (confirmed via reproduction). Blind spot for for-loop bindings confirmed independently — see Anti-Patterns |
| `databasise/tests/validator/test_blast_radius.py` | Under-declaring-wiring refusal regression | ✓ VERIFIED | 2 new tests (refusal + discriminating sibling), both pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `parsed.parts[node_id].effects` (registry Part, trusted) | `runner.budget.meter()` | `scheduler.py:505` | ✓ WIRED | Confirmed by direct read — `part.effects` passed, never `node.effects` |
| node body output dict | `NodeTrace.tokens`/`cache_hit` | `_body_report()`, `scheduler.py:504` | ✓ WIRED | Confirmed; `isinstance` guards against non-Mapping output |
| `node.config['guards']` | `NodeTrace.guards_fired` | `_validated_guards()` (pre-flight) -> `evaluate_guards()` (post-dispatch) | ✓ WIRED | Confirmed; declaration-order preserved (edge test `test_ordering_...` passes) |
| `scheduler.run_wiring`'s `partial`/`stop_reason`/`degraded`/`degradation_reason` | `databasise.run_wiring` -> `RunRecord.__post_init__` | direct threading | ✓ WIRED | Confirmed at `__init__.py:99-102`; honesty invariant enforced (raises `ValueError` if violated) |
| `WiringNode.effects` omitted, resolved `Part.effects=["writes_artifact"]`, scope `shared`, depth `opaque` | blast-radius refusal | `parse_wiring` -> `blast_radius_violations` | ✓ WIRED | Confirmed by the new regression test passing, and independently by direct source read of `blast_radius.py` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full phase test suite | `cd databasise && uv run pytest -q` | `233 passed in 17.09s` | ✓ PASS |
| `runner.budget`/`runner.guards` live call sites | Direct read of `scheduler.py:505-506` | `meter(node_id, part.effects, ...)`, `evaluate_guards(...)` confirmed, sourced from `part.effects` not `node.effects` | ✓ CONFIRMS GAP 2 CLOSED |
| Named metering edge tests | `pytest tests/runner/test_live_metering.py::test_boundary_... tests/runner/test_live_metering.py::test_adjacency_...` | 2/2 PASS | ✓ PASS |
| Named blast-radius regression + AST invariant | `pytest tests/validator/test_blast_radius.py::test_under_declaring_... tests/test_trusted_source_invariant.py` | 3/3 PASS | ✓ PASS |
| AST invariant blind-spot reproduction | Reconstructed the original `for node_id, node in parsed.nodes.items(): ... node.effects` shape and ran `_wiring_node_bound_names`/`_flagged_attribute_reads` against it directly | Returns empty bound-names set and zero findings — the check does NOT flag this shape | ⚠️ CONFIRMS WR-01 (non-blocking, see Anti-Patterns) |
| `write_artifact`'s caller-supplied `scope`/`effective_depth` reachability | `grep -rn "write_artifact(" --include="*.py"` excluding tests | Zero non-test callers found | ✓ CONFIRMS WR-03/second-call-site issue is currently dormant, not live-reachable |
| Import boundary checker | `uv run python -m databasise.tools.check_import_boundary` | exit 0 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|-------------|--------|----------|
| EMBED-01 | 01-01, 01-05, 01-06, 01-09 | Single self-contained process tree, embedded Cozo/Faiss/SQLite, no server, no Docker | ✓ SATISFIED | Unchanged; see Truth 1 |
| MACH-05 | 01-01, 01-02, 01-03, 01-08, 01-09, 01-10 | Structured-concurrency runner, metering spend at declared boundary, full RIG §TR.1 field set | ✓ SATISFIED | Gap 2 closed by 01-10; see Truth 2 |
| MACH-06 | 01-01, 01-02, 01-04, 01-07, 01-09 | name@version + config_hash identity, content-addressed artifact registry, instance identity never a node id | ✓ SATISFIED | Unchanged; see Truth 3 |
| MACH-08 | 01-02, 01-03, 01-05, 01-06, 01-07, 01-09, 01-10 | KV shared-scope rule, opaque→quarantined, per-part namespaces, artifact sharing iff recipe-hash-identical | ✓ SATISFIED | Gap 1 residual closed by 01-10; see Truth 4 |

No orphaned requirements: REQUIREMENTS.md maps only these four IDs to Phase 1. (Note: REQUIREMENTS.md's own checklist still shows these as unchecked `[ ]`/"Pending" — a bookkeeping staleness, not a code gap; the orchestrator should update it alongside this verification.)

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `databasise/tests/test_trusted_source_invariant.py` | 67-82 | `_wiring_node_bound_names` tracks only `ast.Assign` single-`Name`-target bindings, not `ast.For` loop targets (`for node_id, node in parsed.nodes.items():`) | ⚠️ Warning | Reproduced independently: this is the exact shape the original CR-01 bug used in `blast_radius.py`. A future silent regression back to that shape would pass this "structural pin" undetected. Current code does not use this shape (confirmed by direct read), so today's Truth 4 holds regardless — but the regression net protecting it going forward is weaker than 01-10-SUMMARY's "structurally pinned against silent regression" claim implies. Matches 01-REVIEW.md WR-01 exactly. |
| `databasise/stores/vector.py` | 253-293 | `index_done_callback` snapshots `self._pending` before an `await`-suspending `run_in_executor` call, then unconditionally `.clear()`s the live (possibly-mutated-during-suspension) dict afterward | 🛑 Critical (code quality), non-blocking to this phase's success criteria | Real, demonstrated data-loss bug (01-REVIEW.md CR-01) if a concurrent `upsert` lands during a flush. Confirmed currently unreachable: `databasise/__init__.py`'s composer wires only `"kv"` into `ctx.stores`, and no non-test caller of any Faiss-touching path exists in the live scheduler dispatch today (grep confirms). Does not affect any of the 4 ROADMAP success criteria's literal text (none asserts concurrent-write safety for the vector store). Recommend tracking for closure before Faiss is ever wired into a live node. |
| `databasise/registry_artifact/write_path.py` | 50-72 | `_blast_radius_check`/`write_artifact` take `scope`/`effective_depth` as plain caller-supplied keyword arguments rather than deriving them from a resolved, registry-trusted `Part` | ⚠️ Warning (carryover, not fixed by 01-10, was out of its declared scope) | Confirmed: zero non-test callers of `write_artifact` exist anywhere in the package (grep). Dormant today — not reachable via the live scheduler path, so it does not violate Truth 4 currently. Matches 01-REVIEW.md WR-03. Should be closed before any part body is wired to call `write_artifact` directly with untrusted-derived arguments. |
| `databasise/runner/scheduler.py` | 297-306 | `_validated_guards` lets a malformed `config.guards` entry leak a bare `TypeError` from `declare_guard(**entry)` instead of a named refusal (the same class WR-04 fixed for `max_concurrency`) | ⚠️ Warning | Confirmed by direct read. Non-blocking: still refuses pre-flight, just with a less-actionable exception type. Matches 01-REVIEW.md WR-02. |
| `databasise/runner/trace.py` | 44, 79-80 | `TIER_PLACEHOLDER = "T3"` | ℹ️ Info | Explicitly documented sentinel, scoped to Phase 2's evidence-tier mechanism — not a hidden debt marker, no action needed this phase |

No unreferenced `TBD`/`FIXME`/`XXX` markers found in any file modified by plan 01-10 (confirmed by direct grep).

### Gaps Summary

Both BLOCKER gaps from the prior verification (2026-08-30) are closed in source, independently re-confirmed by direct reading (not SUMMARY.md claims alone) and by running the named regression tests as isolated single-test invocations:

1. **Gap 1 (MACH-08 / Success Criterion 4) — CLOSED.** The trusted-source fix was already landed before this re-verification cycle (commits `3b05d54`, `973592e`); plan 01-10 supplied the one missing regression test (`test_under_declaring_wiring_cannot_route_a_shared_artifact_write_around_the_rule`) and a structural AST pin. Both pass and are non-vacuous. One caveat surfaced independently during this re-verification (not merely inherited from 01-REVIEW.md): the AST pin's blind spot for `for`-loop node-mapping bindings is real and reproducible — logged as WR-01, non-blocking, since the current enforcement code does not use that shape (confirmed by direct source read, independent of the flawed test).

2. **Gap 2 (MACH-05 / Success Criterion 2) — CLOSED.** `runner/budget.py`'s `meter()` and `runner/guards.py`'s `evaluate_guards()` now have live call sites in `scheduler.py`'s successful-dispatch path; every previously-hardcoded trace field (`budget_state`, `realised_budget_share`, `tokens`) is now computed from the node's own declared effects (sourced from the registry's `Part`, never the wiring) and its body's real return value. `test_criterion_2_...` was rewritten to distinguish a metered from an unmetered node rather than assert a shared constant — confirmed by reading the assertions directly, not by trusting the SUMMARY's claim that it was rewritten correctly.

No new BLOCKER-level gaps were found. Two pre-existing, correctly-scoped-out Warning-level findings (the Faiss flush race, the write_path.py second call site) remain open but are confirmed dormant/unreachable via any live path today, so they do not affect this phase's four observable truths. Recommend tracking both (plus WR-01's AST blind spot and WR-02's bare-`TypeError` leak) as follow-up items before Phase 2 work that would make them reachable (e.g. wiring Faiss into a live node, or calling `write_artifact` from a part body).

---

_Verified: 2026-08-31T00:00:00Z_
_Verifier: Claude (gsd-verifier)_

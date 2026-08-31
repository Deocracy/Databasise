---
phase: 01-machine-core
verified: 2026-08-30T00:00:00Z
status: gaps_found
score: 2/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "A wiring arm containing an `opaque` node writes `quarantined` and cannot reach `shared` KV (ROADMAP Success Criterion 4 / MACH-08)"
    status: failed
    reason: >
      The deny-by-default containment/blast-radius enforcement (`runner/scheduler.py:227,240`
      and `validator/blast_radius.py:48`) derives `execution_mode`, the capability-scoped store
      view, and the blast-radius refusal from the WIRING NODE's self-declared `effects`/`kind`
      (`WiringNode.effects`, `WiringNode.kind`) — not from the registry's own `Part.effects` /
      `Part.kind`. `validator/parse.py:parse_wiring` never cross-checks the two; `WiringNode.effects`
      defaults to `[]` when the wiring simply omits it (`databasise/parts/schema.py:131`). A
      component registered with `writes_artifact`/`calls_llm`/`net`/`fs` in its Part row can be
      wired with those effects omitted or narrowed on the `WiringNode`, and both the placement
      refusal (D-08) and the blast-radius refusal (D-02) are silently bypassed — no violation, no
      exception, no trace of the bypass. This is the exact property Falsifier 2 depends on and the
      exact anti-pattern the project's own vocabulary (validator/cycles.py: "a hostile or merely
      large wiring could declare...") already treats a wiring document as capable of. Independently
      confirmed by reading scheduler.py, blast_radius.py, parse.py and schema.py directly — matches
      01-REVIEW.md's CR-01 finding. `registry_artifact/write_path.py`'s "second enforcement point"
      (D-02) does not close this either: `write_artifact(scope=..., effective_depth=...)` takes
      `scope` as a caller-supplied argument, re-running the same predicate on caller-supplied
      values rather than a Part-derived one. The literal ROADMAP test (`test_criterion_4_...`)
      passes only because its fixture wiring is honest (`WiringNode.effects` matches
      `Part.effects` exactly) — it does not exercise the mismatch case, so the passing test suite
      does not surface this gap.
    artifacts:
      - path: "databasise/runner/scheduler.py"
        issue: "`_run_node` (line ~227) derives `execution_mode` and the capability-scoped stores view from `node.effects`/`node.kind` instead of `parsed.parts[node_id].effects`/`.kind`"
      - path: "databasise/validator/blast_radius.py"
        issue: "`blast_radius_violations` (line 48) gates the whole rule on `node.effects` (WiringNode) instead of `parsed.parts[node_id].effects` (registry Part)"
      - path: "databasise/validator/parse.py"
        issue: "`parse_wiring` never validates that `WiringNode.effects`/`.kind` is a subset of (or equal to) the resolved `Part.effects`/`.kind`"
    missing:
      - "Derive `execution_mode`, the capability-scoped store view, and the blast-radius predicate from `parsed.parts[node_id].effects`/`.kind` (the registry's trusted declaration), not from `parsed.nodes[node_id].effects`/`.kind`."
      - "Or: add an explicit `parse_wiring` check that `set(node.effects) <= set(part.effects)` (and `node.kind` is consistent with `part.kind`), accumulating a violation when a wiring's declaration diverges from the registry's — never silently letting the wiring's claim override the registry's."
      - "A regression test that registers a Part with real capabilities (e.g. `writes_artifact`, scope `shared`, structural_depth `opaque`) and wires a node for it with `effects: []` (or `effects: ['writes_artifact']` but no matching kind/depth), asserting the placement refusal / blast-radius refusal still fires."
  - truth: "The runner executes a wiring graph to completion under structured concurrency, metering spend at each node's declared boundary (ROADMAP Success Criterion 2 / MACH-05)"
    status: failed
    reason: >
      Structured concurrency (asyncio.TaskGroup + graphlib.TopologicalSorter) and the intra-node
      concurrency mechanism (per-node asyncio.Semaphore, D-09) ARE real and verified. "Metering
      spend at each node's declared boundary" is NOT: `runner/scheduler.py`'s successful-dispatch
      path (lines 376-391) hardcodes every node's `budget_state="within_budget"`,
      `realised_budget_share=1.0`, and `tokens=TokenAccounting()` (all-zero) regardless of the
      node's real declared spend. `runner/budget.py`'s `meter()` (which reads a node's declared
      calling effects and its real `TokenAccounting`) is fully built and unit-tested but is never
      imported or called from `scheduler.py` — confirmed by grepping scheduler.py's own import
      list, which names `runner.trace` but not `runner.budget` or `runner.guards`. Concretely:
      `parts_core/fake_llm_caller.py`'s body computes a real, non-zero `TokenAccounting` (prompt
      tokens, completion tokens, `counted_by="fixture-tokenizer@1"`) and returns it as part of its
      output dict, but the scheduler's trace-stamping code never reads `output["tokens"]` — the
      real value is silently discarded and replaced with the zero placeholder. This matches
      01-REVIEW.md's IN-01 finding (logged there as Info/non-blocking, but the phase's own wave-4
      plan title, "runner completion: per-node semaphore, exact budget metering, full RIG §TR.1
      run record," and ROADMAP Success Criterion 2's literal text both claim metering is real).
      `tests/test_phase_success_criteria.py`'s criterion-2 test only asserts the field is present
      and in `[0, 1]`, which a hardcoded `1.0` also satisfies, so the passing suite does not catch
      this.
    artifacts:
      - path: "databasise/runner/scheduler.py"
        issue: "Successful-dispatch NodeTrace construction (~line 380-391) hardcodes budget_state/realised_budget_share/tokens instead of calling runner/budget.py's meter()"
      - path: "databasise/runner/budget.py"
        issue: "meter()/split_allowance()/apportion() are built and tested but have zero call sites outside their own test file"
      - path: "databasise/runner/guards.py"
        issue: "evaluate_guards() is built and tested but has zero call sites outside its own test file; scheduler.py hardcodes guards_fired=[]"
    missing:
      - "Wire `runner/budget.py`'s `meter()` into `_run_node`/`run_wiring`'s success path, reading the node's declared allowance (from wiring config) and the body's real `TokenAccounting` output, and stamp the real `BudgetToken.state`/`realised_budget_share` onto `NodeTrace` instead of the hardcoded constants."
      - "A regression test asserting a node whose body returns non-zero `TokenAccounting` (e.g. fake_llm_caller) produces a `NodeTrace.tokens` that matches the body's real output, not zeros."
deferred: []
human_verification: []
---

# Phase 01: Machine Core Verification Report

**Phase Goal:** The machine executes a wiring graph over embedded stores with stable component identity, inside one local process tree
**Verified:** 2026-08-30T00:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Owner installs Databasise as a library, starts with no external DB server/container — Cozo (graph), Faiss (vector), SQLite (KV/lexical/registry/ledger) embedded in one process tree | ✓ VERIFIED | `databasise/pyproject.toml` declares exactly 4 runtime deps (`pycozo`, `faiss-cpu`, `rfc8785`, `pydantic`), none a DB-server client; `tests/test_embed_startup.py` Tests 1-8 prove no child process, no new thread, no new listening socket, no host/port/dsn constructor params, no silent fallback on store-load failure — all pass. `stores/graph.py` (Cozo, file-backed), `stores/vector.py` (Faiss, dir-backed), `stores/kv.py`/`lexical.py`/`registry_artifact/index.py`/`ledger/ledger.py` (all stdlib `sqlite3`, file-backed) confirmed by direct read. |
| 2 | Runner executes a wiring graph to completion under structured concurrency, metering spend at each node's declared boundary, with the intra-node concurrency mechanism decided and written down | ✗ FAILED | Structured concurrency (`asyncio.TaskGroup` + `graphlib.TopologicalSorter`) and the intra-node mechanism (per-node `asyncio.Semaphore`, sized from `config.max_concurrency`, D-09) are real and verified in `runner/scheduler.py`. **"Metering spend at each node's declared boundary" is not real**: every node's trace hardcodes `budget_state="within_budget"`, `realised_budget_share=1.0`, `tokens=TokenAccounting()` (zero) regardless of actual spend; `runner/budget.py`'s `meter()` is unit-tested but never called from `scheduler.py`. See Gaps. |
| 3 | The same component wired twice with byte-identical config resolves to one instance identity and one cache partition; a changed config byte yields a different `config_hash`/partition; a wiring node id is never usable as an identity | ✓ VERIFIED | `tests/test_phase_success_criteria.py::test_criterion_3_identity_stability_and_separation` (passing) proves both branches share one `instance_hash`/`cache_partition_key`, a one-byte config mutation changes only the mutated position's identity, and `inspect.signature` on `instance_hash`/`cache_partition_key` structurally excludes `node_id`. `identity/canon.py`'s RFC 8785 canonicalisation and `identity/instance.py`'s hash composition read as correct (also independently confirmed by 01-REVIEW.md, no findings against this module). |
| 4 | A wiring arm containing an `opaque` node writes `quarantined` and cannot reach `shared` KV; per-part graph and vector namespaces are visibly separate after a run | ✗ FAILED | The literal test (`test_criterion_4_...`) passes, but only because its fixture wiring is *honest* — its `WiringNode.effects` matches its `Part.effects` exactly. The underlying enforcement (`scheduler.py`'s placement/capability-scoping and `validator/blast_radius.py`'s refusal) reads the wiring node's own self-declared `effects`/`kind`, never cross-checked against the registry `Part`'s trusted `effects`/`kind`. A wiring that under-declares a node's effects (or `WiringNode.effects` simply omitted — defaults to `[]`) bypasses both the placement refusal and the blast-radius refusal with no violation, no exception. See Gaps (matches 01-REVIEW.md CR-01, independently confirmed by reading source). |

**Score:** 2/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/pyproject.toml` | 4 runtime deps, no DB client | ✓ VERIFIED | Exact match |
| `databasise/identity/canon.py`, `instance.py`, `env.py` | RFC 8785 config_hash, instance_hash, environment_hash | ✓ VERIFIED | Read directly; tests pass |
| `databasise/parts/registry.py`, `schema.py` | name@version dict resolution, Part/WiringNode shapes | ✓ VERIFIED | No dynamic-import fallback confirmed; 4 executable + 3 declaration-only parts present |
| `databasise/validator/parse.py`, `cycles.py`, `depth.py`, `blast_radius.py`, `execution_mode.py` | one-pass accumulation, SCC-condensed depth, blast-radius rule, placement derivation | ⚠️ WIRED but SOURCE-COMPROMISED | Present, wired into `run_wiring`, individually correct as pure functions — but fed the wrong (untrusted) input at the one live call site (see Gap 1) |
| `databasise/runner/scheduler.py`, `trace.py`, `budget.py`, `guards.py` | structured-concurrency dispatch, RIG §TR.1 trace fields, budget metering, guards | ⚠️ PARTIAL | `scheduler.py`/`trace.py` real and wired; `budget.py`/`guards.py` built, unit-tested, **not called** from the live path (see Gap 2) |
| `databasise/stores/*.py` | 5 embedded store adapters, shared lifecycle contract | ✓ VERIFIED | `initialize`/`finalize`/`index_done_callback`/`drop_pending_index_ops`/`drop` confirmed across kv/lexical/vector/graph/blob; frozen-Cozo-bug regression suite passes |
| `databasise/registry_artifact/index.py`, `write_path.py`, `databasise/ledger/ledger.py` | 3-scope registry, second blast-radius call site, append-only ledger | ⚠️ PARTIAL | Registry/ledger correct and append-only (confirmed by direct read + passing tests); second blast-radius call site re-runs the same predicate but on caller-supplied `scope`, not a Part-derived one — same class of gap as Gap 1 |
| `databasise/tools/check_import_boundary.py`, `tests/test_import_boundary.py`, `test_embed_startup.py`, `test_phase_success_criteria.py` | runnable v1-boundary checker, acceptance suite driving the public entry point | ✓ VERIFIED | AST-based checker (not text-scan), self-exclusion proven non-vacuous, all 4 acceptance criteria tests present and running through `databasise.run_wiring` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `databasise/__init__.py:run_wiring` | `validator.parse_wiring` → `runner.scheduler.run_wiring` → `runner.trace.RunRecord` | direct call chain | ✓ WIRED | Confirmed by direct read of `__init__.py` |
| `identity.env.environment_hash()` | `identity.canon.config_hash()` | `identity.instance.instance_hash()` | ✓ WIRED | Confirmed in `scheduler.py::_resolve_identities` |
| `node.effects`/`node.kind` (WiringNode, untrusted) | `execution_mode` derivation + capability-scoped stores + blast-radius refusal | `scheduler.py:227,240`, `blast_radius.py:48` | ✗ WRONG SOURCE | Should read `parsed.parts[node_id].effects`/`.kind` (registry Part, trusted) — see Gap 1 |
| node body's real `TokenAccounting` output | `NodeTrace.tokens`/`budget_state`/`realised_budget_share` | `runner/budget.py::meter()` | ✗ NOT WIRED | `meter()` has zero call sites in `scheduler.py`; trace fields are hardcoded constants — see Gap 2 |
| `blob_store.put()` content hash | `registry_artifact.index` row | content-addressed join | ✓ WIRED | Confirmed in `write_path.py::write_artifact` |
| ledger `INSERT` | `active_pointer()` | `SELECT ... ORDER BY id DESC LIMIT 1` | ✓ WIRED | Confirmed by direct read of `ledger/ledger.py`; append-only, no UPDATE/DELETE |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full phase test suite | `cd databasise && uv run pytest -q` | `209 passed in 18.50s` | ✓ PASS |
| CR-01 claim (blast-radius/execution_mode source) | direct read of `runner/scheduler.py:227,240`, `validator/blast_radius.py:48`, `validator/parse.py`, `parts/schema.py` | confirmed: derives from `WiringNode.effects`/`.kind`, no cross-check against `Part.effects`/`.kind` exists | ✓ CONFIRMS GAP 1 |
| Budget metering claim | grep `runner.budget` / `runner.guards` imports in `scheduler.py`; read `fake_llm_caller.py` body vs. trace-stamping code | confirmed: no import, real `TokenAccounting` computed by a reference part is discarded before the trace is stamped | ✓ CONFIRMS GAP 2 |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|-------------|--------|----------|
| EMBED-01 | 01-01, 01-05, 01-06, 01-09 | Single self-contained process tree, embedded Cozo/Faiss/SQLite, no server, no Docker | ✓ SATISFIED | See Truth 1 |
| MACH-05 | 01-01, 01-02, 01-03, 01-08, 01-09 | Structured-concurrency runner, metering spend at declared boundary, full RIG §TR.1 field set | ✗ BLOCKED | Structured concurrency real; metering not wired live (Gap 2) |
| MACH-06 | 01-01, 01-02, 01-04, 01-07, 01-09 | name@version + config_hash identity, content-addressed artifact registry, instance identity never a node id | ✓ SATISFIED | See Truth 3 |
| MACH-08 | 01-02, 01-03, 01-05, 01-06, 01-07, 01-09 | KV shared-scope rule, opaque→quarantined, per-part namespaces, artifact sharing iff recipe-hash-identical | ✗ BLOCKED | Namespace separation real; opaque→quarantined containment not machine-enforced against a misdeclaring wiring (Gap 1) |

No orphaned requirements: REQUIREMENTS.md maps only these four IDs to Phase 1 (MACH-07 is Phase 7; all others are later phases).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `databasise/runner/scheduler.py` | 227, 240 | Trusts wiring's self-declared `effects`/`kind` over registry `Part`'s | 🛑 Blocker | Bypasses deny-by-default containment (Gap 1) |
| `databasise/validator/blast_radius.py` | 48 | Same — gates on `WiringNode.effects` | 🛑 Blocker | Same as above |
| `databasise/runner/scheduler.py` | 376-391 | Hardcoded `budget_state`/`realised_budget_share`/`tokens` instead of calling `budget.meter()` | 🛑 Blocker | "Metering spend" success criterion not actually true (Gap 2) |
| `databasise/parts_core/__init__.py` | 42-46 | `CapabilityScopedStores.require()` returns `None` on a declared-but-unwired store instead of raising | ⚠️ Warning | Confusing downstream `AttributeError` instead of a named refusal (01-REVIEW.md WR-01, not gating) |
| `databasise/stores/vector.py` | 208-231 | Two-file commit (index + sidecar) not atomic as a pair | ⚠️ Warning | Crash window leaves a mismatched pair (01-REVIEW.md WR-02, not gating) |
| `databasise/stores/kv.py`, `lexical.py`, `vector.py`, `ledger/ledger.py`, `registry_artifact/index.py` | various | Synchronous I/O inline in `async def` (inconsistent with `stores/graph.py`'s own `run_in_executor` rationale) | ⚠️ Warning | Can stall sibling tasks in the same TaskGroup batch (01-REVIEW.md WR-03, not gating) |
| `databasise/runner/scheduler.py` | 205-214 | `int(config.get("max_concurrency", 1))` raises bare `ValueError` for non-numeric input instead of the documented `InvalidMaxConcurrencyError` | ⚠️ Warning | Contract-inconsistent refusal message (01-REVIEW.md WR-04, not gating) |
| `databasise/runner/trace.py` | 44, 79-80 | `TIER_PLACEHOLDER = "T3"` | ℹ️ Info | Explicitly documented sentinel, scoped to Phase 2's evidence-tier mechanism — not a hidden debt marker, no action needed this phase |

No unreferenced `TBD`/`FIXME`/`XXX` markers found in any file modified by this phase.

### Gaps Summary

Two BLOCKER gaps, both traced directly to source (not SUMMARY.md claims), both independently confirmed against 01-REVIEW.md's own findings:

1. **Containment enforcement trusts the untrusted input (CR-01).** The whole point of CONTRACT §3's deny-by-default rule is that a wiring document cannot grant itself capabilities beyond what its registered `Part` actually declares. Right now it can: `runner/scheduler.py` and `validator/blast_radius.py` both derive placement/capability-scoping/blast-radius from the wiring node's own self-declared `effects`/`kind`, never cross-checked against the registry `Part`'s trusted declaration. Success Criterion 4's literal test passes only because its fixture wiring happens to be honest about its own effects — the invariant the criterion is meant to prove (opaque containment holds even when it matters) is not actually machine-enforced.

2. **Budget metering is not live.** Success Criterion 2 states the runner meters spend at each node's declared boundary. It doesn't: every node's trace stamps a hardcoded `within_budget`/`1.0`/zero-tokens regardless of real spend, and `runner/budget.py`'s tested `meter()` has no call site in the live scheduler path. A reference part (`fake_llm_caller`) computes real, non-zero token accounting that the scheduler silently discards before stamping the trace.

Both gaps are narrow and mechanical to close (the fix for Gap 1 is a one-line source swap per the review's own sketch; Gap 2 needs `meter()` wired into `_run_node`'s success path) — neither requires new architecture. Recommend routing back through `/gsd-plan-phase --gaps` for a closure plan before Phase 2 begins, since Phase 2's Falsifier 2 gate presumes exactly the machine-computed (not self-declared) property Gap 1 currently violates.

---

_Verified: 2026-08-30T00:00:00Z_
_Verifier: Claude (gsd-verifier)_

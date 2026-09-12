---
phase: 01-machine-core
fixed_at: 2026-08-31T00:00:00Z
review_path: .planning/phases/01-machine-core/01-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 01-machine-core: Code Review Fix Report

**Fixed at:** 2026-08-31T00:00:00Z
**Source review:** `.planning/phases/01-machine-core/01-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope (Critical + Warning, per `fix_scope: critical_warning`): 5 (CR-01, WR-01, WR-02, WR-03, WR-04)
- Fixed: 5
- Skipped: 0
- Info findings (IN-01, IN-02, IN-03) were explicitly out of scope for this run and were not touched.

**Verification:** every fix below was applied and verified inside an isolated git worktree
(`gsd-reviewfix/01-835564`, per `workflow.use_worktrees`), then fast-forwarded into the main
checkout's `main` branch via `git merge --ff-only`. The final `217 passed` run reported under
CR-01 through WR-04 below was re-run a second time directly in the main checkout's own venv
(`/home/chris/coding/Databasise-2.0-fully-agnostic-system/databasise/.venv`) after the
fast-forward, confirming the numbers are reproducible from the tree a reader now sees — not only
from the (now-removed) worktree.

## Fixed Issues

### CR-01: Deny-by-default containment and blast-radius checks trusted the wiring's self-declared effects/kind, not the registry's

**Files modified:** `databasise/runner/scheduler.py`, `databasise/validator/blast_radius.py`, `databasise/validator/errors.py`, `databasise/validator/parse.py`, `databasise/tests/runner/test_scheduler.py`, `databasise/tests/validator/test_cycles_and_depth.py`, `databasise/tests/validator/test_taint_conformance.py`
**Commit:** `3b05d54`
**Applied fix:**
- `runner/scheduler.py`'s `_run_node` now derives `execution_mode` and builds the capability-scoped store view from `parsed.parts[node_id].effects`/`.kind` (the registry's resolved `Part`) instead of `parsed.nodes[node_id].effects`/`.kind` (the wiring's own, untrusted, self-declared fields) — exactly the two call sites CR-01 named.
- `validator/blast_radius.py`'s `blast_radius_violations` now iterates `parsed.parts.items()` and gates on `part.effects` (not `node.effects`), closing the same bypass for the blast-radius rule.
- `validator/parse.py`'s `parse_wiring` adds a new consistency check (`CODE_EFFECTS_EXCEED_PART`, `validator/errors.py`): a `WiringNode`'s declared `effects` must be a subset of its resolved `Part`'s declared `effects` — a wiring MAY declare fewer effects than its Part is capable of (to prove it exercises only a subset), but never more. This is a document-validation-layer consistency check, not the containment enforcement itself — the runner and blast-radius rule are unaffected by what the wiring declares regardless of this check, since both now read `Part` directly.
- **Deliberately scoped to `effects` only, not `kind`:** the review's fix text asked for an "effects/kind" consistency check. `WiringNode.kind` is a plain, unconstrained `str` (per `parts/schema.py`'s own docstring: "a later plan is where the fanout/join/fixpoint/subgraph/opaque structural-kind dispatch actually gets built"), and this codebase's own test suite establishes `WiringNode.kind` as a distinct "wiring-position kind" that is not expected to equal `Part.kind` — `tests/validator/test_taint_conformance.py`'s entire 12-case table uses `WiringNode.kind="primitive"` uniformly regardless of each fixture Part's real `kind` (`"stage"`/`"opaque"`/`"evidence"`), and `tests/test_phase_success_criteria.py`'s own module docstring explicitly documents this as deliberate ("its *wiring-position* kind stays hostable, since Phase 1's runner does not yet build the real subprocess containment..."). A strict kind-consistency check would have broken this entire, intentional, pre-existing test convention. Since `execution_mode` is now sourced from `part.kind` directly (never `node.kind`), the security property CR-01 exists to prove already holds regardless of what a wiring's `kind` field claims — a `kind` consistency check would be pure hygiene, not closing any remaining bypass, so it was left out rather than forced through against the grain of the existing, deliberate test convention.
- **Test fix required by the new `effects` check:** `tests/validator/test_taint_conformance.py::test_transient_effects_added_to_case_6_change_nothing` previously added a transient effect (`writes_kv`/etc.) to a wiring node's `effects` **without** adding it to the resolved Part's `effects` — under the new consistency check this is now a `CODE_EFFECTS_EXCEED_PART` violation, so `parse_wiring`'s `report.ok` becomes `False` and the blast-radius pass (which the test asserts on) never runs. This encoded the old, no-longer-correct assumption that a wiring's declared effects need not match its Part's. Updated the test to build a per-iteration `Part` fixture carrying the same added transient effect, preserving the original intent (transient effects never trigger a blast-radius violation) while being consistent with the new rule.
- **New regression tests added** (fail without the fix, pass with it):
  - `tests/runner/test_scheduler.py::test_11_placement_is_sourced_from_the_parts_effects_not_the_wirings_underdeclared_ones` — a wiring node claims `effects=[]` while its Part declares `net`; asserts the run is still refused (`long-lived-service`, D-08's unimplemented placement) rather than silently hosted in-process.
  - `tests/runner/test_scheduler.py::test_12_capability_scoped_store_view_is_sourced_from_the_parts_effects_not_the_wirings` — a wiring node claims `effects=[]` while its Part declares `writes_kv`; asserts `ctx.stores["kv"]` still resolves (sourced from the Part, not the wiring).
  - `tests/validator/test_cycles_and_depth.py::test_wiring_node_declaring_an_effect_its_part_does_not_is_refused` and `::test_wiring_node_declaring_a_narrower_effects_set_than_its_part_is_permitted` — cover the new `parse_wiring` consistency check in both directions (over-declaration refused, under-declaration permitted).

### WR-01: `CapabilityScopedStores.require()` returned `None` instead of refusing when a declared effect's backing store isn't wired

**Files modified:** `databasise/parts_core/__init__.py`, `databasise/tests/parts/test_reference_parts.py`
**Commit:** `55fbcc0`
**Applied fix:** Added a purpose-built `StoreNotWiredError(effect, store_key)` (per the review's suggested fix) and changed `require()` to `self._raw_stores[store_key]` (a `KeyError` caught and re-raised as `StoreNotWiredError`) instead of `self._raw_stores.get(store_key)`. Added `test_7_a_declared_effect_with_no_backing_store_wired_is_a_named_refusal_not_none`, which fails (returns `None`, no exception) without the fix.

### WR-02: `FaissVectorStore._persist`'s two-file commit was not atomic as a pair

**Files modified:** `databasise/stores/vector.py`, `databasise/tests/stores/test_vector.py`
**Commit:** `36a899a`
**Applied fix:** Chose option (c) from the review's three suggested fixes — a checksum cross-validated at open time — as the smallest change that closes the actual gap without redesigning the commit protocol. `_persist` now writes a SHA-256 `index_checksum` of the index file into the sidecar; `__init__` recomputes that checksum against whatever index file is actually on disk and raises a new `VectorStoreCorruptedError` (naming the path, expected, and actual checksum) rather than silently loading a mismatched pair. The crash window between the two `os.replace` calls still exists (as the review noted, closing it fully would require a heavier staging-directory or symlink scheme) — what changed is that a pair it produces is now detected and refused at the next open instead of silently used. Added `test_a_half_committed_pair_is_detected_and_refused_at_next_open`, which fails (silently loads the mismatched pair) without the fix.

### WR-03: Blocking, synchronous I/O ran directly inside `async def` store methods

**Files modified:** `databasise/stores/vector.py`, `databasise/tests/stores/test_vector.py`, `databasise/stores/kv.py`, `databasise/stores/lexical.py`, `databasise/ledger/ledger.py`, `databasise/registry_artifact/index.py`
**Commit:** `6ec39b0`
**Applied fix:** Split across the two alternatives the review's own Fix section sanctioned as equally valid ("Either dispatch ... or explicitly document ... why the other four stores are exempt"):
- **Code-fixed:** `stores/vector.py`'s `FaissVectorStore.index_done_callback` and `delete_by_ids` now dispatch the CPU/IO-bound work (`np.vstack`, `faiss.add_with_ids`/`remove_ids`, `faiss.clone_index`, and `_persist`'s file writes) via `loop.run_in_executor(None, ...)`, mirroring `stores/graph.py`'s existing, already-adopted pattern exactly. This is the file the reviewer flagged as the most concerning ("not obviously cheap at scale"), and mechanically the safest to fix: unlike `sqlite3.Connection`, Faiss/numpy objects have no same-thread restriction, so no connection-safety redesign was needed. Instance-attribute reassignment (`self._index`, `self._entries`, `self._next_int_id`) was deliberately kept on the event-loop thread (assigned only after the `run_in_executor` call returns), never inside the worker-thread closure, so a concurrent `query()` (which reads those attributes with no lock of its own) never races a worker-thread mutation. Added `test_flush_dispatch_does_not_block_the_event_loop`, mirroring `tests/stores/test_graph.py`'s existing `test_query_dispatch_does_not_block_the_event_loop` pattern exactly.
- **Documented (not code-changed), with rationale, for the other four files:** `stores/kv.py`, `stores/lexical.py`, `ledger/ledger.py`, `registry_artifact/index.py`. Each now carries a "WR-03, deliberate exception" docstring paragraph explaining why:
  - `kv.py`/`lexical.py`: both are genuinely `async def` and reachable from the live runner path, but `sqlite3.Connection` objects are usable only from the thread that created them by default — dispatching via the default executor's thread pool would first require reopening every connection with `check_same_thread=False` and re-verifying cross-thread access is actually safe under this project's single-writer discipline (the underlying C library's thread-safety mode is not pinned by this codebase). That is real surgery with real correctness risk across every call site in two files, not a one-line change, and could not be verified safe within this fix pass's scope — attempting it "blindly" risked introducing a subtle, hard-to-catch threading bug in exchange for a speed-up the reviewer themselves conceded is likely unnecessary ("SQLite writes under WAL are typically fast"). Deferred rather than half-applied, per this task's own instruction to skip rather than half-apply an unsafe fix.
  - `ledger/ledger.py`: every method is plain synchronous `def` (not `async def` at all) — there is no event-loop-blocking concern to fix today, since the module's own "Scope fence" note already establishes nothing in the live Phase 1 runner calls `append()`.
  - `registry_artifact/index.py`: also plain synchronous `def`, invoked from `write_path.py`'s plain-sync `write_artifact()`, which IS reachable from an async node body. A real fix here would mean either converting the whole public API to `async def` (a breaking signature change for every caller, sync and async, far beyond this finding's scope) or offloading only at the one current call site — both larger surgery than this pass, deferred given Phase 1's own write-path call volume (one artifact write per node, not a bulk flush).

### WR-04: `max_concurrency` validation raised an uncaught `ValueError` for non-numeric config instead of the documented refusal

**Files modified:** `databasise/runner/scheduler.py`, `databasise/tests/runner/test_scheduler.py`
**Commit:** `a7d6c95`
**Applied fix:** Applied the review's exact suggested fix: wrapped `int(config.get("max_concurrency", 1))` in `try`/`except (TypeError, ValueError)`, re-raising `InvalidMaxConcurrencyError(node_id, raw)` (`from None`). Widened `InvalidMaxConcurrencyError.__init__`'s `value` type hint from `int` to `Any` to reflect that a non-coercible value (a string, list, dict, ...) can now reach it. Added `test_3b_max_concurrency_non_numeric_is_refused_as_invalid_max_concurrency_not_value_error`, which fails (raises a bare `ValueError` from `int(...)`, not `InvalidMaxConcurrencyError`) without the fix.

## Skipped Issues

None — all 5 in-scope findings were fixed (see WR-03's writeup above for the two files where the resolution was a documented, deliberate exception rather than a code change; this is a review-sanctioned outcome, not a skip).

## Test Suite

Full suite re-run after every commit inside the isolated worktree, and once more in the main
checkout's own venv after the fast-forward:

```
217 passed
```

(Baseline before this run's fixes: 209 passed, 1 pre-existing test — `test_transient_effects_added_to_case_6_change_nothing` — updated as documented under CR-01 above because it encoded an assumption the fix makes incorrect. Net new: 4 CR-01 regression tests, 1 WR-01 regression test, 2 WR-02/WR-03 regression tests on `vector.py`, 1 WR-04 regression test = 8 new tests; 209 + 8 = 217.)

No logic-bug findings in this batch required a `"fixed: requires human verification"` classification — every fix here is a sourcing change (read from the trusted registry field instead of the untrusted wiring field), a refusal-instead-of-`None`/bare-exception change, a checksum-detection addition, or an off-loop dispatch change, each covered by a concrete regression test that fails without the fix and passes with it.

## Orchestrator Follow-up: CR-01 Residual

Commit `973592e`, applied by the orchestrator after verifying the fixer's work.

The CR-01 fix moved the capability-scoped store view onto the registry's `Part.effects`, but one
call site in the same file still read the untrusted `WiringNode.effects`:
`runner/scheduler.py`'s D-13 resume-boundary computation
(`resumable = not (set(node.effects) & _STORE_MUTATING_EFFECTS)`).

Because `parse_wiring` deliberately permits a wiring to declare a *narrower* effects set than its
Part, a node whose wiring omits `writes_kv` while its Part declares it would be granted the KV
store (correctly, from `part.effects`), mutate it, and still be stamped `resumable=True` — the
same untrusted-field substitution CR-01 names, reaching D-13's resume boundary instead of D-08's
containment rule.

Fixed by sourcing `resumable` from `parsed.parts[node_id].effects`. `test_12` was extended with
the resume-boundary assertion; it fails against the pre-fix scheduler and passes after.

Suite after this commit: **217 passed** (no new test count — the assertion rides the existing
CR-01 fixture rather than adding a redundant one).

---

_Fixed: 2026-08-31T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

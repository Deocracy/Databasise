---
phase: 01-machine-core
reviewed: 2026-08-31T00:00:00Z
depth: standard
files_reviewed: 73
files_reviewed_list:
  - databasise/README.md
  - databasise/__init__.py
  - databasise/identity/__init__.py
  - databasise/identity/canon.py
  - databasise/identity/env.py
  - databasise/identity/instance.py
  - databasise/ledger/__init__.py
  - databasise/ledger/ledger.py
  - databasise/namespaces.py
  - databasise/parts/__init__.py
  - databasise/parts/registry.py
  - databasise/parts/schema.py
  - databasise/parts_core/__init__.py
  - databasise/parts_core/declared_only.py
  - databasise/parts_core/fake_llm_caller.py
  - databasise/parts_core/fake_retriever.py
  - databasise/parts_core/fixpoint_body.py
  - databasise/parts_core/passthrough.py
  - databasise/pyproject.toml
  - databasise/registry_artifact/__init__.py
  - databasise/registry_artifact/index.py
  - databasise/registry_artifact/write_path.py
  - databasise/runner/__init__.py
  - databasise/runner/budget.py
  - databasise/runner/guards.py
  - databasise/runner/scheduler.py
  - databasise/runner/trace.py
  - databasise/stores/__init__.py
  - databasise/stores/base.py
  - databasise/stores/blob.py
  - databasise/stores/graph.py
  - databasise/stores/kv.py
  - databasise/stores/lexical.py
  - databasise/stores/vector.py
  - databasise/tests/conftest.py
  - databasise/tests/fixtures/wiring-tracer.json
  - databasise/tests/identity/test_config_hash.py
  - databasise/tests/identity/test_instance_identity.py
  - databasise/tests/ledger/test_ledger.py
  - databasise/tests/parts/test_reference_parts.py
  - databasise/tests/parts/test_registry.py
  - databasise/tests/registry_artifact/test_index.py
  - databasise/tests/registry_artifact/test_write_path_blast_radius.py
  - databasise/tests/runner/test_budget.py
  - databasise/tests/runner/test_live_metering.py
  - databasise/tests/runner/test_run_record.py
  - databasise/tests/runner/test_scheduler.py
  - databasise/tests/stores/test_blob.py
  - databasise/tests/stores/test_graph.py
  - databasise/tests/stores/test_graph_frozen_bugs.py
  - databasise/tests/stores/test_kv.py
  - databasise/tests/stores/test_lexical.py
  - databasise/tests/stores/test_namespace_derivation.py
  - databasise/tests/stores/test_vector.py
  - databasise/tests/test_conftest_fixtures.py
  - databasise/tests/test_embed_startup.py
  - databasise/tests/test_import_boundary.py
  - databasise/tests/test_phase_success_criteria.py
  - databasise/tests/test_tracer_end_to_end.py
  - databasise/tests/test_trusted_source_invariant.py
  - databasise/tests/validator/test_blast_radius.py
  - databasise/tests/validator/test_cycles_and_depth.py
  - databasise/tests/validator/test_execution_mode.py
  - databasise/tests/validator/test_taint_conformance.py
  - databasise/tools/__init__.py
  - databasise/tools/check_import_boundary.py
  - databasise/validator/__init__.py
  - databasise/validator/blast_radius.py
  - databasise/validator/cycles.py
  - databasise/validator/depth.py
  - databasise/validator/errors.py
  - databasise/validator/execution_mode.py
  - databasise/validator/parse.py
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 01: Machine Core Code Review Report (re-review after plan 01-10)

**Reviewed:** 2026-08-31T00:00:00Z
**Depth:** standard
**Files Reviewed:** 73 (71 from the 2026-08-30 pass, re-verified lightly; 2 new files from
01-10: `tests/runner/test_live_metering.py`, `tests/test_trusted_source_invariant.py`)
**Status:** issues_found

## Summary

This is a targeted re-review after plan 01-10 wired `runner/budget.py`'s `meter()` and
`runner/guards.py`'s `evaluate_guards()` into `runner/scheduler.py`'s live dispatch path, closing
both `01-VERIFICATION.md` BLOCKER gaps (Gap 1's under-declaring blast-radius bypass and Gap 2's
unwired budget metering). Direct reading confirms the two claims this plan's summary makes about
its own security-relevant sourcing: `runner/scheduler.py`'s `_run_node` derives
`execution_mode`, the capability-scoped store view, `resumable`, and now `meter()`'s spend
computation all from `parsed.parts[node_id].effects`/`.kind` (the registry's trusted `Part`),
never from `parsed.nodes[node_id].effects`/`.kind` (the wiring's untrusted, self-declared
fields); `validator/blast_radius.py` gates identically on `parsed.parts.items()`. The
integer-only halt comparison (`spent <= allowance`) and the `[0, 1]`-capped float-only
`realised_budget_share` both hold exactly as specified, `guards_fired` is stamped in declaration
order and is never `None`, and `FAKE_LLM_CALLER_PART`'s new `writes_kv` effect does not weaken
either the execution-mode derivation (`writes_kv` is not in `_NOT_IN_PROCESS_EFFECTS`) or the
blast-radius rule (which keys only on `writes_artifact`).

One genuine, newly introduced Critical defect was found: the same 01-10 diff that dispatches
`FaissVectorStore`'s flush off the event loop (closing the prior review's WR-03) opens an
unguarded concurrency window in which a write landing while a flush is in flight is silently
discarded rather than persisted — the diff's own new regression test proves the interleaving
point it relies on for the WR-03 fix is real, but nothing protects `self._pending` across it. The
new AST-based "trusted source" invariant test — meant to be the structural backstop against this
exact class of regression recurring — itself has a blind spot for the for-loop binding shape,
which happens to be the literal shape the original CR-01 bug used in `blast_radius.py`; a revert
in that shape would slip past the new safety net undetected. A smaller inconsistency was found in
the new `config.guards` pre-flight validation (a malformed guard entry leaks a bare `TypeError`
rather than a named refusal, the same class of gap WR-04 fixed for `max_concurrency` in this same
file but not extended to its sibling field), and the previously flagged second blast-radius call
site (`registry_artifact/write_path.py`) remains an open, un-addressed carryover from
`01-VERIFICATION.md`'s Gap-1 discussion — it was not part of 01-10's scope and was not touched.

## Critical Issues

### CR-01: `FaissVectorStore`'s off-loop flush silently drops a write that arrives while the flush is in flight

**File:** `databasise/stores/vector.py:243-293` (`index_done_callback`), `:178-211`
(`delete_by_ids`)
**Issue:**

The WR-03 fix (this diff) moved `index_done_callback`'s Faiss/numpy work onto
`loop.run_in_executor`, introducing a real `await` suspension point that did not exist before.
The diff's own new regression test proves a sibling coroutine genuinely gets to run during that
suspension:

```python
# tests/stores/test_vector.py::test_flush_dispatch_does_not_block_the_event_loop
ticker_task = asyncio.create_task(_ticker())
await store.index_done_callback()
await ticker_task
assert interleaved is True
```

But `index_done_callback` snapshots the pending buffer *before* that suspension and
unconditionally clears the live buffer *after* it, with no lock or generation check in between:

```python
pending = dict(self._pending)          # snapshot BEFORE the await

def _do_flush():
    ...  # uses the snapshot `pending`, never self._pending
    self._persist(staging, staging_entries, next_int_id)
    return staging, staging_entries, next_int_id

loop = asyncio.get_running_loop()
new_index, new_entries, new_next_int_id = await loop.run_in_executor(None, _do_flush)
self._index = new_index
self._entries = new_entries
self._next_int_id = new_next_int_id
self._pending.clear()                  # clears EVERYTHING live, not just the snapshot
```

Concretely: if a second coroutine calls `store.upsert(["b"], [...])` while the first
coroutine's `index_done_callback()` is suspended in `run_in_executor`, `self._pending["b"]` is
added to the *live* dict during the suspension. `"b"` was never part of `pending` (the snapshot),
so it is never flushed into the returned `staging`/`staging_entries`. When the flush resumes and
reaches `self._pending.clear()`, `"b"` is wiped from the live buffer having never been persisted
anywhere — a silent, permanent data loss with no exception, no log line, and no trace of the
dropped write. This is the exact failure mode CONTEXT.md's own "raise, don't silently drop" house
style (quoted verbatim in this same module's docstring) exists to prevent.

A second, related hazard: `delete_by_ids` (also dispatched off-loop by this same diff) and
`index_done_callback` both snapshot `self._index`/`self._entries` *before* dispatching to the
executor and both unconditionally reassign `self._index`/`self._entries` *after* their own
executor call returns, with no mutual exclusion between them. Two such calls in flight
concurrently on the same store instance (e.g. one node deleting while a sibling node's write
triggers a flush) race on a last-writer-wins basis — whichever finishes second silently discards
whatever the other one persisted, since both compute their staged index from the same stale
`base_index`/`base_entries` snapshot. The two calls also both write to the *same* temp-file paths
(`vector.faiss.tmp`, `vector.meta.json.tmp`) inside `_persist`, so two genuinely concurrent
flush/delete calls can interleave writes to those shared temp files from two different OS threads.

**Currently unreachable via the live scheduler path** — `databasise/__init__.py`'s composer wires
only `"kv"` into `ctx.stores`, so no part body can reach `FaissVectorStore` today. That is a
mitigating fact about today's blast radius, not a reason to treat the defect as hypothetical: it
is a real, demonstrated bug in shipped store code (proven by the diff's own test), and the vector
store's own docstring explicitly frames its off-loop dispatch as being *for* exactly the
concurrent-sibling-node scenario ("the runner's structured concurrency ... can genuinely have
sibling nodes in flight in the same batch") that this defect breaks.

**Fix:** Give `FaissVectorStore` an `asyncio.Lock` guarding the read-modify-write sequence across
`upsert`/`delete_by_ids`/`index_done_callback` (cheap, since these are rare per-node calls, not a
hot path), or re-diff the pending buffer against what changed during the flush instead of an
unconditional `.clear()` — e.g. `self._pending = {k: v for k, v in self._pending.items() if k not
in pending}` so only what was actually included in the flushed snapshot is removed, never
anything added afterward.

## Warnings

### WR-01: The new AST-based "trusted source" invariant test does not catch the for-loop binding shape — the literal shape of the original CR-01 bug

**File:** `databasise/tests/test_trusted_source_invariant.py:67-113`
**Issue:** `_wiring_node_bound_names` only records a name bound by a plain `ast.Assign` whose
right-hand side is exactly a `parsed.nodes[node_id]` subscript (`node = parsed.nodes[node_id]`).
It does not record a name bound by a `for` loop's target
(`for node_id, node in parsed.nodes.items():`) — and that for-loop shape is precisely how the
*original*, pre-fix `blast_radius_violations` read the wiring's untrusted field (quoted verbatim
in `01-REVIEW.md`'s own CR-01 finding: `for node_id, node in parsed.nodes.items(): if
"writes_artifact" not in node.effects:`).

Verified directly: running this test's own `_wiring_node_bound_names`/`_flagged_attribute_reads`
logic against a reconstruction of that exact original for-loop shape returns zero bound names and
zero findings — the check would pass clean over a module that had silently regressed back to
reading the wiring's own `effects` inside a `for ... in parsed.nodes.items():` loop, which is
arguably the more natural (and historically the actually-used) way to iterate `parsed.nodes` in
this codebase, more so than the single-name `assign`-then-attribute shape the test does catch (the
shape `runner/scheduler.py`'s own `_run_node` happens to use for `part = parsed.parts[node_id]`).

This matters specifically because `01-10-SUMMARY.md`'s own stated purpose for this test is "the
exact failure class that let the `resumable` residual survive the first CR-01 fix pass until a
later manual inspection caught it" — i.e., this test's entire reason to exist is to catch a
silent, easy-to-miss reintroduction of the untrusted-field read. It currently cannot catch the one
reintroduction shape most likely to occur in `validator/blast_radius.py`, the very module whose
historical bug it is modeled on.

**Fix:** Extend `_wiring_node_bound_names` to also record `for`-loop targets bound from
`parsed.nodes.items()` (an `ast.For` whose `.iter` is `parsed.nodes.items()` and whose `.target`
is an `ast.Tuple` of two `ast.Name`s — record the second). Add a regression case (mirroring the
existing `test_the_check_does_not_trip_on_prose_describing_the_rule`) that constructs the for-loop
shape as a temp fixture module and asserts the check flags it.

### WR-02: `_validated_guards` lets a malformed `config.guards` entry leak a bare `TypeError` instead of the module's own named refusal

**File:** `databasise/runner/scheduler.py:297-306`
**Issue:**

```python
def _validated_guards(node_id: str, config: dict[str, Any] | None) -> list[GuardDeclaration]:
    raw_guards = (config or {}).get("guards") or []
    return [declare_guard(**entry) for entry in raw_guards]
```

`declare_guard(name, evaluating_node, value_when_not_fired, granularity)` only guards against an
inadmissible `granularity` value (raising `GuardDeclarationError`); a guard entry dict that is
missing a required key (e.g. `{"name": "g", "granularity": "per-query"}`, omitting
`evaluating_node`/`value_when_not_fired`) or carries an unexpected key raises a bare
`TypeError: declare_guard() missing N required positional argument(s): ...` from the `**entry`
unpacking, not `GuardDeclarationError`. This is the identical defect class WR-04 fixed for
`config.max_concurrency` in this exact same file two commits earlier (a bare built-in exception
leaking instead of a named, actionable refusal naming the offending node), applied to
`max_concurrency` and `token_allowance` but not extended to `config.guards`, its sibling
pre-flight-validated field introduced in this same diff.

**Fix:** Wrap the `declare_guard(**entry)` call and re-raise a named error on `TypeError`:

```python
def _validated_guards(node_id: str, config: dict[str, Any] | None) -> list[GuardDeclaration]:
    raw_guards = (config or {}).get("guards") or []
    declared = []
    for entry in raw_guards:
        try:
            declared.append(declare_guard(**entry))
        except TypeError as exc:
            raise GuardDeclarationError(entry.get("name", "<unnamed>"), entry) from exc
    return declared
```

### WR-03 (carryover, not fixed by 01-10): `registry_artifact/write_path.py`'s second blast-radius call site still takes `scope`/`effective_depth` as plain caller-supplied arguments

**File:** `databasise/registry_artifact/write_path.py:49-70`
**Issue:** `01-VERIFICATION.md`'s Gap 1 explicitly named this file as not closed by the CR-01
fix: `write_artifact(scope=..., effective_depth=...)` still constructs an ad hoc single-node
`WiringNode`/`Part` pair from caller-supplied `scope` (never a resolved, registry-trusted
`Part.artifact_scope`) and a caller-supplied `effective_depth` (never the runner's own computed
depth for a real node), then re-runs `blast_radius_violations` against that fabricated pair. The
CR-01 fix commits (`3b05d54`, and this plan's `973592e`/01-10 work) touched
`runner/scheduler.py`, `validator/blast_radius.py`, and `validator/parse.py`, but never this
file — it was not in 01-10's scope and remains exactly as `01-VERIFICATION.md` described it. This
is not a regression from 01-10, but it is a real, still-open gap directly adjacent to this
review's focus area (the trusted-source enforcement paths) and was never re-verified or closed.
**Fix:** Out of this review's immediate scope to design, but flagging so it is not lost: derive
`scope`/`effective_depth` from a real resolved `Part` and the runner's own computed depth map at
the one real call site that exists (rather than accepting them as free-form keyword arguments any
caller can supply), or explicitly document why a caller-supplied value is considered trustworthy
at this call site (e.g. because every current caller is itself gated by an earlier, already-
enforced check) if that is in fact the intended design.

## Info

### IN-01: `_validated_token_allowance` accepts a negative `config.token_allowance` with no bound check, unlike its sibling `_validated_max_concurrency`

**File:** `databasise/runner/scheduler.py:281-294`
**Issue:** `_validated_max_concurrency` explicitly refuses any value `< 1` via
`InvalidMaxConcurrencyError`. `_validated_token_allowance` only guards against a value `int()`
cannot coerce at all — a wiring declaring `"token_allowance": -5` passes validation silently and
reaches `meter()`, where `spent <= allowance` is `False` for any spend, including `spent == 0`
(`0 <= -5` is `False`), so even a zero-spend node halts against a negative allowance. `runner/
budget.py`'s own `Allowance` dataclass (a sibling primitive in the same subsystem, currently
unused anywhere in the live path) explicitly rejects a negative `tokens` value via
`__post_init__`, so the "an allowance is a non-negative integer" invariant already exists
elsewhere in this codebase but is not enforced at the one place user/wiring input actually enters
it. The failure mode is safe (fails closed, as an unconditional halt, never a bypass), so this is
informational rather than a correctness defect.
**Fix:** Either reject `token_allowance < 0` explicitly (mirroring `_validated_max_concurrency`'s
own pattern, raising `InvalidTokenAllowanceError`), or, if a negative allowance is intentionally
permitted as a way to force an unconditional halt, say so in `_validated_token_allowance`'s own
docstring so a future reader does not mistake the silent acceptance for an oversight.

---

_Reviewed: 2026-08-31T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

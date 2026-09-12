---
phase: 07-promotion-rollback
reviewed: 2026-09-12T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md
  - databasise/mcp/tools.py
  - databasise/seam/engine.py
  - databasise/seam/promotion.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/tests/seam/test_dual_transport.py
  - databasise/tests/seam/test_promotion_posture.py
  - databasise/tests/seam/test_rest_transport.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 7: Promotion & Rollback — Code Review Report (Incremental: 07-04)

**Reviewed:** 2026-09-11
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

This is an incremental review of 07-04 only (commits `86ca4b3`, `214faff`, `844ccf5`, `d9a6378`),
whose sole purpose was to close the previous review's CR-01: `promote()`'s `verb` argument crashed
with a bare `ValueError` instead of refusing by name for an out-of-enum value.

**CR-01 is genuinely closed.** Verified directly against the diff and the current source:

- `Databasise.promote()` now checks `if verb not in PROMOTION_VERBS: raise
  UnrecognisedPromotionVerbError(verb=verb)` as the literal first statement of the function body —
  before `_resolve_operator_preconditions` (trace-id resolution), before `_NOT_BUILT_VERBS`/
  `_GATE_VERBS` handling, and before any `Ledger` object is constructed or touched
  (`databasise/seam/engine.py:1179-1181`).
- `PROMOTION_VERBS` is derived via `frozenset(typing.get_args(PromotionVerb))`
  (`databasise/seam/promotion.py:62`) — there is no second hand-maintained verb list anywhere to
  drift out of sync; `test_the_verb_guard_reads_the_enum_rather_than_a_second_list` pins this.
- `UnrecognisedPromotionVerbError` (`databasise/seam/refusals.py:360-377`) matches the shape of its
  siblings exactly: keyword-only `__init__(self, *, verb: Any)`, attribute stored as `self.verb`,
  class name embedded as a message prefix, and `Any`-typed (not `str`) so a JSON body delivering
  `None`, a number, or an object is still named in the refusal rather than crashing pydantic
  coercion first — the parametrized test in `test_promotion_posture.py` exercises exactly this with
  `verb=None` and `verb=""`.
- The old terminal `raise ValueError(...)` branch inside `_promote_sync` now raises the same named
  `UnrecognisedPromotionVerbError` instead, and remains reachable only by construction (a future
  seventh `PromotionVerb` literal added without a matching branch) — it is not reachable today,
  since the top-of-body guard already rejects everything outside the six declared literals.
- Both transport DTOs (`PromoteRequest.verb` in `rest.py:158`, `PromoteToolArgs.verb` in
  `tools.py:184`) deliberately stay unconstrained `str`, each carrying an explicit docstring
  explaining why (mirroring `change_origin`'s existing rule): constraining to `Literal` would let
  FastAPI's/pydantic's own validation-error path answer with no `refusal_type`, which is exactly
  the three-transport divergence this design avoids. The new
  `test_an_out_of_enum_verb_refuses_identically_across_three_transports` in
  `test_dual_transport.py` proves the identical `refusal_type` lands on all three transports
  (in-process, REST 422, MCP `ToolError`) for the same out-of-enum value, and that the ledger row
  count stays 0 on all three paths.
- None of the plan-declared prohibitions are violated: no coercion/case-folding/normalisation of
  the verb, no ledger write on any refusal path (guard runs before `Ledger` is even constructed),
  the message names only the caller's own value (no menu of the six accepted verbs, no implied
  default — pinned by `test_an_unrecognised_verb_refuses_by_name_before_any_trace_resolution`'s own
  "no menu" assertion), and the refusal's only public attribute (`verb`) carries the caller's own
  input, never a wiring/arm/node/instance identity.
- `test_rest_transport.py`'s `_REFUSAL_FACTORIES`/`_all_seam_refusal_subclasses` exhaustiveness
  test is a genuine hard failure, not a silent skip: it is a `pytest.mark.parametrize` over every
  live `SeamRefusalError` subclass (found via recursive `__subclasses__()` walk, not a
  hand-maintained list), and the body's first line is `assert exc_cls in _REFUSAL_FACTORIES` with
  an explicit failure message — a subclass added without a factory fails this test, it does not
  skip. `UnrecognisedPromotionVerbError` has a factory registered.

No new defects were introduced by 07-04's own diff. Two findings from the prior 07-REVIEW.md that
07-04 did not touch remain open below, carried forward rather than dropped, plus one small
Info-level cleanliness issue in the two test files 07-04 edited.

## Warnings

### WR-01 (carried forward, unaddressed by 07-04): No serialization across concurrent `promote()`/`rollback()`/`retire()` calls on the same alias

**File:** `databasise/seam/engine.py:1179-1234` (`_promote_sync`), `1297-1355` (`_rollback_sync`),
`1432-1478` (`_retire_sync`)
**Issue:** Each sync body opens its own fresh `Ledger(self.store_root)` inside its own
`run_in_executor` call, reads the alias's current state, derives a mutation class and a minted
version from that read, then appends. Nothing prevents two separate `run_in_executor` calls (two
concurrent `promote()` calls, or a `promote()` racing a `retire()`, on the same alias) from both
reading the same prior state before either appends — the default `ThreadPoolExecutor` has more
than one worker. This is unchanged by 07-04; 07-04's diff touches none of the three `_*_sync`
bodies' locking behavior.

Concretely reachable outcomes (unchanged from the prior review): two concurrent `promote(alias,
...)` calls can both mint the same version number and both append, violating the ledger's own
"a published name is never reused" rule; `retire()`'s `ActiveGenerationRetirementError` guard can
pass on a generation that becomes active only after the guard's own read, via a race with a
concurrent `promote()`/`rollback()`.

No test in the suite exercises concurrent calls to `promote`/`rollback`/`retire` (grep for
`asyncio.gather`/`Lock`/`threading` across `test_promote.py`, `test_rollback.py`, `test_retire.py`,
`test_ledger.py` returns nothing).

**Fix:** Serialize per-alias, e.g. an `asyncio.Lock` keyed by alias held around the whole
async-method body (acquired before dispatching to the executor, released after it returns),
mirroring this codebase's existing keyed-lock pattern (`get_storage_keyed_lock`):

```python
self._promotion_locks: dict[str, asyncio.Lock] = {}

def _lock_for_alias(self, alias: str) -> asyncio.Lock:
    return self._promotion_locks.setdefault(alias, asyncio.Lock())

async def promote(self, alias, trace_ids, change_origin, *, verb="operator-asserted"):
    ...
    async with self._lock_for_alias(alias):
        minted_version, generation_ordinal = await asyncio.get_running_loop().run_in_executor(
            None, _promote_sync
        )
```
(Apply identically around `rollback()`/`retire()`'s own executor calls.) A single-process
`asyncio.Lock` does not protect two separate OS processes sharing one `store_root`; a cross-process
guard (SQLite `BEGIN IMMEDIATE` around the read+append) would be needed if multiple processes are
expected to share one ledger file.

### WR-02 (carried forward, unaddressed by 07-04): `resolve_single_arm`'s promotion-target derivation has no uniqueness guard against two arms sharing a node-id set

**File:** `databasise/seam/promotion.py:115-128` (`_arm_name_for_node_ids`)
**Issue:** `_arm_name_for_node_ids` returns the **first** candidate from `all_wirings()` whose
resolved node-id set equals the trace record's dispatched set:

```python
for name, resolved in all_wirings():
    if frozenset(resolved.get("nodes", {}).keys()) == node_ids:
        return name
```

If a future arm patch changes only a node's `component` (not its node-id membership) — the exact
scenario `derive_mutation_class`'s own docstring calls out as needing separate handling — two arms
could end up with identical node-id sets. `resolve_single_arm` is the sole signal
`promote()`/`rollback()`/`retire()` use to determine which wiring becomes the alias's next
generation; a silent match to the wrong arm here would promote a different wiring than the operator
actually reviewed, with no error raised anywhere. Unchanged by 07-04.

**Fix:** Collect all matches instead of returning on the first, and raise when more than one
candidate's node-id set matches:

```python
matches = [name for name, resolved in all_wirings() if frozenset(resolved.get("nodes", {}).keys()) == node_ids]
if len(matches) > 1:
    raise AssertionError(f"node id set {sorted(node_ids)!r} matches more than one registered wiring: {matches!r}")
if not matches:
    raise AssertionError(...)
return matches[0]
```

## Info

### IN-01 (carried forward, unaddressed by 07-04): `rollback()`'s docstring does not state whether the resolved arm must match the rollback target (unlike `retire()`, which states this explicitly)

**File:** `databasise/seam/engine.py:1248-1296`
**Issue:** `retire()`'s docstring explicitly documents that "the resolved arm does not have to
match the generation being retired" as a deliberate, cited design decision. `rollback()` shares the
identical shape — the resolved arm from `_resolve_operator_preconditions` is used only for
`arm_instance_hashes`, never checked against `target.mutation_id` — but `rollback()`'s own
docstring never states this is deliberate, so a future reader may treat it as an oversight and "fix"
it into a match check. Unchanged by 07-04.
**Fix:** Add the same one-paragraph disclosure `retire()` carries, or add a test exercising a
rollback whose trace ids resolve to an arm different from the rollback target, to make the intended
behavior explicit and pinned.

### IN-02: 07-04's two edited test files fail `ruff check`'s import-sort rule (I001)

**File:** `databasise/tests/seam/test_dual_transport.py:49`, `databasise/tests/seam/test_promotion_posture.py:13`
**Issue:** 07-04 added `UnrecognisedPromotionVerbError` to existing single-line multi-name imports
rather than wrapping them, pushing both lines past ruff's wrap threshold and leaving the import
block flagged as unformatted by `ruff check`:

```python
from databasise.seam.refusals import DisagreeingPromotionTraceIdsError, UnrecognisedPromotionVerbError
```
```python
from databasise.seam.promotion import _MEASUREMENT_POSTURE, PROMOTION_VERBS, MutationClass, PromotionVerb
```
Confirmed by running `ruff check` directly against both files (two `I001` findings, both isolated
to lines 07-04 touched — every other `I001`/lint hit in this file set is pre-existing and outside
07-04's diff hunks, so not reported here). Cosmetic only; does not affect test collection or
runtime behavior (suite is green per the orchestrator's pre-review run).
**Fix:** `ruff check --fix` on both files, or wrap the import list manually:
```python
from databasise.seam.refusals import (
    DisagreeingPromotionTraceIdsError,
    UnrecognisedPromotionVerbError,
)
```

---

_Reviewed: 2026-09-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

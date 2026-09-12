---
phase: 07-promotion-rollback
reviewed: 2026-09-11T00:00:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md
  - databasise/ledger/ledger.py
  - databasise/mcp/server.py
  - databasise/mcp/tools.py
  - databasise/seam/engine.py
  - databasise/seam/envelope.py
  - databasise/seam/__init__.py
  - databasise/seam/promotion.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/tests/evidence/test_promotion_ledger_record.py
  - databasise/tests/ledger/test_ledger.py
  - databasise/tests/mcp/test_dual_transport_parity.py
  - databasise/tests/mcp/test_tool_growth_invariant.py
  - databasise/tests/runner/test_measurement_posture.py
  - databasise/tests/seam/test_alias_registry.py
  - databasise/tests/seam/test_dual_transport.py
  - databasise/tests/seam/test_promote.py
  - databasise/tests/seam/test_promotion_posture.py
  - databasise/tests/seam/test_rest_transport.py
  - databasise/tests/seam/test_retire.py
  - databasise/tests/seam/test_rollback.py
  - databasise/tests/seam/test_selectors.py
findings:
  critical: 2
  warning: 2
  info: 1
  total: 5
status: issues_found
---

# Phase 7: Promotion & Rollback — Code Review Report

**Reviewed:** 2026-09-11
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

The core invariants the phase context called out — append-only ledger, semver-minted-only-at-promotion,
tombstones never lifted, `change_origin`/`promotion_provenance` orthogonality, gate-verb refusal
before any write, single-`run_in_executor` read+append — all hold as implemented and are exercised
by the cited tests. The three-transport parity suite (`test_dual_transport.py`,
`test_dual_transport_parity.py`) is genuinely thorough and does prove field-for-field parity for the
happy paths and for one representative refusal (`DisagreeingPromotionTraceIdsError`).

Two defects survive that suite anyway, both in the class the task explicitly asked to hunt for
("refusal paths reachable in the wrong order," "concurrency/atomicity holes," and "anything that
could let a write land before a refusal fires" — the second finding below is closer to "a write
lands under a stale precondition" than a torn write, but it is the same family):

1. `Databasise.promote()`'s `verb` parameter accepts an arbitrary string at both the REST and MCP
   boundary and, for any value outside the six known verbs, raises a bare `ValueError` from inside
   the executor thread instead of a named `SeamRefusalError` — this is not caught by either
   transport's refusal handler and surfaces as an unhandled crash (REST: 500; MCP: an unwrapped
   `UnexpectedToolError`-style crash), not the documented 422/`ToolError`.
2. `promote()`/`rollback()`/`retire()` each read the ledger's current state and decide what to
   append (mutation class, minted version, and — for `retire()` — the "is this the active
   generation" guard) inside one `run_in_executor` call, but nothing serializes two concurrent
   calls against the *same alias*. Two racing calls open independent SQLite connections, both read
   the same prior state, and both compute and append based on it — this can mint a duplicate
   version number, misattribute `parent`, or let `retire()`'s `ActiveGenerationRetirementError`
   guard pass on a generation that becomes active only after the guard's own read.

Neither defect is covered by any existing test — `grep` for `concurrent`/`Lock`/`threading` across
the ledger and promotion test suites returns nothing, and no test drives `promote()` with a `verb`
value outside the six known literals.

## Critical Issues

### CR-01: `promote()`'s `verb` argument crashes instead of refusing for any unrecognised value

**File:** `databasise/seam/engine.py:1197-1201`
**Issue:** `Databasise.promote()`'s signature declares `verb: str = "operator-asserted"` (not the
`PromotionVerb` `Literal` `databasise/seam/promotion.py` already defines), and neither REST's
`PromoteRequest.verb: str` (`databasise/seam/rest.py:157`) nor MCP's `PromoteToolArgs.verb: str`
(`databasise/mcp/tools.py:184`) constrains it either — both are plain `str` fields with no
validator. Inside `_promote_sync`, once `verb` has passed the `_NOT_BUILT_VERBS` check and the
`_GATE_VERBS` check, the fallback branch is:

```python
if verb != "operator-asserted":
    raise ValueError(f"unknown promotion verb {verb!r}")
```

`ValueError` is **not** a `SeamRefusalError` (it's the other way around — `SeamRefusalError`
subclasses `ValueError`), so:
- `databasise/seam/rest.py`'s `app.add_exception_handler(SeamRefusalError, _refusal_response)`
  does not match it, and it propagates as an unhandled exception → FastAPI's default 500, not the
  documented 422.
- `databasise/mcp/server.py`'s `_refusal_mapped` wrapper only catches `SeamRefusalError`, so the
  same raw exception crashes the tool call rather than surfacing as a `ToolError` — precisely the
  failure mode the project already named and fixed for other manually-parsed fields
  (`MalformedBase64PayloadError`/CR-01b, `MalformedSelectorPayloadError`/CR-02, `PageSizeExceededError`).

A caller sending `"verb": "Promote-Next"` (case typo), `"verb": "promote_next"` (underscore typo),
or any other string reaches this branch. No test exercises it — `grep -rn "unknown promotion verb"
databasise/tests/` finds only the raise site itself.

**Fix:** Raise a named `SeamRefusalError` subclass instead of a bare `ValueError` (mirroring
`InvalidChangeOriginError`'s own shape), and validate as early as `_NOT_BUILT_VERBS`/`_GATE_VERBS`
are checked — before any ledger read runs:

```python
# databasise/seam/refusals.py
class UnrecognisedPromotionVerbError(SeamRefusalError):
    def __init__(self, *, verb: str) -> None:
        self.verb = verb
        super().__init__(f"UnrecognisedPromotionVerbError: verb {verb!r} is not a recognised promotion verb")

# databasise/seam/engine.py, in promote(), before _resolve_operator_preconditions:
_ALL_KNOWN_VERBS = _NOT_BUILT_VERBS + _GATE_VERBS + ("operator-asserted",)
if verb not in _ALL_KNOWN_VERBS:
    raise UnrecognisedPromotionVerbError(verb=verb)
```

## Warnings

### WR-01: No serialization across concurrent `promote()`/`rollback()`/`retire()` calls on the same alias

**File:** `databasise/seam/engine.py:1179-1234` (`_promote_sync`), `1297-1355` (`_rollback_sync`),
`1432-1478` (`_retire_sync`)
**Issue:** Each of the three sync bodies opens its own fresh `Ledger(self.store_root)` (its own
SQLite connection) inside the `run_in_executor` call, reads the alias's current state
(`ledger.by_alias(alias)` / `ledger.generation_state(alias, version)`), derives a mutation class and
a minted version from that read, and then appends — all correctly within one executor call, so the
documented "never split the read and the write across two threads" constraint is honoured. But
nothing prevents **two separate `run_in_executor` calls** (two concurrent `promote()` calls, or a
`promote()` racing a `retire()`, on the same alias) from both reading the same prior state before
either has appended. `asyncio.get_running_loop().run_in_executor(None, ...)` dispatches to the
default `ThreadPoolExecutor`, which has more than one worker, so two REST/MCP requests against the
same alias genuinely can run these bodies in parallel.

Concretely reachable outcomes:
- Two concurrent `promote(alias, ...)` calls both read the same `prior_record`/`prior_surface`,
  both compute the same `minted_version` (e.g. both mint `"1.1.0"`), and both append — violating
  the ledger's own stated "a published name is never reused" rule
  (`databasise/seam/engine.py`'s own `rollback()` docstring, and CONTRACT §0.4).
- `retire()`'s `ActiveGenerationRetirementError` guard (`active.minted_version == version`) reads
  `active` before its own append; a concurrent `promote()`/`rollback()` that changes the active
  generation between that read and the `retire()` append can let a retirement of what was — by the
  time it lands — the active generation through, exactly the outcome the guard exists to prevent.

No test in this phase's suite exercises concurrent calls to `promote`/`rollback`/`retire` (confirmed
by grep: no `asyncio.gather`, `Lock`, or `threading` reference anywhere in
`databasise/tests/seam/test_promote.py`, `test_rollback.py`, `test_retire.py`, or
`databasise/tests/ledger/test_ledger.py`).

**Fix:** Serialize per-alias, e.g. an `asyncio.Lock` keyed by alias held around the whole
`_execute`-style body (acquired in the coroutine before dispatching to the executor, released after
the executor call returns), mirroring the "keyed locks" pattern already used elsewhere in this
codebase for per-entity/per-doc writes (`get_storage_keyed_lock`):

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
(Apply the identical lock around `rollback()`/`retire()`'s own executor calls.) A single-process
`asyncio.Lock` does not protect against two separate OS processes sharing one `store_root`, but it
closes the concurrent-coroutine race this review demonstrated and is proportionate to this
milestone's single-process embedded-engine scope; a cross-process guard (SQLite `BEGIN IMMEDIATE`
around the read+append) would be needed if multiple processes are expected to share one ledger file.

### WR-02: `resolve_single_arm`'s promotion-target derivation has no uniqueness guard against two arms sharing a node-id set

**File:** `databasise/seam/promotion.py:111-124` (`_arm_name_for_node_ids`)
**Issue:** The module's own docstring states the dispatched node-id set is "both query-invariant
and unique per arm," and today, across the registered LightRAG/HippoRAG arms, that happens to hold.
But `_arm_name_for_node_ids` never verifies uniqueness at the point it matters — it iterates
`all_wirings()` and returns the **first** candidate whose resolved node-id set equals the trace
record's dispatched set:

```python
for name, resolved in all_wirings():
    if frozenset(resolved.get("nodes", {}).keys()) == node_ids:
        return name
```

If a future arm patch changes only a node's `component` (not its node-id membership) — exactly the
scenario `derive_mutation_class`'s own docstring calls out as needing separate handling (D-10) — two
arms could end up with identical node-id sets. `resolve_single_arm` is the sole signal
`promote()`/`rollback()`/`retire()` use to determine which wiring becomes the alias's next
generation; a silent match to the wrong arm here would promote a different wiring than the operator
actually reviewed, with no error raised anywhere.

**Fix:** Collect all matches instead of returning on the first, and raise (an `AssertionError` is
consistent with this function's existing "should be unreachable" contract, or a dedicated internal
invariant error) when more than one candidate's node-id set matches:

```python
matches = [name for name, resolved in all_wirings() if frozenset(resolved.get("nodes", {}).keys()) == node_ids]
if len(matches) > 1:
    raise AssertionError(f"node id set {sorted(node_ids)!r} matches more than one registered wiring: {matches!r}")
if not matches:
    raise AssertionError(...)
return matches[0]
```

## Info

### IN-01: `rollback()`'s docstring does not state whether the resolved arm must match the rollback target (unlike `retire()`, which states this explicitly)

**File:** `databasise/seam/engine.py:1248-1296`
**Issue:** `retire()`'s docstring explicitly documents that "the resolved arm does not have to match
the generation being retired" as a deliberate, cited design decision. `rollback()` shares the
identical shape — `_resolve_operator_preconditions`'s resolved arm is used only for
`arm_instance_hashes`, never checked against `target.mutation_id` — but `rollback()`'s own docstring
never states this is deliberate, so a future reader may treat it as an oversight and "fix" it into a
match check (exactly the trap `retire()`'s docstring warns against for itself). Every test in
`test_rollback.py` happens to seed the same arm for both the rollback target and the trace ids, so
this is untested behavior either way.
**Fix:** Add the same one-paragraph disclosure `retire()` carries, or add a test exercising a
rollback whose trace ids resolve to an arm different from the rollback target, to make the intended
behavior explicit and pinned.

---

_Reviewed: 2026-09-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

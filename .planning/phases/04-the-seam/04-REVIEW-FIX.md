---
phase: 04-the-seam
fixed_at: 2026-09-06T19:30:00-07:00
review_path: .planning/phases/04-the-seam/04-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-09-06
**Source review:** .planning/phases/04-the-seam/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (5 Critical, 3 Warning)
- Fixed: 8
- Skipped: 0

**Verification:** every gate ran inside the isolated worktree this agent created
(`.claude/worktrees/rf-04-*`, fast-forwarded into `main` on cleanup) — the numbers below are
reproducible from the commits on `main` after this run completes.

- `cd databasise && uv run --extra rest pytest -q` — **572 passed, 9 skipped**, zero failures
- `cd databasise && uv run pytest -q` — **572 passed, 9 skipped**, zero failures (proves the
  embedded library needs no web stack)

Both commands were at 561 passed / 9 skipped before any fix in this run (the actual current
baseline on `main` — the config's documented 570/552 baseline predates this phase's own commits).
Every fix added net-new test coverage; no existing test was weakened or deleted to make a fix pass.

## Fixed Issues

### CR-04: The two-tier leak gate never inspects low-entropy identities that leak as string *values*

**Files modified:** `databasise/seam/redact.py`, `databasise/tests/seam/test_leak.py`
**Commit:** `e16dca8`
**Applied fix:** Added `assert_no_forbidden_values` — a scoped value-walk that checks every string
value at every nesting depth for an *exact* match against the forbidden low-entropy set, skipping
only `answer` (the one genuinely freeform, LLM-composed field) via a `FREEFORM_VALUE_KEYS` allow
list. This avoids reintroducing the false-positive problem the two-tier design exists to avoid: an
answer legitimately containing the word "keywords" still passes, while a node id sitting in
`SeamEvent.component` (the review's own reproduction) now fails. Also added `run_id` to
`forbidden_identities()`'s high-entropy set (a random UUID, same identity-name pattern as the other
high-entropy fields) — the review noted this was a related, narrower gap that let CR-02's leak slip
past the gate too. Two negative-control tests added: a planted value leak that must fail, and a
legitimate "keywords" answer that must not.

### CR-02: `resolve_trace(debug=False)` leaks `wiring_id`, `wiring_instance_hash`, `arm_id`, and `run_id`

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_trace_token.py`,
`databasise/tests/seam/test_leak.py`, `databasise/tests/seam/test_rest_transport.py`
**Commit:** `3e3ff08`
**Applied fix:** Replaced the deny-list-of-one-key (`!= "nodes"`) with an explicit allow-list
(`_NON_DEBUG_TRACE_FIELDS`) naming exactly the ten non-identity `RunRecord` fields safe to return
without `debug=True`. This closes CR-02 and CR-05 together, per the review's own grouping: CR-05's
fix is the missing test coverage that let CR-02 ship unnoticed, so both landed in one commit.

### CR-05: `resolve_trace`'s non-debug filtering has no test coverage against the leak gate at all

**Files modified:** `databasise/tests/seam/test_leak.py`, `databasise/tests/seam/test_rest_transport.py`
**Commit:** `3e3ff08` (same commit as CR-02 — see above)
**Applied fix:** Added a leak-gate run against `resolve_trace(debug=False)`'s actual in-process
output (`test_leak.py`) and against `POST /trace/resolve {"debug": false}`'s actual REST response
(`test_rest_transport.py`), using both the high-entropy substring check and the new key/value
structural checks — exercising the real production `resolve_trace()` method, not a hand-copied
replica.

### CR-03: `UnbudgetableParticipantError` discloses a real internal `node_id` in its own message and REST body

**Files modified:** `databasise/seam/tokens.py`, `databasise/seam/rest.py`,
`databasise/tests/seam/test_rest_transport.py`
**Commit:** `ba1c813`
**Applied fix:** The refusal now stores the wiring's own `node_id` on a leading-underscore
`_internal_node_id` attribute instead of a public `node_id` attribute, and drops it from the
message entirely. `rest.py`'s `_refusal_response` now skips leading-underscore attributes
generically when dumping `vars(exc)` into the REST body — a convention any future internal-only
refusal value can reuse. Corrected `test_rest_transport.py`'s own parametrized refusal test, which
previously *asserted* the leak as required behavior, to instead assert the private attribute's
absence from the response body.

### CR-01: `/query/stream` refusals crash instead of returning the documented non-success response

**Files modified:** `databasise/seam/rest.py`, `databasise/tests/seam/test_rest_transport.py`
**Commit:** `8536200`
**Applied fix:** Traced FastAPI's own SSE routing internals (`fastapi/routing.py`) to confirm the
mechanism: `dependant.call(**values)` for an async-generator endpoint only creates the generator
object — the body (and any exception it raises) doesn't run until the SSE producer task starts
consuming it, by which point the response has already begun and the app-level exception handler
can no longer intercept anything. FastAPI dependencies, by contrast, are awaited synchronously
during request dispatch, before the SSE branch runs at all. Moved envelope resolution into a
`Depends()`-injected dependency (`_resolve_streamed_envelope`, calling the same `engine.query()` an
in-process caller awaits — never a private method), so a refusal now propagates through the normal
`add_exception_handler(SeamRefusalError, ...)` path. Added the missing test: POSTing an empty query
object to `/query/stream` now asserts a `422` with `refusal_type: "EmptyQueryObjectError"`.

### WR-01: Multiple `provides` nodes silently last-write-wins for `answer`/`depth_label`

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_seam_tracer.py`
**Commit:** `8abab46`
**Applied fix:** Extracted the answer/depth_label selection into a new pure helper,
`_select_answer()`, which iterates `provides` (the wiring's own declared order) instead of
`record.nodes` (scheduler dispatch order), and raises `RuntimeError` if more than one `provides`
node produces a completion — mirroring `_execute()`'s own existing precedent for a cyclic resolved
wiring (also a bare `RuntimeError`, also "should never happen with today's selectors"). Added a
focused unit test for both the ordering fix and the new refusal.

### WR-02: `_mach11_events`'s "node not found" fallback fabricates a zero-count spend, untested

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_mach11_event.py`
**Commit:** `1651180`
**Applied fix:** Investigated whether the branch is provably unreachable in production (every
node the scheduler's own recorder reports a touch for also receives a `NodeTrace`, even when
halted) and concluded the safer choice — given the branch has no coverage today and the risk
calculus favors a visible sentinel over a deletion that could silently reintroduce an
`AttributeError` if the scheduler's tracing guarantee ever changes — is to give the fallback a
distinct `counted_by="unknown"` sentinel, never the real `"none"` value an honestly-zero node
reports. Added the test that exercises this previously dead-in-coverage branch directly.

### WR-03: `mint_evidence_refs` raises a raw `KeyError` instead of a named refusal for a malformed item

**Files modified:** `databasise/seam/evidence.py`, `databasise/tests/seam/test_evidence_refs.py`
**Commit:** `01ee6bc`
**Applied fix:** Added `MalformedEvidenceItemError` (a plain named `RuntimeError` subclass,
matching `databasise.stores.vector`'s own `VectorNamespaceNotSelectedError`/
`VectorStoreCorruptedError` precedent — not a `SeamRefusalError`, since the malformed shape is the
wiring's own retrieval output, never the consumer's own input per `refusals.py`'s own stated
boundary). `mint_evidence_refs` now checks for a missing `"id"` key explicitly and raises, naming
the malformed item's namespace/index, instead of letting a bare `KeyError` propagate. Added a test
covering the previously-unguarded path.

## Skipped Issues

None — every finding in scope was fixed.

---

_Fixed: 2026-09-06_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

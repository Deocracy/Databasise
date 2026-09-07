---
phase: 04-the-seam
fixed_at: 2026-09-07T03:15:47Z
review_path: .planning/phases/04-the-seam/04-VERIFICATION.md
iteration: 1
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 4: The Seam — Gap Closure Report

**Fixed at:** 2026-09-07T03:15:47Z
**Source review:** `.planning/phases/04-the-seam/04-VERIFICATION.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 1 (the single gap `04-VERIFICATION.md` recorded)
- Fixed: 1
- Skipped: 0

## Fixed Issues

### GAP-01: `Databasise.query_stream()` orphaned by the CR-01 fix; REST reimplements its shaping inline

**Files modified:**
- `databasise/seam/engine.py`
- `databasise/seam/rest.py`
- `databasise/tests/seam/test_rest_transport.py`
- `.planning/phases/04-the-seam/04-05-SUMMARY.md`

**Commit:** `b581413`

**Applied fix — took the reuse option, not the retirement option (per the task's explicit
instruction):**

The verifier's own diagnosis named the exact mechanism: the CR-01 review fix moved envelope
resolution into a FastAPI `Depends()` dependency so a `SeamRefusalError` is known and mapped to a
422 *before* the SSE response begins. That is a genuine, necessary constraint — Python does not run
an async generator function's body until it is first iterated, so `Databasise.query_stream()`
itself (an `async def` containing `yield`) can never supply that eager-refusal guarantee to a REST
caller, no matter how it is called. `post_query_stream` could not simply `async for event in
engine.query_stream(...)` and keep CR-01's fix — hence the CR-01 patch's own side effect of
reimplementing the two shaping lines inline instead, leaving `query_stream()` with zero callers.

The fix extracts the event-shaping itself — the two `yield` statements, which read only an
already-computed `ResponseEnvelope`'s own fields and never touch the network, the scheduler, or
anything that can raise a `SeamRefusalError` — into a new module-level, pure, synchronous function:

```python
def stream_envelope_events(envelope: ResponseEnvelope) -> Iterator[dict[str, Any]]:
    for ref in envelope.evidence:
        yield {"kind": "evidence", "evidence": ref.model_dump()}
    yield {"kind": "final", **envelope.model_dump(exclude={"evidence"})}
```

`Databasise.query_stream()` now shapes through it:

```python
async def query_stream(self, query_object, selector=None, *, debug=False):
    del debug
    envelope = await self._execute(query_object, selector)
    for event in stream_envelope_events(envelope):
        yield event
```

And `rest.py`'s `post_query_stream` shapes the eagerly-`Depends()`-resolved envelope through the
identical function, rather than re-writing the two `yield` lines itself:

```python
@app.post("/query/stream", response_class=EventSourceResponse)
async def post_query_stream(envelope: ResponseEnvelope = Depends(_resolve_streamed_envelope)):
    for event in stream_envelope_events(envelope):
        yield event
```

This is the shape the verifier itself suggested as one legitimate closure ("pre-resolving the
envelope via the same `_execute()` call `query_stream()` itself calls, then sharing the
field-splitting helper rather than re-writing it") and satisfies the stated constraint: REST still
resolves the envelope eagerly via `_resolve_streamed_envelope` (unchanged, still calls
`engine.query()` — no regression to CR-01), and now genuinely shares its event-shaping
implementation with `Databasise.query_stream()` rather than maintaining an independent copy. A
`grep -rn "\.query_stream("` now finds a real in-process caller (the new parity test below), so
`query_stream()` is no longer orphaned.

**Why not call `query_stream()` itself from REST:** doing so would either (a) reintroduce CR-01's
crash — awaiting the generator inside the SSE producer body means a refusal fires after the
response has begun — or (b) require manually draining the generator inside `Depends()`, which
defeats the purpose of a generator and produces the same "REST re-implements a resolution loop"
smell in a different shape. Splitting resolution (`_execute`, already eager via `Depends()`) from
shaping (`stream_envelope_events`, pure and side-effect-free) is what lets both properties hold at
once without a second execution path.

**Test added — closes 04-05-PLAN.md Task 2's unmet acceptance criterion:**
`test_rest_streamed_events_equal_databasise_query_streams_in_process_output` in
`databasise/tests/seam/test_rest_transport.py` runs the identical query object against the
identical synthetic store/stub clients twice — once via `Databasise.query_stream()` in-process,
once via `POST /query/stream` — and asserts every SSE event equal, field-by-field, excluding only
`trace_token` in the final event (the one field two independent runs legitimately mint differently,
D-06; mirrors `test_dual_transport.py`'s own exclusion pattern for the non-streaming operations).
This is the test that would fail if a future edit made the two shaping paths diverge again.

**Stale claims corrected:**
- `databasise/seam/engine.py`'s module docstring: added a new paragraph ("CR-01 gap closure")
  explaining precisely why `query_stream()` alone cannot give REST an eager-refusal guarantee, and
  how `stream_envelope_events()` is the shared function both paths now iterate.
- `.planning/phases/04-the-seam/04-05-SUMMARY.md`: corrected the "Accomplishments" bullets that
  implied `/query/stream` calls "the identical in-process method" the same way the other three
  endpoints do (it does not, and cannot, per the constraint above) to instead describe the actual
  eager-resolve-then-shared-shape design; added a new "Deviation 5" entry documenting the gap, its
  cause, and its fix, and updated the deviations total.

## Verification

Ran in two places, in this order:

1. **Isolated worktree** (`.claude/worktrees/rf-04-489128-1788749930`, on temp branch
   `gsd-reviewfix/04-489128`) — where the fix was authored and committed:
   - `cd databasise && uv run --extra rest pytest -q tests/seam/` → **116 passed** (115 baseline +
     1 new parity test).
   - `cd databasise && uv run --extra rest pytest -q` → **573 passed, 9 skipped**. The 9 skips are
     the pre-existing v1-parity-fixture-dependent tests (`tests/parity/*`) that require untracked
     directories (`v1/.parity_working_dir`, `v1/.parity_v2_store`, `v1/.venv`) — a worktree does
     not carry untracked files from the main checkout, so these skip there regardless of this fix.
     This is a worktree-isolation artifact, not a regression; not reproducible as "573 passed" from
     the main checkout, which is why the numbers below (main checkout) are the ones that compare
     directly against `04-VERIFICATION.md`'s own 581-passed baseline.
   - After committing, the worktree's `gsd-reviewfix/04-489128` branch was fast-forward-merged
     into `main`, the worktree removed, the temp branch deleted, and the recovery sentinel cleared
     — all in the main checkout, `/home/chris/coding/Databasise-2.0-fully-agnostic-system`.

2. **Main checkout** (`/home/chris/coding/Databasise-2.0-fully-agnostic-system/databasise`, after
   the fast-forward, where the v1 parity fixtures do exist) — the numbers that reproduce from the
   tree a reader is actually looking at:
   - `cd databasise && uv run --extra rest pytest -q tests/seam/` → **116 passed**.
   - `cd databasise && uv run --extra rest pytest -q` → **582 passed, 0 skipped** — exactly the
     verifier's 581-passed baseline plus the one new parity test, with the v1-parity fixtures
     present so nothing skips. **Confirms no regression and no residual skip anywhere.**
   - `cd databasise && uv run pytest -q` (no `rest` extra flag on this invocation) → **582 passed**
     in 148.93s. (The shared `.venv` still had the `rest` extra's packages installed from the
     `--extra rest` runs above, so `fastapi` was importable and the REST-gated tests ran rather
     than skipped via `pytest.importorskip("fastapi")` — this is an artifact of a shared virtualenv
     across successive commands in this session, not a claim about the embed-without-`rest`
     dependency boundary, which `test_embed_startup.py` proves structurally via
     `importlib.metadata` regardless of what happens to be installed at test time.) The relevant
     fact for this gap-fix is unambiguous either way: 0 failures, 0 errors.

## No Skipped Findings

`04-VERIFICATION.md` recorded exactly one gap; it is closed as described above.

---

_Fixed: 2026-09-07T03:15:47Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_

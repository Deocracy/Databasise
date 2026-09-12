---
phase: 04-the-seam
verified: 2026-09-07T04:00:00Z
status: passed
score: 13/13 must-haves verified
covered_files: [".planning/REQUIREMENTS.md", ".planning/ROADMAP.md", ".planning/phases/04-the-seam/04-01-PLAN.md", ".planning/phases/04-the-seam/04-01-SUMMARY.md", ".planning/phases/04-the-seam/04-02-PLAN.md", ".planning/phases/04-the-seam/04-02-SUMMARY.md", ".planning/phases/04-the-seam/04-03-PLAN.md", ".planning/phases/04-the-seam/04-03-SUMMARY.md", ".planning/phases/04-the-seam/04-04-PLAN.md", ".planning/phases/04-the-seam/04-04-SUMMARY.md", ".planning/phases/04-the-seam/04-05-PLAN.md", ".planning/phases/04-the-seam/04-05-SUMMARY.md", ".planning/phases/04-the-seam/04-CHECKPOINT-ANSWERS.md", ".planning/phases/04-the-seam/04-CONTEXT.md", ".planning/phases/04-the-seam/04-GAP-FIX.md", ".planning/phases/04-the-seam/04-RESEARCH.md", ".planning/phases/04-the-seam/04-REVIEW-FIX.md", ".planning/phases/04-the-seam/04-REVIEW.md", ".planning/phases/04-the-seam/04-VERIFICATION.md", ".planning/phases/04-the-seam/COVERAGE.md", "databasise/__init__.py", "databasise/ledger/ledger.py", "databasise/pyproject.toml", "databasise/seam/__init__.py", "databasise/seam/_base.py", "databasise/seam/engine.py", "databasise/seam/envelope.py", "databasise/seam/evidence.py", "databasise/seam/query.py", "databasise/seam/redact.py", "databasise/seam/refusals.py", "databasise/seam/rest.py", "databasise/seam/selectors.py", "databasise/seam/tokens.py", "databasise/seam/trace_store.py", "databasise/stores/vector.py", "databasise/tests/fixtures/wiring-harness.json", "databasise/tests/runner/test_measurement_posture.py", "databasise/tests/seam/__init__.py", "databasise/tests/seam/conftest.py", "databasise/tests/seam/test_alias_registry.py", "databasise/tests/seam/test_dual_transport.py", "databasise/tests/seam/test_envelope_schema.py", "databasise/tests/seam/test_evidence_refs.py", "databasise/tests/seam/test_leak.py", "databasise/tests/seam/test_mach11_event.py", "databasise/tests/seam/test_query_object.py", "databasise/tests/seam/test_rest_transport.py", "databasise/tests/seam/test_seam_tracer.py", "databasise/tests/seam/test_selectors.py", "databasise/tests/seam/test_token_accounting.py", "databasise/tests/seam/test_trace_token.py", "databasise/tests/test_embed_startup.py"]
covered_digest: "v1:sha256:5e56b76bf4c4718c1d04d1e4f5f4dcecbf97822bf9caaf60b2b579613c175337"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 12/13
  gaps_closed:
    - "The REST streaming endpoint and Databasise.query_stream() share one execution/serialization path, and a test proves REST's streamed output equals the in-process query_stream() counterpart's output for the same input"
  gaps_remaining: []
  regressions: []
---

# Phase 4: The Seam — Verification Report (Re-verification after gap closure)

**Phase Goal:** Callers reach the engine through one closed envelope that tells them nothing about which modality answered
**Verified:** 2026-09-07T04:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (commit `b581413`, `04-GAP-FIX.md`)

## Method

This is a targeted re-verification. The prior pass (`12/13`, `gaps_found`) already reproduced all
8 review fixes and verified 12 of 13 must-haves; that work was spot-checked, not redone. Effort
concentrated on the single reported gap and anything the closure touched: read
`databasise/seam/engine.py` and `databasise/seam/rest.py` in full at their current state (not the
GAP-FIX narrative), read the new parity test in `databasise/tests/seam/test_rest_transport.py` in
full, grepped the repo for every remaining event-shaping literal, ran the CR-01 regression test and
the leak-gate exploit/false-positive tests directly, and ran the full suite once.

## The Gap and Its Closure

**Gap (previous pass):** `Databasise.query_stream()` was an orphaned async generator — the CR-01
fix moved envelope resolution into REST's `Depends()` dependency and reimplemented SSE
event-shaping inline in `rest.py`, so `query_stream()` had zero callers repo-wide and no test
compared REST's streamed output to the in-process generator's output.

**Closure (commit `b581413`):** a new module-level pure function
`stream_envelope_events(envelope) -> Iterator[dict]` in `databasise/seam/engine.py`, containing the
two `yield` statements (one per evidence ref, one final event). `Databasise.query_stream()` now
calls `self._execute(...)` then iterates `stream_envelope_events(envelope)`. `rest.py`'s
`post_query_stream` resolves the envelope eagerly via the unchanged `Depends(_resolve_streamed_envelope)`
(itself an unchanged call to `engine.query()`, preserving CR-01's before-first-SSE-byte refusal
mapping) and then iterates the identical `stream_envelope_events(envelope)` — not a re-write.

### 1. Is there genuinely one event-shaping implementation now?

Verified by reading both call sites and by grep. `databasise/seam/engine.py:259-260` is the only
place in the repository containing the literal dict construction `{"kind": "evidence", ...}` /
`{"kind": "final", ...}`:

```
databasise/seam/engine.py:259:        yield {"kind": "evidence", "evidence": ref.model_dump()}
databasise/seam/engine.py:260:    yield {"kind": "final", **envelope.model_dump(exclude={"evidence"})}
```

`rest.py`'s `post_query_stream` (lines 143-154) contains no such literal — it only calls
`for event in stream_envelope_events(envelope): yield event`. `Databasise.query_stream()`
(engine.py:336-354) does the same. **Genuinely one implementation, imported by rest.py from
engine.py (`from databasise.seam.engine import Databasise, stream_envelope_events`), not two.**

### 2. Was CR-01 regressed?

No. `_resolve_streamed_envelope` is unchanged — still a FastAPI dependency (evaluated during
request dispatch, before the SSE generator body runs) calling `engine.query()` directly, so a
`SeamRefusalError` still raises before any SSE byte is written and is still caught by the same
`app.add_exception_handler(SeamRefusalError, ...)` every other endpoint uses.
`test_a_refusal_via_query_stream_returns_the_documented_non_success_response` (unmodified from
before the gap-fix) still asserts a `422` with `refusal_type == "EmptyQueryObjectError"` for an
empty query posted to `/query/stream`. Ran it directly:

```
tests/seam/test_rest_transport.py::test_a_refusal_via_query_stream_returns_the_documented_non_success_response PASSED
```

No unhandled `ExceptionGroup`, no crash. CR-01 holds.

### 3. Does the new equality test compare substantive content, or pass vacuously?

Read `test_rest_streamed_events_equal_databasise_query_streams_in_process_output` in full. It is
not shape-only or count-only:

- Asserts both event lists are non-empty (`assert rest_events and in_process_events`) — guards
  against a vacuous pass on two empty sequences.
- Asserts equal length.
- For every non-final event, asserts full dict equality (`rest_event == in_process_event`) — this
  includes `evidence.ref` and the full evidence payload, not just `kind`.
- For the final event, asserts full dict equality on every field **except** `trace_token`, and
  explicitly asserts the two `trace_token` values differ (proving each run legitimately minted its
  own random token rather than the comparison accidentally passing because both sides share state).
- The `answer`, `token_accounting`, `depth_label`, `evidence` and all other envelope fields are
  therefore compared field-by-field between the REST-obtained SSE stream and the in-process
  `query_stream()` generator, run against the same synthetic store/stub clients. This is
  substantive content comparison, not shape-only — held to the same bar Phase 3's review applied.

Ran it directly, isolated:

```
tests/seam/test_rest_transport.py::test_rest_streamed_events_equal_databasise_query_streams_in_process_output PASSED
```

### 4. Do the two previously-stale claims now match the code?

- `engine.py`'s module docstring: now contains a "CR-01 gap closure" paragraph (lines 60-70)
  explaining precisely why `query_stream()` alone cannot give REST an eager-refusal guarantee and
  naming `stream_envelope_events` as the one shared function both paths iterate. Matches the code.
- `04-05-SUMMARY.md`: contains a new "5. [Post-verification correction, 04-GAP-FIX.md]" deviation
  entry (lines 338-358) describing the orphaning, the fix, the files touched, and the verification
  numbers (116 passed in `tests/seam/`, full suite passed) — matches the current code and this
  pass's own independent re-run. The "Total deviations" count was updated to include it.

Both stale claims are corrected and now consistent with the shipped code.

### 5. Leak gate re-confirmed (regression check on unrelated code)

`databasise/seam/redact.py` was not touched by this gap-fix; re-ran its tests directly to confirm
no incidental regression from the engine.py/rest.py edits:

```
tests/seam/test_leak.py::test_the_value_check_fails_on_a_node_id_planted_as_a_seam_events_component_value PASSED
tests/seam/test_leak.py::<legitimate-word-in-answer positive control> PASSED
```

The exploit reproduction (`SeamEvent.component = "chunk-vector"`) still raises `AssertionError` as
expected (gate catches it); a `SeamEvent`/answer containing the ordinary word "keywords" still does
not false-positive. All 11 tests in `test_leak.py` pass.

## Observable Truths (delta from previous pass)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 19 | The same seam is reachable two ways with identical behavior for the **streaming** operation — REST's SSE output proven equal to `Databasise.query_stream()`'s own in-process output for the same input (criterion 5, part) | ✓ VERIFIED | `stream_envelope_events()` is the one shared function both `Databasise.query_stream()` and `rest.py`'s `post_query_stream` iterate (grep-confirmed, no duplicate literal); `test_rest_streamed_events_equal_databasise_query_streams_in_process_output` passes with substantive field-by-field comparison |

All other 21 individually-tracked truths from the prior pass are unchanged (not re-derived from
scratch this pass; spot-checked via the full-suite run and the leak-gate re-run above, both green).

**Score:** 13/13 must-have-level items verified (was 12/13; the one remaining gap is now closed).

### Required Artifacts (delta)

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `databasise/seam/engine.py` | The `Databasise` seam object | ✓ VERIFIED | `query_stream` no longer orphaned — has a real in-process caller (the new parity test) and is the shaping-logic owner both transports use |
| `databasise/seam/rest.py` | Optional REST transport | ✓ VERIFIED | Streaming endpoint no longer duplicates event-shaping; imports and reuses `stream_envelope_events` from `engine.py` |

### Key Link Verification (delta)

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `rest.py` | `engine.py` | `stream_envelope_events(envelope)` | ✓ WIRED | `rest.py` imports the function directly (`from databasise.seam.engine import Databasise, stream_envelope_events`); no local reimplementation remains |
| `Databasise.query_stream()` | (in-process caller) | direct `async for` iteration | ✓ WIRED | `test_rest_streamed_events_equal_databasise_query_streams_in_process_output` calls it in-process; no longer zero callers |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| No duplicate event-shaping literal anywhere in the repo | `grep -rn '"kind": "evidence"\|"kind": "final"' databasise/seam/` | Only `engine.py:259-260` match | ✓ PASS |
| CR-01 regression: refusal via `/query/stream` still maps to 422 | `pytest tests/seam/test_rest_transport.py::test_a_refusal_via_query_stream_returns_the_documented_non_success_response` | PASSED | ✓ PASS |
| New parity test proves substantive equality, not vacuous | Read test source; ran it directly | PASSED, asserts non-empty + full field equality (excl. `trace_token`, whose inequality is itself asserted) | ✓ PASS |
| Leak-gate exploit reproduction still catches a planted node-id value | `pytest tests/seam/test_leak.py` (11 tests) | 11 passed | ✓ PASS |
| Targeted subset (stream/leak/refusal) | `pytest tests/seam/test_rest_transport.py tests/seam/test_leak.py -k "stream or leak or CR01 or refusal or forbidden"` | 24 passed | ✓ PASS |
| Full seam suite | `cd databasise && uv run --extra rest pytest -q tests/seam/` | 116 passed (115 baseline + 1 new) | ✓ PASS |
| Full repo suite, REST extra active | `cd databasise && uv run --extra rest pytest -q` | **582 passed** in 181.6s (was 581; matches GAP-FIX's own claimed count exactly) | ✓ PASS |

### Requirements Coverage (delta)

| Requirement | Source Plan(s) | Status | Evidence |
|---|---|---|---|
| API-04 | 04-05 | ✓ SATISFIED (was ⚠️ PARTIALLY SATISFIED) | REST/in-process streaming parity now proven by a substantive test; the previously-unmet 04-05-PLAN.md Task 2 acceptance criterion is now met |

All other six requirement IDs (API-03, API-05, API-10, API-11, EMBED-02, MACH-11) are unchanged
from the prior pass's `✓ SATISFIED` determinations — not re-derived here; the full-suite green run
covers their tests as a regression check.

### Anti-Patterns Found

None new. No `TBD`/`FIXME`/`XXX`/`HACK`/`PLACEHOLDER` markers in any file this gap-fix touched
(`databasise/seam/engine.py`, `databasise/seam/rest.py`, `databasise/tests/seam/test_rest_transport.py`,
`04-05-SUMMARY.md`). The two previously-flagged stale-documentation findings (engine.py module
docstring, 04-05-SUMMARY.md) are resolved — see "Do the two previously-stale claims now match the
code?" above.

## Deferred / Not-in-Scope (unchanged, correctly disclosed, not gaps)

- The alias registry is empty this phase by design (Phase 7 populates it).
- Unauthenticated REST surface — disclosed, accepted, `transfer` disposition.
- MACH-11's event is proven only against fixture parts (no `parts_core` part declares
  `mutates_store` yet) — disclosed, sound correlation rule.
- EMBED-02's MCP half is deferred to a later phase; COVERAGE.md records this as an explicit
  `OPT-OUT`.

## Gaps Summary

None. The single gap the previous pass raised — REST streaming and `Databasise.query_stream()`
diverging into two independently-maintained event-shaping implementations, with the acceptance
criterion requiring proven parity left unmet — is closed. Verified independently, not by trusting
`04-GAP-FIX.md`'s narrative: read both call sites and confirmed by grep that only one location in
the repository constructs the SSE event dicts; read the new test in full and confirmed it performs
substantive field-by-field comparison rather than a shape- or count-only check; re-ran the CR-01
refusal-mapping test directly and confirmed no regression; re-ran the leak-gate exploit and
false-positive control directly and confirmed no regression; ran the full suite once and got 582
passed, exactly the baseline (581) plus the one new test, with zero failures and zero skips.

Phase 4's goal — callers reach the engine through one closed envelope that tells them nothing about
which modality answered, reachable identically in-process and over REST, including for streaming —
is achieved.

---

_Verified: 2026-09-07T04:00:00Z_
_Verifier: Claude (gsd-verifier)_

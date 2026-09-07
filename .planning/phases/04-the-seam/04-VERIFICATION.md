---
phase: 04-the-seam
verified: 2026-09-06T20:15:00Z
status: gaps_found
score: 12/13 must-haves verified
covered_files: [".planning/REQUIREMENTS.md", ".planning/ROADMAP.md", ".planning/phases/04-the-seam/04-01-PLAN.md", ".planning/phases/04-the-seam/04-01-SUMMARY.md", ".planning/phases/04-the-seam/04-02-PLAN.md", ".planning/phases/04-the-seam/04-02-SUMMARY.md", ".planning/phases/04-the-seam/04-03-PLAN.md", ".planning/phases/04-the-seam/04-03-SUMMARY.md", ".planning/phases/04-the-seam/04-04-PLAN.md", ".planning/phases/04-the-seam/04-04-SUMMARY.md", ".planning/phases/04-the-seam/04-05-PLAN.md", ".planning/phases/04-the-seam/04-05-SUMMARY.md", ".planning/phases/04-the-seam/04-CHECKPOINT-ANSWERS.md", ".planning/phases/04-the-seam/04-CONTEXT.md", ".planning/phases/04-the-seam/04-RESEARCH.md", ".planning/phases/04-the-seam/04-REVIEW-FIX.md", ".planning/phases/04-the-seam/04-REVIEW.md", ".planning/phases/04-the-seam/COVERAGE.md", "databasise/__init__.py", "databasise/ledger/ledger.py", "databasise/pyproject.toml", "databasise/seam/__init__.py", "databasise/seam/_base.py", "databasise/seam/engine.py", "databasise/seam/envelope.py", "databasise/seam/evidence.py", "databasise/seam/query.py", "databasise/seam/redact.py", "databasise/seam/refusals.py", "databasise/seam/rest.py", "databasise/seam/selectors.py", "databasise/seam/tokens.py", "databasise/seam/trace_store.py", "databasise/stores/vector.py", "databasise/tests/fixtures/wiring-harness.json", "databasise/tests/runner/test_measurement_posture.py", "databasise/tests/seam/__init__.py", "databasise/tests/seam/conftest.py", "databasise/tests/seam/test_alias_registry.py", "databasise/tests/seam/test_dual_transport.py", "databasise/tests/seam/test_envelope_schema.py", "databasise/tests/seam/test_evidence_refs.py", "databasise/tests/seam/test_leak.py", "databasise/tests/seam/test_mach11_event.py", "databasise/tests/seam/test_query_object.py", "databasise/tests/seam/test_rest_transport.py", "databasise/tests/seam/test_seam_tracer.py", "databasise/tests/seam/test_selectors.py", "databasise/tests/seam/test_token_accounting.py", "databasise/tests/seam/test_trace_token.py", "databasise/tests/test_embed_startup.py"]
covered_digest: "v1:sha256:0be29fda55291bda04fb4f875a864eeefb055bb92a857edd76ca50b01f60ddb4"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "The REST streaming endpoint and Databasise.query_stream() share one execution/serialization path, and a test proves REST's streamed output equals the in-process query_stream() counterpart's output for the same input (04-05-PLAN.md Task 2 acceptance criterion: 'a test asserts each [of the four §18 operations] returns the same value its in-process counterpart returns for the same input')."
    status: failed
    reason: >
      The CR-01 review fix (commit 8536200) moved envelope resolution into a FastAPI
      Depends()-injected dependency that calls Databasise.query() directly, and reimplemented the
      SSE event-shaping (`{"kind": "evidence", ...}` / `{"kind": "final", ...}`) inline inside
      rest.py's post_query_stream, instead of continuing to iterate Databasise.query_stream()'s own
      generator as 04-05 Task 2 originally built it. This was a necessary fix for the crash CR-01
      identified, but it was not accompanied by a corresponding update to query_stream() (still
      present, still described in engine.py's own module docstring as what "the REST layer
      iterates") or to 04-05-SUMMARY.md (still lists query_stream as the symbol the streaming
      endpoint iterates). A grep across the entire repository confirms Databasise.query_stream is
      called nowhere — not by rest.py, not by any test. It is an orphaned artifact: present,
      substantive, correctly implemented, and completely unwired. The REST and in-process streaming
      paths are now two independently maintained copies of the same event-shaping logic rather than
      one shared implementation — exactly the "one seam quietly becoming two" failure 04-05-PLAN.md's
      own prohibition names as the thing the promote decision in 04-01 exists to prevent. No test
      compares the two, so a future edit to one copy's event shape could silently diverge from the
      other with nothing in the suite to catch it.
    artifacts:
      - path: "databasise/seam/engine.py"
        issue: "Databasise.query_stream (lines 310-330) is a correct, tested-in-isolation-by-nothing async generator that is never called from production code or from any test — dead code relative to its own stated purpose"
      - path: "databasise/seam/rest.py"
        issue: "post_query_stream (lines 142-148) duplicates query_stream()'s event-shaping logic inline rather than iterating it, contradicting this module's own docstring claim ('iterates that same generator') and 04-05-SUMMARY.md's claim"
    missing:
      - "Either: wire post_query_stream to actually iterate engine.query_stream() (adjusting for the CR-01 refusal-timing fix, e.g. by pre-resolving the envelope via the same _execute() call query_stream() itself calls, then sharing the field-splitting helper rather than re-writing it) — or: delete Databasise.query_stream() and correct engine.py's module docstring plus 04-05-SUMMARY.md to state plainly that SSE shaping is REST-only, not a shared seam operation."
      - "A test asserting Databasise.query_stream()'s in-process output for a query equals /query/stream's REST output for the identical query — mirroring the existing evidence/trace in-process-vs-REST parity tests in test_rest_transport.py."
---

# Phase 4: The Seam — Verification Report

**Phase Goal:** Callers reach the engine through one closed envelope that tells them nothing about which modality answered
**Verified:** 2026-09-06
**Status:** gaps_found
**Re-verification:** No — initial verification

## Method

Read all five PLAN/SUMMARY pairs, 04-CONTEXT.md, 04-CHECKPOINT-ANSWERS.md, 04-REVIEW.md and
04-REVIEW-FIX.md, REQUIREMENTS.md and ROADMAP.md's Phase 4 entry, and CONTRACT.md §18. Then read
the actual current source of every file under `databasise/seam/` end to end (not the SUMMARY
descriptions of them), ran the seam test suite (115 passed) and the full suite with the `rest`
extra active (581 passed), and independently reproduced/attempted to falsify the review's own
governing question ("can you construct an envelope or a `resolve_trace` output that still leaks an
internal identity past the current gate?") against the code as it exists today, not as the fix
report describes it.

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP criterion / plan must-have) | Status | Evidence |
|---|------|--------|----------|
| 1 | Caller submits a §18.1 query object (never a string) via `Databasise.query`, no wiring/arm/node/instance identity in or out (criterion 1) | ✓ VERIFIED | `databasise/seam/query.py` `QueryObject` (5 members, `frozen=True, extra="forbid"`); `databasise/seam/engine.py` `Databasise.query`; `test_seam_tracer.py` asserts real answer text, not shape |
| 2 | Empty query object refused before any wiring resolves; unconsumable member refused by name (criterion 1, D-14) | ✓ VERIFIED | `query.py:check_consumable`, `EmptyQueryObjectError`/`UnconsumableQueryMemberError`; `test_query_object.py` spies `resolve_arm` never called on the empty path |
| 3 | Non-ASCII `text` round-trips byte-for-byte into the answer | ✓ VERIFIED | `test_query_object.py` non-ASCII + emoji round-trip assertion |
| 4 | All four §18.4 selectors resolve (alias, capability, harness, default); a selector naming a wiring/arm/node/instance-hash is refused at validation | ✓ VERIFIED | `databasise/seam/selectors.py` all four branches implemented; `Selector._no_instance_hash_shaped_values` validator; `test_selectors.py` |
| 5 | An unsatisfiable selector refuses by name, never falls back to default, and the refusal names nothing the machine holds | ✓ VERIFIED | `UnsatisfiableSelectorError`; `test_selectors.py` spies `_resolve_default` never called on the capability-refusal path; refusal-message assertions compare against `resolve_arm`'s real node/wiring ids at test time |
| 6 | Opaque-depth `provides` nodes excluded from the default selector only; still reachable by alias/capability/harness | ✓ VERIFIED | `selectors.py:_is_default_eligible`; `test_selectors.py` opaque-fixture-part test proves both halves |
| 7 | Alias registry read shape is defined (dedicated `alias` column per 04-03 checkpoint); empty/absent-alias refuse identically; alias resolution never appends to the ledger | ✓ VERIFIED | `ledger.py:Ledger.by_alias`; `selectors.py:_resolve_alias`; `test_alias_registry.py` asserts `Ledger.history` row count unchanged across resolution and a full query |
| 8 | Every answer carries evidence references (never inline content) that resolve back through the seam to the same store record; unresolvable ref raises; empty retrieval yields an empty (not omitted) list (criterion 2, API-05) | ✓ VERIFIED | `databasise/seam/evidence.py` `EvidenceRef`, `mint_evidence_refs`, `resolve_evidence_ref`; `Databasise.resolve_evidence`; `test_evidence_refs.py` |
| 9 | Evidence order preserves the store's own order; top-k boundary and score-tie ordering are pinned by explicit expected-id-sequence tests | ✓ VERIFIED | `test_evidence_refs.py` Task 2 tests, literal expected-id-list assertions, no re-sort in `engine.py` |
| 10 | Token accounting is a per-`counted_by` breakdown (never a merged scalar), deterministically ordered, zero-count entries present not omitted (criterion 3, API-11) | ✓ VERIFIED | `databasise/seam/tokens.py` `assemble_token_breakdown`; `test_token_accounting.py` multi-`counted_by`/zero-run/ordering-determinism tests |
| 11 | An `unbudgetable` participant produces an explicit refusal, never a substituted/estimated number; spend never conflated with capacity | ✓ VERIFIED | `tokens.py` `UnbudgetableParticipantError`; no allowance/capacity field on `TokenBreakdownEntry` |
| 12 | A `mutates_store` node reached outside its wiring's declared `deps` surfaces as a `SeamEvent` (`name@version`, spend, closed-vocabulary outcome); an in-`deps` mutation produces no event (criterion 2, MACH-11) | ✓ VERIFIED | `engine.py:_mach11_events`/`_accounted_store_keys`; `SeamEvent` with `Literal` outcome; `test_mach11_event.py` fixture-part pair proves both the positive and negative case, `name@version` compared against the registry's own value |
| 13 | The envelope carries an opaque trace reference; resolving it returns the node-by-node trace only when `debug=True`; unknown reference refuses; durable across a second `Databasise` instance at the same store root (criterion 4, API-10) | ✓ VERIFIED | `databasise/seam/trace_store.py` (`secrets.token_urlsafe(32)`, SQLite+WAL beside `ledger.db`); `Databasise.resolve_trace`; `test_trace_token.py` |
| 14 | `resolve_trace(debug=False)` never leaks `run_id`/`wiring_id`/`wiring_instance_hash`/`arm_id` (CR-02/CR-05, independently re-verified against live code, not the fix report) | ✓ VERIFIED | `engine.py:_NON_DEBUG_TRACE_FIELDS` explicit allow-list (not the original deny-list-of-one); `test_trace_token.py` set-intersection assertion; `test_leak.py`/`test_rest_transport.py` run the two-tier gate against the actual `debug=False` output, in-process and over REST |
| 15 | The two-tier leak gate catches a low-entropy identity leaking as a string *value* (not only as a dict key) — independently reproduced the review's own CR-04 exploit against current code | ✓ VERIFIED | `databasise/seam/redact.py` `assert_no_forbidden_values` (exact-match, scoped to non-`answer` fields); `test_leak.py`'s planted-leak negative control matches the review's exact reproduction (`SeamEvent.component = "chunk-vector"`) and fails as expected; a legitimate-word-in-`answer` positive control does not false-positive |
| 16 | `UnbudgetableParticipantError` never discloses the machine's own `node_id` in its message or REST body (CR-03) | ✓ VERIFIED | `tokens.py` stores it on `_internal_node_id` (leading underscore); `rest.py:_refusal_response` generically skips leading-underscore `vars(exc)` attributes; `test_rest_transport.py` asserts its absence from the body |
| 17 | `/query/stream` refusals return the documented non-success response rather than crashing the ASGI task group (CR-01) | ✓ VERIFIED | `rest.py`'s `_resolve_streamed_envelope` `Depends()` dependency resolves eagerly, before the SSE generator body runs; `test_rest_transport.py` posts an empty query and asserts `422` |
| 18 | The same seam is reachable two ways (in-process, REST) with identical behavior for query, evidence dereference and trace resolution — field-by-field, introspected, only `trace_token`/timing excluded (criterion 5, part) | ✓ VERIFIED | `test_dual_transport.py` (query, introspected field list); `test_rest_transport.py`'s evidence/trace parity tests compare REST JSON against `await rest_app.state.engine.resolve_evidence/resolve_trace(...)` directly |
| 19 | The same seam is reachable two ways with identical behavior for the **streaming** operation specifically — REST's SSE output proven equal to `Databasise.query_stream()`'s own in-process output for the same input (criterion 5, part; explicit 04-05-PLAN.md Task 2 acceptance criterion) | ✗ FAILED | See `gaps` below — `Databasise.query_stream()` is never called by `rest.py` or any test; only REST-streaming-vs-REST-non-streaming content equality is tested |
| 20 | Installing without the `rest` extra leaves the embedded dependency set unchanged; only an explicit `import databasise.seam.rest` raises, naming the extra | ✓ VERIFIED | `rest.py` module-scope `try/except ImportError` re-raise; `test_embed_startup.py::test_5` reads `importlib.metadata` `Requires-Dist` structurally (extra-gated vs unconditional), not just "does an import succeed today" |
| 21 | `rest.py` contains no selector resolution, no redaction, no envelope assembly — proven structurally, not by convention | ✓ VERIFIED | `test_rest_transport.py::test_rest_module_calls_no_selector_resolution_redaction_or_envelope_assembly_function` — AST-walks `rest.py`'s own call names against `selectors`/`redact`/`ResponseEnvelope`'s own `__all__` |
| 22 | Every seam refusal maps to a REST non-success response, enumerated from `SeamRefusalError.__subclasses__()` at runtime, never a hand-maintained list that could let a new refusal type fall through to a 500 | ✓ VERIFIED | `rest.py:create_app` registers one `app.add_exception_handler(SeamRefusalError, ...)`; `test_rest_transport.py` parametrizes over the discovered subclass set |

**Score:** 21/22 individual truths verified; 12/13 must-have-level items in the frontmatter's gap accounting (the one FAILED item covers both truth #19 and the corresponding must-have text).

### Deferred / Not-in-Scope (correctly disclosed, not gaps)

- The alias registry is empty this phase by design (Phase 7 populates it) — confirmed correct, not re-raised.
- Unauthenticated REST surface — disclosed, accepted, `transfer` disposition; no requirement asks for auth.
- MACH-11's event is proven only against fixture parts, since no `parts_core` part declares `mutates_store` — disclosed in `04-04-SUMMARY.md` and `engine.py`'s own docstring; the correlation rule itself (FA-08) is sound and independently readable.
- EMBED-02's MCP half is a CONTEXT.md Deferred Idea for a later phase; COVERAGE.md records this as an explicit `OPT-OUT`, not silently.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `databasise/seam/query.py` | §18.1 query object + consumption check | ✓ VERIFIED | `QueryObject`, `check_consumable` |
| `databasise/seam/envelope.py` | §18.2 closed envelope, strict at every depth | ✓ VERIFIED | `ResponseEnvelope`, `SeamEvent`, all inherit `_StrictModel` |
| `databasise/seam/engine.py` | The `Databasise` seam object | ✓ VERIFIED | `query`, `query_stream` (orphaned, see gap), `resolve_evidence`, `resolve_trace`, `_execute` |
| `databasise/seam/refusals.py` | Typed refusal hierarchy | ✓ VERIFIED | Base + 4 subclasses, no-enumeration rule honored throughout |
| `databasise/seam/selectors.py` | All four §18.4 selectors | ✓ VERIFIED | default/capability/alias/harness, opaque exclusion |
| `databasise/seam/evidence.py` | Evidence ref mint/resolve | ✓ VERIFIED | `EvidenceRef`, `mint_evidence_refs`, `resolve_evidence_ref` |
| `databasise/seam/tokens.py` | `counted_by` breakdown | ✓ VERIFIED | `TokenBreakdownEntry`, `assemble_token_breakdown`, `UnbudgetableParticipantError` |
| `databasise/seam/trace_store.py` | Durable trace persistence | ✓ VERIFIED | SQLite+WAL, random token, `UnknownTraceReferenceError` |
| `databasise/seam/redact.py` | Two-tier leak gate | ✓ VERIFIED | `forbidden_identities`, `assert_no_forbidden_keys`, `assert_no_forbidden_values` (CR-04) |
| `databasise/seam/rest.py` | Optional REST transport | ⚠️ ORPHANED (partial) | Non-streaming/evidence/trace endpoints thin and verified; streaming endpoint duplicates rather than reuses `Databasise.query_stream` |
| `.planning/phases/04-the-seam/COVERAGE.md` | API coverage record | ✓ VERIFIED | Reasoned no-external-API declaration + exposed-operation matrix, matches shipped surface |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `engine.py` | `runner/scheduler.py` | `run_wiring(...)` | ✓ WIRED | Same call shape as `run_arm.py` |
| `engine.py` | `wirings/resolve.py` | `resolve_arm`/`provides` off raw dict | ✓ WIRED | `resolve_selector` returns raw dict; `provides` never read off `ParsedWiring` |
| `evidence.py` | `stores/vector.py` | mint/resolve via store's own item shape | ✓ WIRED | `resolve_evidence_ref` calls `vector_store.select(...).get_by_id(...)` |
| `tokens.py` | `runner/trace.py` | `counted_by` grouped verbatim | ✓ WIRED | `assemble_token_breakdown` |
| `selectors.py` | `ledger/ledger.py` | `Ledger.by_alias`, read-only | ✓ WIRED | Row-count-unchanged test proves no append |
| `rest.py` | `engine.py` | `Databasise.query`/`resolve_evidence`/`resolve_trace` | ✓ WIRED | Non-streaming query, evidence, trace endpoints call the identical in-process method |
| `rest.py` | `engine.py` | `Databasise.query_stream` | ✗ NOT WIRED | Declared as this plan's own deliverable ("the streaming endpoint... iterates that same generator") but never called; `post_query_stream` reimplements the shaping instead — see gap |
| `rest.py` | `redact.py` | leak gate imported, not reimplemented | ✓ WIRED | `test_rest_transport.py` imports the same functions `test_leak.py` does |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full seam suite | `cd databasise && uv run --extra rest pytest -q tests/seam/` | 115 passed | ✓ PASS |
| Full repo suite, REST extra active | `cd databasise && uv run --extra rest pytest -q` | 581 passed | ✓ PASS |
| Embeddability: no REST import at module scope | `uv run python -c "from databasise.seam import Databasise, QueryObject, ResponseEnvelope, Selector"` | `ok` | ✓ PASS |
| REST extra installable and importable | `uv run --extra rest python -c "from databasise.seam.rest import create_app"` | `ok` | ✓ PASS |
| Import boundary (no v1 imports from `seam`) | `uv run python -m databasise.tools.check_import_boundary` | exit 0, no violation lines | ✓ PASS |
| CR-04 exploit reproduction, independently re-run against current code | `test_the_value_check_fails_on_a_node_id_planted_as_a_seam_events_component_value` | raises `AssertionError` as expected (gate now catches it) | ✓ PASS |
| `Databasise.query_stream()` called anywhere in the repo | `grep -rn "\.query_stream(" databasise/` | no matches | ✗ FAIL (confirms the gap) |

### Requirements Coverage

| Requirement | Source Plan(s) | Status | Evidence |
|---|---|---|---|
| API-03 | 04-01, 04-03 | ✓ SATISFIED | Query object, four selectors, refusal-by-name, opaque exclusion — all independently verified above |
| API-04 | 04-05 | ⚠️ PARTIALLY SATISFIED | REST SSE streaming works and content-matches REST's own non-streaming endpoint (tested); the in-process/REST streaming parity the plan's own acceptance criteria required is not proven — see gap |
| API-05 | 04-02 | ✓ SATISFIED | Evidence refs, deref-raising, ordering/top-k pinned |
| API-10 | 04-04 | ✓ SATISFIED | Trace reference, debug gating, durability, non-debug leak fixed and independently re-verified |
| API-11 | 04-02 | ✓ SATISFIED | Per-`counted_by` breakdown, `unbudgetable` refusal, spend/capacity separation |
| EMBED-02 | 04-05 | ✓ SATISFIED (REST half; MCP explicitly deferred, disclosed in COVERAGE.md) | Extra-gated dependency, structural proof via `Requires-Dist`, AST-walk proving no logic in the transport |
| MACH-11 | 04-04 | ✓ SATISFIED | Out-of-`deps` correlation rule, `SeamEvent`, closed outcome vocabulary, fixture-proven both directions |

No orphaned requirements: the seven IDs ROADMAP maps to Phase 4 are exactly the seven IDs the five plans' `requirements:` frontmatter fields declare, together.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `databasise/seam/engine.py` | 310-330 | Declared "new symbol" (`query_stream`) that is never called in production or by any test | ⚠️ Warning (elevated to gap, see below) | Dead code relative to its own stated purpose; risk of silent behavioral drift between the two streaming implementations |
| `databasise/seam/rest.py` | 142-148 | Streaming endpoint reimplements event-shaping logic instead of reusing the seam's own generator | ⚠️ Warning (elevated to gap, see below) | Violates 04-05-PLAN.md's own stated prohibition ("the REST layer must not acquire logic of its own... one seam quietly becoming two") |
| `.planning/phases/04-the-seam/04-05-SUMMARY.md` / `04-04-SUMMARY.md` provides lists, `engine.py` module docstring | — | Stale claim: describes `query_stream` as what the REST layer iterates, which stopped being true after the CR-01 fix (commit `8536200`) and was never corrected | ℹ️ Info | Documentation drift — SUMMARY.md is not evidence, confirmed here by reading the actual current source |

No `TBD`/`FIXME`/`XXX` markers found in any file this phase modified. No stub returns, no hardcoded-empty props, no placeholder text.

## Independent Fix Verification (per this task's explicit instruction)

Re-derived, rather than trusted, each of the review's 5 Critical + 3 Warning findings against the
code as it exists today:

- **CR-01** (streaming refusal crash): fixed and verified — `Depends()`-based eager resolution, tested with a `422` assertion. ✓
- **CR-02/CR-05** (`resolve_trace(debug=False)` leak): fixed and verified — explicit allow-list, tested both in-process and over REST, against the real production method. ✓
- **CR-03** (`node_id` disclosure): fixed and verified — private attribute, generic underscore-skip in the REST handler, test asserts the leak's absence rather than its presence. ✓
- **CR-04** (value-leak blind spot): fixed and verified — independently re-ran the review's own exploit (`SeamEvent.component = "chunk-vector"`) as a negative-control test; it now fails the gate as intended, and a legitimate-word-in-`answer` case does not false-positive. Also confirmed `run_id` was added to the high-entropy forbidden set. ✓
- **WR-01/WR-02/WR-03**: each independently re-read in `engine.py`/`evidence.py` and confirmed to match the fix report's description. ✓

**One new finding, not in the original review, surfaced by this independent pass:** the CR-01 fix's
own side effect — `Databasise.query_stream()` orphaned, REST streaming reimplementing its logic
instead of reusing it — is real, reproducible (`grep` confirms zero callers), and contradicts both
`engine.py`'s own module docstring and `04-05-SUMMARY.md`'s claims. See `gaps` in the frontmatter.

## Gaps Summary

One gap, scoped narrowly: the REST layer's server-sent-event streaming endpoint no longer shares
implementation with `Databasise.query_stream()`, the in-process streaming operation 04-05 built for
exactly that purpose. This is a side effect of the CR-01 review fix (which was itself a correct and
necessary fix for a real crash) that was not reconciled with the design it changed. Functionally,
REST streaming still works correctly and content-matches REST's own non-streaming endpoint — this is
not a broken feature from a consumer's point of view. It is a broken guarantee: the specific,
written acceptance criterion that both transports' streaming behavior be proven identical by
sharing one execution path is no longer true, and no test would catch a future divergence between
the two copies.

Recommended closure: either wire `post_query_stream` to genuinely iterate
`Databasise.query_stream()` (restructuring around the CR-01 fix's own eager-resolution requirement),
or deliberately retire `query_stream()` as a public seam operation and correct the two now-inaccurate
docstring/SUMMARY claims that describe it as shared. Either resolves the gap; leaving both
`query_stream()` and the duplicated REST logic in place, silently diverging over time, does not.

---

_Verified: 2026-09-06_
_Verifier: Claude (gsd-verifier)_

---
phase: 04-the-seam
reviewed: 2026-09-06T00:00:00Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - databasise/seam/engine.py
  - databasise/seam/envelope.py
  - databasise/seam/query.py
  - databasise/seam/refusals.py
  - databasise/seam/selectors.py
  - databasise/seam/evidence.py
  - databasise/seam/tokens.py
  - databasise/seam/trace_store.py
  - databasise/seam/redact.py
  - databasise/seam/rest.py
  - databasise/seam/_base.py
  - databasise/seam/__init__.py
  - databasise/__init__.py
  - databasise/ledger/ledger.py
  - databasise/stores/vector.py
  - databasise/pyproject.toml
  - databasise/tests/seam/conftest.py
  - databasise/tests/seam/test_seam_tracer.py
  - databasise/tests/seam/test_query_object.py
  - databasise/tests/seam/test_envelope_schema.py
  - databasise/tests/seam/test_evidence_refs.py
  - databasise/tests/seam/test_token_accounting.py
  - databasise/tests/seam/test_selectors.py
  - databasise/tests/seam/test_alias_registry.py
  - databasise/tests/seam/test_trace_token.py
  - databasise/tests/seam/test_mach11_event.py
  - databasise/tests/seam/test_leak.py
  - databasise/tests/seam/test_rest_transport.py
  - databasise/tests/seam/test_dual_transport.py
  - databasise/tests/test_embed_startup.py
  - databasise/tests/runner/test_measurement_posture.py
  - databasise/tests/fixtures/wiring-harness.json
findings:
  critical: 5
  warning: 3
  info: 0
  total: 8
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-09-06
**Depth:** standard
**Files Reviewed:** 27 (plus one JSON fixture)
**Status:** issues_found

## Summary

The happy-path seam is well built and the house style (typed refusals, closed strict Pydantic
models, order-preserving evidence, per-`counted_by` token breakdown) is followed carefully and
tested with real values, not shape alone. The four load-bearing claims mostly hold for the paths
the test suite exercises. But every one of the five Critical findings below is a path the test
suite does **not** exercise, and every one is a live, reproduced violation of the phase's own
central promise — "no wiring name, arm name, node id or instance hash crossing the boundary in
either direction" — or of the "thin adapter, provably" claim for the REST transport. I reproduced
all five findings by running the actual code (not by inspection alone); reproduction scripts and
output are inlined below each finding.

The two-tier leak gate (`redact.py`) is real and does what its own docstring says: high-entropy
substring search plus a low-entropy structural key-walk. What it does **not** do — and what its own
docstring never claims it does — is inspect low-entropy identities that leak as plain string
*values* rather than dict *keys*. I constructed an envelope that leaks a real node id through
`SeamEvent.component` and it passes both tiers cleanly (CR-04). Separately, `resolve_trace(debug=
False)` — one of the seam's own three declared §18 operations — never filters `wiring_id`,
`wiring_instance_hash`, `arm_id`, or `run_id` out of its return value, only `nodes`; every one of
those four internal identities crosses the boundary today, in both the in-process API and the REST
`/trace/resolve` endpoint, and no test in this phase's suite ever runs the leak gate against that
code path (CR-02). The REST streaming endpoint's refusal mapping — the one property T-04-27 exists
to guarantee — does not fire at all for `/query/stream`: every `SeamRefusalError` raised during
`_execute()` crashes the ASGI task group with an unhandled `ExceptionGroup` instead of returning the
documented non-success response (CR-01). And one refusal type, `UnbudgetableParticipantError`,
embeds a real internal `node_id` directly in its own message and (via the REST handler's generic
`vars(exc)` dump) in the JSON response body — the sole refusal among seven that names something
other than the consumer's own input, and `test_rest_transport.py`'s own parametrized test currently
*requires* this leak to keep passing (CR-03).

## Critical Issues

### CR-01: `/query/stream` refusals crash instead of returning the documented non-success response

**File:** `databasise/seam/rest.py:116-119`, `databasise/seam/engine.py:243-263`

**Issue:** `post_query_stream` is an `async def` **generator** function. `engine.query_stream()`'s
own body calls `await self._execute(...)` (the call that can raise any `SeamRefusalError`) before
its first `yield`. Because a generator's body does not run until first iterated, FastAPI's SSE
producer machinery has already begun constructing the streaming response by the time `_execute()`
raises — so the refusal never reaches `app.add_exception_handler(SeamRefusalError, ...)` at all. It
propagates as an unhandled `ExceptionGroup` out of `anyio`'s task group, breaking the connection
instead of returning the `422` every other endpoint returns for the identical refusal. This
directly contradicts the module's own docstring claim ("One application-level exception handler
maps every `SeamRefusalError` subclass to a non-success response... so a refusal type added later
cannot silently fall through to a generic 500") — for this endpoint, *every* refusal type falls
through, not just one added later. No test in `test_rest_transport.py` or `test_dual_transport.py`
exercises a refusal via `/query/stream`; every refusal-mapping test uses the non-streaming
`/_test/raise/{class_name}` route.

Reproduced live:
```
$ uv run python probe.py   # POST /query/stream {"query": {}} — an empty QueryObject
...
ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  File "databasise/seam/rest.py", line 118, in post_query_stream
    async for event in engine.query_stream(body.query, body.selector):
  File "databasise/seam/engine.py", line 260, in query_stream
    envelope = await self._execute(query_object, selector)
  File "databasise/seam/query.py", line 78, in check_consumable
    raise EmptyQueryObjectError(query_object)
databasise.seam.refusals.EmptyQueryObjectError: query object carries no set member: ...
```
The exception propagates all the way out to the test client (no status code — the connection
itself fails), not a `422`.

**Fix:** Wrap the `_execute()` call inside the streaming generator in a `try`/`except
SeamRefusalError` and translate it into the SSE stream's own error convention (e.g. a final
`{"kind": "refusal", ...}` event before closing, since headers/status are already committed once
streaming starts), or — simpler — resolve the envelope in the route handler *before* entering the
generator, so the existing app-level handler catches it before any response has started:
```python
@app.post("/query/stream", response_class=EventSourceResponse)
async def post_query_stream(body: QueryRequest):
    envelope = await engine._execute(body.query, body.selector)  # raises -> caught by app handler
    async def _events():
        for ref in envelope.evidence:
            yield {"kind": "evidence", "evidence": ref.model_dump()}
        yield {"kind": "final", **envelope.model_dump(exclude={"evidence"})}
    return _events()
```
Add a test that POSTs an empty query object to `/query/stream` and asserts a `422`, mirroring the
non-streaming refusal-mapping test.

---

### CR-02: `resolve_trace(debug=False)` leaks `wiring_id`, `wiring_instance_hash`, `arm_id`, and `run_id`

**File:** `databasise/seam/engine.py:394-406`

**Issue:** The docstring states: "without [debug], the `nodes` key is stripped so a caller that did
not ask for internal node identities does not receive them." The implementation only strips
`nodes`:
```python
async def resolve_trace(self, trace_reference: str, *, debug: bool = False) -> dict[str, Any]:
    record = self._trace_store.resolve(trace_reference)
    if debug:
        return record
    return {key: value for key, value in record.items() if key != "nodes"}
```
`wiring_id`, `wiring_instance_hash`, `arm_id`, and `run_id` are top-level `RunRecord` fields — the
exact internal identities §18.2 forbids a consumer from receiving ("A consumer MUST NOT receive a
field that names a wiring... an instance hash, or any other internal identity") — and every one of
them survives the non-debug filter unchanged. This is not a hypothetical: it is the seam's own
third declared §18 operation, reachable both in-process and via `POST /trace/resolve` with
`"debug": false`, with no additional filtering at the REST layer.

Reproduced live (real run against a synthetic store, default `debug=False`):
```
non-debug resolve_trace() keys: ['arm_execution_order', 'arm_id', 'bundle_ref',
  'concurrency_setting', 'corpus_snapshot_hash', 'degradation_reason', 'degraded',
  'determinism_setting', 'executor_version', 'partial', 'run_id', 'stop_reason',
  'wiring_id', 'wiring_instance_hash']
  wiring_id present: True -> lightrag-base
  wiring_instance_hash present: True -> sha256:76789588ee36ed8a28e3860f0ca6602b0eed9c50c002323cfc22df68198dc545
  arm_id present: True -> seam
  run_id present: True -> 8edfa14b-8f01-4bff-a093-9c44e08dc0b2
```
No test in `test_trace_token.py` or `test_rest_transport.py` checks for the absence of these
fields in the non-debug path — `test_exchanging_the_reference_without_debug_carries_no_node_level_
entry` only asserts `"nodes" not in non_debug_record`. Every leak-gate run in `test_leak.py`/
`test_rest_transport.py` exercises either the envelope or the `debug=True` trace record — never
`resolve_trace(debug=False)`'s own output — so this leak is invisible to the phase's own gate.

**Fix:** Filter to an explicit allow-list (mirroring the strict-model pattern used everywhere else
in this package) rather than a deny-list of one key:
```python
_NON_DEBUG_TRACE_FIELDS = {
    "partial", "degraded", "stop_reason", "degradation_reason",
    "bundle_ref", "corpus_snapshot_hash", "executor_version",
    "concurrency_setting", "determinism_setting", "arm_execution_order",
}
return {k: v for k, v in record.items() if k in _NON_DEBUG_TRACE_FIELDS}
```
Add a test asserting `{"wiring_id", "wiring_instance_hash", "arm_id", "run_id"} & non_debug_record
.keys() == set()`, and extend `test_leak.py`/`test_rest_transport.py`'s gate runs to cover the
non-debug `resolve_trace`/`/trace/resolve` output, not only the `debug=True` path.

---

### CR-03: `UnbudgetableParticipantError` discloses a real internal `node_id` in its own message and REST body

**File:** `databasise/seam/tokens.py:52-62`, `databasise/seam/rest.py:80-92`

**Issue:** `refusals.py`'s own module docstring states the house rule for every seam refusal: "a
seam refusal names only the consumer's own input... never what the machine has." Every refusal
type except one honors this (`selector_kind`/`requested`, `member_name`, `trace_reference`,
`query_object`, evidence `ref` — all consumer-supplied values). `UnbudgetableParticipantError` is
the exception:
```python
class UnbudgetableParticipantError(SeamRefusalError):
    def __init__(self, node_id: str):
        self.node_id = node_id
        super().__init__(
            f"node {node_id!r} is admitted unbudgetable; no token comparison may include it"
        )
```
`node_id` here is the *machine's own* internal wiring-node identity (e.g. `"chunk-vector"` in a
real run) — not consumer input. It is embedded directly in the exception message, and
`rest.py`'s `_refusal_response` generically dumps every `vars(exc)` attribute into the JSON body,
so the REST client receives it a second time as a top-level `node_id` key.

Reproduced live:
```
>>> _refusal_response(None, UnbudgetableParticipantError("chunk-vector"))
422 b'{"refusal_type":"UnbudgetableParticipantError","message":"node \'chunk-vector\' is admitted
unbudgetable; no token comparison may include it","node_id":"chunk-vector"}'
```
`test_rest_transport.py`'s own `test_every_refusal_subclass_maps_to_a_non_success_status_carrying_
its_named_value` currently *asserts* `body.get("node_id") == "chunk-vector"` for this factory,
meaning the test suite enshrines the leak as expected behavior rather than catching it.

**Fix:** Do not carry the wiring's own `node_id` on this refusal at all — the phase's own precedent
(`refusals.py`'s selector refusals) shows the fix is to name only what the consumer can act on. If a
caller-facing signal is still wanted, drop it or replace it with a redacted counter/ordinal ("the
Nth participant declared unbudgetable") rather than the raw node id:
```python
class UnbudgetableParticipantError(SeamRefusalError):
    def __init__(self, node_id: str):
        self._internal_node_id = node_id  # never exposed via message or vars()
        super().__init__("a participant is admitted unbudgetable; no token comparison may include it")
```
and update the REST refusal test's factory/assertions accordingly rather than asserting the leak.

---

### CR-04: The two-tier leak gate never inspects low-entropy identities that leak as string *values*

**File:** `databasise/seam/redact.py:47-59` (`assert_no_forbidden_keys`)

**Issue:** The low-entropy tier is exclusively a dict-*key* walk ("it never inspects string
content, only dict keys, at every nesting depth"). That rationale is sound for genuinely freeform
fields (`answer`, corpus-derived evidence content) where a legitimate word could collide with a
node id. But it is applied uniformly to every field, including structured, non-freeform,
program-controlled string fields — `SeamEvent.component`, `stop_reason`, `degradation_reason`,
`EvidenceRef.kind` — where a value-level check would produce no false positive and would catch
exactly the leak class this gate exists for. I constructed an envelope carrying a real node id
(`"chunk-vector"`) as the *value* of `SeamEvent.component` and ran both gate tiers against it:

```
low entropy forbidden set: {'chunk-vector', 'seam', 'lightrag-base'}
dumped: {..., 'seam_events': [{'component': 'chunk-vector', 'spend': None, 'outcome': 'completed'}]}
high-entropy tier: PASSED (no hash found, as expected)
low-entropy structural tier: PASSED <-- despite 'chunk-vector' (a real node_id) sitting in
  seam_events[0].component
```
Both tiers pass cleanly. This is precisely the case the review's own governing question asks for:
"Can you construct an envelope that leaks an internal identity and still passes this gate?" — yes.
There is no negative control in `test_leak.py` for a low-entropy *value* leak (only a key leak and a
high-entropy value leak are proven to fail the gate), which is itself the tell: such a control would
immediately show the gate passing a real leak.

Related, narrower gap in the same module: `forbidden_identities()` never adds `run_id` to either
forbidden set, even though `run_id` matches the same identity-name pattern the sibling test
(`test_envelope_schema.py`'s `_IDENTITY_NAME_PATTERN`) already uses to classify `RunRecord` fields
as internal identities. This is exactly why CR-02's `run_id` leak was never caught by this gate.

**Fix:** Add a value-level low-entropy check scoped to the envelope's own non-freeform string
fields (everything except `answer` and evidence/tier content that is legitimately derived from a
corpus) — e.g. walk every string leaf whose containing key is not on an explicit "freeform" allow
list (`{"answer"}`) and assert it does not *equal* a forbidden low-entropy value. Add `run_id` to
`forbidden_identities()`'s high-entropy set (it is a random UUID, so the existing substring-search
tier is the correct home for it). Add a negative control proving a value-leak (like the one
reproduced above) fails the strengthened gate.

---

### CR-05: `resolve_trace`'s non-debug filtering has no test coverage against the leak gate at all

**File:** `databasise/tests/seam/test_leak.py`, `databasise/tests/seam/test_rest_transport.py`

**Issue:** Grouping this separately from CR-02 because it is a distinct, fixable process gap: every
leak-gate assertion in this phase's suite runs against either `ResponseEnvelope.model_dump_json()`
or `resolve_trace(debug=True)`/`POST /trace/resolve {"debug": true}`. The one output that is
actually the *default*, consumer-facing shape of the seam's third §18 operation —
`resolve_trace(debug=False)` / `POST /trace/resolve {"debug": false}` — is never run through
`forbidden_identities()`/`assert_no_forbidden_keys()` by any test. This is how CR-02 shipped
unnoticed despite the phase building a purpose-made two-tier gate specifically to prevent this
class of bug.

**Fix:** Add a `debug=False` leak-gate run alongside the existing `debug=True` one in both
`test_leak.py` and `test_rest_transport.py`.

## Warnings

### WR-01: Multiple `provides` nodes silently last-write-wins for `answer`/`depth_label`

**File:** `databasise/seam/engine.py:336-344`

**Issue:**
```python
for node in record.nodes:
    if node.node_id not in provides:
        continue
    depth_label = node.effective_depth
    output = provided.get(node.node_id)
    if isinstance(output, dict) and "completion" in output:
        answer = str(output["completion"])
```
Iterates `record.nodes` (scheduler dispatch order), not `provides` (the wiring's own declared
order) — if a future wiring declares more than one `provides` position, whichever provides-node
happens to appear last in dispatch order silently wins for both `answer` and `depth_label`, with no
signal in the envelope that a choice was made among several. Today `naive`'s `provides` is a
single-element list so this is dormant, but it is exactly the kind of implicit, order-dependent
behavior the phase's own house style (explicit refusals over silent narrowing) argues against
elsewhere.

**Fix:** Iterate `provides` (not `record.nodes`) and raise or document the tie-break explicitly if
more than one node in `provides` produces a `completion`, rather than relying on incidental
dispatch order.

### WR-02: `_mach11_events`'s "node not found" fallback fabricates a zero-count spend, untested

**File:** `databasise/seam/engine.py:195-200`

**Issue:**
```python
node_trace = node_by_id.get(node_id)
spend = (
    TokenBreakdownEntry(**node_trace.tokens.to_dict())
    if node_trace is not None
    else TokenBreakdownEntry(counted_by="none")
)
```
When a mutating node's own trace is missing, this reports a confident `counted_by="none"`,
zero-count entry rather than refusing or reporting the spend as genuinely unknown — in tension with
`UnbudgetableParticipantError`'s own stated principle ("a plausible-looking fabricated count is
worse than a refusal because it reads as measured"). No test in `test_mach11_event.py` or
`test_leak.py` exercises `node_by_id.get(node_id) is None`; every fixture registers the mutating
node so its trace is always present. This branch is currently dead in test coverage.

**Fix:** Either prove this branch is unreachable in production and delete it, or give it a
sentinel `counted_by` value (e.g. `"unknown"`, distinct from the real `"none"`) so a reader cannot
mistake "we never saw this node's trace" for "this node genuinely spent zero tokens."

### WR-03: `mint_evidence_refs` raises a raw `KeyError` instead of a named refusal for a malformed item

**File:** `databasise/seam/evidence.py:81-84`

**Issue:**
```python
return [
    EvidenceRef(ref=str(item["id"]), namespace=namespace, kind=kind, score=item.get("score"))
    for item in items
]
```
`item["id"]` is unguarded; a retrieval item missing an `"id"` key (e.g. a future retrieval node
returning a differently-shaped item) raises a bare `KeyError` rather than a named, informative
refusal — inconsistent with this phase's own stated house style ("refusals over silent
fallbacks... a named exception carrying the specifics") used everywhere else in `seam/`
(`VectorNamespaceNotSelectedError`, `VectorStoreCorruptedError`, every `SeamRefusalError`
subclass).

**Fix:** `item.get("id")` with an explicit check, raising a named `SeamRefusalError` subclass (or
at minimum a clear `ValueError`) naming the malformed item's namespace/index rather than letting
`KeyError: 'id'` propagate raw.

---

_Reviewed: 2026-09-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

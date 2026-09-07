---
phase: 04-the-seam
plan: 04
subsystem: api
tags: [seam, pydantic, trace-store, mach11, leak-gate, lightrag]

requires:
  - phase: 04-the-seam (plans 01-03)
    provides: "databasise.seam.Databasise, the QueryObject/ResponseEnvelope/Selector shapes, the
      SeamRefusalError base class, the declared-but-empty trace_token/seam_events envelope fields,
      and the four §18.4 selectors this plan's leak test reuses (resolve_arm, _build_stores,
      _inject_query/_inject_token_allowance)"
provides:
  - "databasise.seam.trace_store.TraceStore — durable RunRecord persistence keyed by an opaque
    secrets.token_urlsafe reference (API-10, D-06); databasise.seam.engine.Databasise.resolve_trace,
    the third §18 seam operation"
  - "databasise.seam.engine._accounted_store_keys / _mach11_events — the FA-08 correlation rule
    that turns an out-of-deps mutates_store touch into a databasise.seam.envelope.SeamEvent"
  - "databasise.seam.envelope.SeamEvent.outcome as a closed Literal (\"completed\"/\"halted\"/\"failed\")"
  - "databasise.seam.redact.forbidden_identities / assert_no_forbidden_keys — the two-tier D-05
    leak gate, shipped as library code for 04-05's REST transport to reuse"
affects: [04-05-rest-transport, 07-promote-rollback]

actuals:
  tokens: 13637
  tasks: 3
  commits: 3
  plan_head_before: d6b0153bb9761444651cf28077215293eab3824e

tech-stack:
  added: []
  patterns:
    - "Random, not derived, opaque tokens: secrets.token_urlsafe backing a durable SQLite lookup
      table, following ledger.py's own schema/WAL/row-round-trip pattern at a sibling database
      file (trace.db) rather than overloading ledger.db"
    - "A correlation rule stated once in the producing module's own docstring (engine.py), not
      CONTRACT — FA-08's own discretion note, explicit about its own provenance and narrowness"
    - "A structural-only check for low-entropy identity leaks (dict keys, never substring text),
      paired with an unconditional substring check for high-entropy identities — two tiers, never
      one blind search, so a corpus containing an ordinary word like a node id's name can never
      false-positive the gate"
    - "Bypassing an unrelated architectural gap (D-08's in-process-only hosting) by calling the
      scheduler's own production touch-recording class directly for a fixture node that cannot
      complete real dispatch, rather than fabricating the touch tuple by hand or changing the
      hosting gate itself"

key-files:
  created:
    - databasise/seam/trace_store.py
    - databasise/seam/redact.py
    - databasise/tests/seam/test_trace_token.py
    - databasise/tests/seam/test_mach11_event.py
    - databasise/tests/seam/test_leak.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/envelope.py

key-decisions:
  - "The token is secrets.token_urlsafe(32) (256 bits) — random, never derived from canonicalise
    over any run field — per D-06's own prohibition against a decodable trace reference, recorded
    in trace_store.py's own module docstring."
  - "resolve_trace's non-debug path strips exactly the `nodes` key from the resolved run record,
    keeping every other run-level field (T-04-19's own framing: node-level identities are gated,
    not the whole record) — Claude's Discretion since neither CONTRACT nor 04-CONTEXT.md names the
    exact non-debug field set."
  - "SeamEvent.outcome's closed vocabulary (completed/halted/failed) is Claude's Discretion (no
    CONTRACT vocabulary exists for this event); halted is derived from the node's own
    budget_state, completed is the default, failed is declared but unreached by any path this
    plan exercises."
  - "The MACH-11 correlation rule (FA-08) reads a touching node's own declared `deps`, and for
    each dependency, the store key any reads_*/writes_* effect on that dependency's OWN resolved
    Part names — never mutates_store itself, which is deliberately opaque about which store it
    touches (§2). A touched key no dependency accounts for is out-of-deps."
  - "A genuine, orthogonal architectural gap was discovered and worked around, not silently
    papered over: databasise.validator.execution_mode.derive_execution_mode routes ANY Part
    declaring mutates_store to the confined-unit placement, and Phase 1's host() (D-08) hosts
    in-process only — so no Part declaring mutates_store can complete real dispatch under the
    current runner, ever, regardless of what else it declares. Both mach11 tests and the leak
    test work around this by calling the scheduler's own _ScopedStoresView directly for the
    un-hostable node, producing a real touch through the exact production code path a hosted
    node's body would use, rather than fabricating a bare tuple or changing D-08's hosting scope."
  - "The leak test cannot use Databasise.query() directly: no selector this phase implements can
    route a caller to a custom wiring (the four selectors only ever resolve the five committed
    LightRAG arms, or a ledger alias pointing at one of them). It instead replicates query()'s own
    internal assembly directly over resolve_arm(\"naive\") plus one spliced-in out-of-deps
    mutating fixture node — reusing engine.py's own functions verbatim, never a re-implementation."

patterns-established:
  - "A leak/redaction gate ships as library code under the module it protects (databasise/seam/),
    never as test-only helper code, whenever more than one transport (REST, in-process) must
    assert against the identical check."

requirements-completed: [API-10, MACH-11]

coverage:
  - id: D1
    description: "A completed query's envelope carries a non-empty trace reference that equals,
      and does not contain, the run's own run_id/wiring_id/wiring_instance_hash/arm_id/node
      instance_hash/node_id — and vice versa"
    requirement: "API-10"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_trace_token.py::test_the_trace_reference_reveals_none_of_the_runs_own_identities"
        status: pass
    human_judgment: false
  - id: D2
    description: "Exchanging the reference with debug=True returns the run's own node-by-node
      trace; without debug, the nodes key is stripped from the resolved record"
    requirement: "API-10"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_trace_token.py::test_exchanging_the_reference_with_debug_returns_the_runs_own_node_entries, ::test_exchanging_the_reference_without_debug_carries_no_node_level_entry"
        status: pass
    human_judgment: false
  - id: D3
    description: "An unknown trace reference raises UnknownTraceReferenceError by exception type,
      never None or a partial record"
    requirement: "API-10"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_trace_token.py::test_an_unknown_trace_reference_raises_the_named_refusal"
        status: pass
    human_judgment: false
  - id: D4
    description: "A reference minted by one Databasise instance resolves through a second instance
      constructed against the same store root — durability across the minting process"
    requirement: "API-10"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_trace_token.py::test_a_reference_minted_by_one_instance_resolves_through_a_second_instance_same_store_root"
        status: pass
    human_judgment: false
  - id: D5
    description: "Two runs of the same query mint two different references, each resolving to its
      own record; the trace database is created beside ledger.db under the store root"
    requirement: "API-10"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_trace_token.py::test_two_runs_of_the_same_query_mint_two_different_references_each_resolving_to_its_own_record, ::test_the_trace_database_is_created_beside_the_ledger_database_under_the_store_root"
        status: pass
    human_judgment: false
  - id: D6
    description: "An out-of-deps mutates_store touch yields exactly one SeamEvent naming the
      part's verbatim registered name@version; the same wiring shape with the touch accounted for
      by a declared dependency yields none"
    requirement: "MACH-11"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_mach11_event.py::test_an_out_of_deps_mutation_yields_exactly_one_event_and_the_in_deps_mutation_yields_none, ::test_the_events_component_equals_the_out_of_deps_parts_registered_name_at_version"
        status: pass
    human_judgment: false
  - id: D7
    description: "A zero-spend event carries a present spend member, zero counts, and a
      non-empty counted_by — never an omitted spend field"
    requirement: "MACH-11"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_mach11_event.py::test_the_out_of_deps_event_carries_a_present_zero_spend_with_a_non_empty_counted_by"
        status: pass
    human_judgment: false
  - id: D8
    description: "SeamEvent.outcome is a closed Literal; constructing one with an outcome outside
      the declared vocabulary raises pydantic.ValidationError; the event carries no node position,
      wiring id, or instance hash"
    requirement: "MACH-11"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_mach11_event.py::test_constructing_a_seam_event_with_an_outcome_outside_the_declared_set_raises_validation_error, ::test_the_event_carries_no_node_position_wiring_id_or_instance_hash"
        status: pass
    human_judgment: false
  - id: D9
    description: "A complete real envelope (non-empty evidence, a multi-counted_by token
      breakdown, a non-empty trace reference, and at least one seam event) contains no
      high-entropy internal identity anywhere in its serialized JSON text"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_leak.py::test_the_envelope_carries_every_field_this_phase_populates_before_the_leak_gate_runs, ::test_no_high_entropy_identity_appears_anywhere_in_the_serialized_envelope"
        status: pass
    human_judgment: false
  - id: D10
    description: "The same envelope contains no dict key at any nesting depth equal to a
      low-entropy identity (node id/wiring id/arm id); both tiers are proven to fail on a planted
      violation (a forbidden key at depth three; a string containing a real instance_hash)"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_leak.py::test_no_forbidden_key_appears_at_any_nesting_depth_in_the_parsed_envelope, ::test_the_structural_check_fails_on_a_hand_built_forbidden_key_at_nesting_depth_three, ::test_the_high_entropy_check_fails_on_a_string_containing_a_real_instance_hash"
        status: pass
    human_judgment: false

duration: 90min
completed: 2026-09-07
status: complete
---

# Phase 4 Plan 4: The Seam — Trace Token, MACH-11 Event, and the Leak Gate Summary

**A durable SQLite-backed trace store mints an opaque `secrets.token_urlsafe` reference that
resolves through the seam's new `resolve_trace` operation to a run's node-by-node trace only when
debug is requested; an out-of-`deps` `mutates_store` touch now surfaces as a `SeamEvent` with a
closed outcome vocabulary; and a two-tier leak gate (substring for 64-hex identities, structural
key-walk for human-readable ones) proves a complete real envelope leaks nothing, with both tiers
shown to fail on a planted violation.**

## Performance
- **Duration:** ~90 min
- **Started:** 2026-09-06 / **Completed:** 2026-09-07
- **Tasks:** 3 / **Files created:** 5 / **Files modified:** 2

## Accomplishments

- `databasise/seam/trace_store.py`: `TraceStore` persists a full `RunRecord.to_dict()` keyed by a
  `secrets.token_urlsafe(32)` token at its own `trace.db` beside `ledger.db`, mirroring
  `ledger.py`'s schema/WAL pattern. `UnknownTraceReferenceError` (subclassing `SeamRefusalError`)
  refuses an unknown token by exception type — never `None`, never a partial record.
- `Databasise.__init__` opens one `TraceStore` per engine instance; `query()` persists the
  `RunRecord` and mints the token into the envelope's `trace_token` field before the record goes
  out of scope. `Databasise.resolve_trace(trace_reference, *, debug=False)` is the third §18
  operation the seam exposes — the full record (including `nodes`) only when `debug` is set;
  otherwise the `nodes` key is stripped.
- `databasise/seam/envelope.py`'s `SeamEvent.outcome` is now `Literal["completed", "halted",
  "failed"]` instead of a bare `str` — an unknown outcome refuses at construction.
- `databasise/seam/engine.py`'s `query()` passes a `TouchRecorder` to `scheduler.run_wiring` and
  correlates the recorded touches after the run (`_mach11_events`/`_accounted_store_keys`, FA-08):
  for every node whose registered `Part` declares `mutates_store`, a touched store key its own
  declared `deps` do not account for (via a dependency's own `reads_*`/`writes_*` effect) produces
  one `SeamEvent` naming the part's verbatim `name@version`, its own token spend, and an outcome.
  No production LightRAG part declares `mutates_store`, so `seam_events` is always empty for the
  real arms this phase ships — proven only against fixture parts.
- `databasise/seam/redact.py`: `forbidden_identities()` builds the ground-truth
  high-/low-entropy forbidden sets from a run record dict; `assert_no_forbidden_keys()` walks a
  parsed structure and fails on a forbidden dict key at any nesting depth. Shipped as library code
  so 04-05's REST transport asserts against the identical gate.
- `databasise/tests/seam/test_trace_token.py` (7 tests), `test_mach11_event.py` (9 tests),
  `test_leak.py` (7 tests) — 23 new tests, all passing.

## Task Commits
1. **Task 1: Trace token + resolve_trace** - `3ef8fc2` (feat)
2. **Task 2: MACH-11 seam event** - `286a9b6` (feat)
3. **Task 3: Two-tier leak gate** - `a758504` (feat)

**Plan metadata:** committed after this SUMMARY (see completion report for hash).

## Files Created/Modified
- `databasise/seam/trace_store.py` - `TraceStore`, `UnknownTraceReferenceError`
- `databasise/seam/redact.py` - `forbidden_identities`, `assert_no_forbidden_keys`
- `databasise/seam/engine.py` - `TraceStore` wiring, `resolve_trace`, `_accounted_store_keys`,
  `_mach11_events`, the `TouchRecorder` passed to `scheduler.run_wiring`
- `databasise/seam/envelope.py` - `SeamEvent.outcome` retyped to a closed `Literal`
  (`SeamEventOutcome`)
- `databasise/tests/seam/test_trace_token.py` - 7 tests (Task 1)
- `databasise/tests/seam/test_mach11_event.py` - 9 tests (Task 2)
- `databasise/tests/seam/test_leak.py` - 7 tests (Task 3)

## Decisions Made
See `key-decisions` above for the token-randomness rationale, the non-debug field strip, the
outcome vocabulary, the correlation rule's exact statement, the D-08 hosting-gap workaround, and
why the leak test bypasses `Databasise.query()`.

## Deviations from Plan

**1. [Discovery, not a Rule 1-4 fix — a genuine, orthogonal architectural gap] No `Part` declaring
`mutates_store` can complete real dispatch under the current runner.**
- **Found during:** Task 2, while designing the MACH-11 fixture.
- **Issue:** `databasise.validator.execution_mode.derive_execution_mode` routes any `Part`
  declaring `mutates_store` to the `confined-unit` placement (§2's vocabulary keeps `mutates_store`
  deliberately opaque about which store it touches — that opacity is exactly why it is treated as
  a store-boundary effect the runner must not host in-process). Phase 1's `host()` (D-08) hosts
  `in-process` only; every other placement raises `UnimplementedPlacementError`. This means a
  fixture part declaring `mutates_store` — the very effect MACH-11 exists to detect — is traced as
  `budget_state="halted"` (CONTRACT §9's "MUST NOT be discarded" rule; the run itself still
  completes and returns, `partial=True`) but its body never runs, so the scheduler's own recorder
  never observes a touch for it through ordinary dispatch.
- **Why this is not a Rule 1-4 fix:** Widening `host()` to also host `confined-unit` would be a
  real architectural change to D-08's own explicitly-scoped Phase-1 boundary ("Phase 1 hosts
  in-process only... real opaque-node admission in Phase 2/5 is what earns this placement's
  hosting") — out of this plan's lane and squarely Rule 4 territory (changing what a prior,
  explicitly-scoped phase decision covers). This is also not a task-blocking bug to auto-fix: the
  correlation logic under test is correct and does not require the touching node to have been
  dispatched through the full scheduler to be exercised meaningfully.
- **Resolution:** Both `test_mach11_event.py` and `test_leak.py` call the scheduler's own
  production `_ScopedStoresView` class directly for the un-hostable fixture node — the identical
  code path a hosted node's body would exercise via `ctx.stores["kv"]` — producing a real touch in
  the exact tuple shape the scheduler emits, rather than fabricating one by hand or changing the
  hosting gate. Documented in both test modules' own docstrings, with an explicit note that a
  later phase introducing real `confined-unit` hosting (Phase 5+) should re-verify this path
  against an actually-dispatched `mutates_store` node.
- **Files affected:** `databasise/tests/seam/test_mach11_event.py`, `databasise/tests/seam/test_leak.py`.
- **Verification:** All 9 + 7 tests in the two files pass; the correlation functions
  (`_accounted_store_keys`/`_mach11_events`) are exercised against real `ParsedWiring`/`NodeTrace`
  objects and a real, recorder-driven touches list.
- **Commit:** `286a9b6` (mach11), `a758504` (leak).

**Total deviations:** 1 (a discovered architectural gap, worked around rather than papered over or
silently widened).
**Impact on plan:** None on the plan's own stated goals — every task's acceptance criteria and the
plan-level `<verification>` block all pass. The workaround is orthogonal to the correlation logic
itself, which is exercised with real production code and real data throughout.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

`databasise/seam/envelope.py`'s complete §18.2 field set (declared upfront in 04-01) is now fully
populated by real values for every field this phase owns — `.planning/WINDOWS.md` entries 1 and 2
are both `fixed`. 04-05 (REST transport) inherits: `Databasise.resolve_trace` as the seam's third
operation to expose over HTTP, and `databasise.seam.redact`'s two exported helpers to assert
against for its own dual-transport conformance test, rather than re-deriving the leak gate. No
blockers.

## Self-Check: PASSED

- `databasise/seam/trace_store.py`, `databasise/seam/redact.py` — present (`[ -f ]` verified).
- `databasise/tests/seam/test_trace_token.py`, `test_mach11_event.py`, `test_leak.py` — present.
- `git log --oneline --all --grep="04-04"` returns 3 commits (`3ef8fc2`, `286a9b6`, `a758504`).
- `cd databasise && uv run pytest -q tests/seam/ -x` — 86 passed.
- `cd databasise && uv run pytest -q` — 552 passed (baseline 529 + 23 new; above the plan's own
  466-test floor and above the session's 529-test baseline).
- `cd databasise && uv run python -m databasise.tools.check_import_boundary` — exit 0, no
  violations.

---
*Phase: 04-the-seam*
*Completed: 2026-09-07*

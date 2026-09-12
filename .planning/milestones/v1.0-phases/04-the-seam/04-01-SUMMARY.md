---
phase: 04-the-seam
plan: 01
subsystem: api
tags: [seam, pydantic, envelope, query-object, refusals, lightrag]

requires:
  - phase: 03-lightrag-query-side
    provides: the seven-node "naive" arm, the registered LightRAG parts, run_arm.py's proven
      resolve->inject->parse->run_wiring->RunRecord call shape, and the synthetic-store/stub-client
      test pattern this plan's tracer reuses
provides:
  - "databasise.seam.Databasise — the async consumer-facing seam object (D-01), the phase's primary noun"
  - "databasise.seam.QueryObject — §18.1's five-member query object, frozen, extra-forbidding, with D-14's per-member consumption check"
  - "databasise.seam.ResponseEnvelope — §18.2's closed response envelope with the complete field set declared up front"
  - "databasise.seam.Selector — §18.4's selector input model, default branch resolved (alias/capability/harness are 04-03's deliverable)"
  - "databasise.seam.refusals — the typed refusal hierarchy 04-03's selector refusals will extend"
  - "run_wiring demoted to machine-internal in its own docstring (D-02), no behaviour change"
affects: [04-02-token-and-evidence, 04-03-selectors-and-alias, 04-04-trace-and-mach11, 04-05-rest-transport]

actuals:
  tokens: 9200
  tasks: 3
  commits: 3
  plan_head_before: 3e59f4efece27b4b5f7f0b0beae2bbf5825d9ade

tech-stack:
  added: []
  patterns:
    - "Shared strict Pydantic v2 base (_StrictModel: frozen=True, extra=forbid) inherited by every envelope model, top-level and nested, since Pydantic v2 does not cascade per-model config through nested fields"
    - "Refusal-by-absence: a query-object member is refused because no registered part/store declares the matching capability yet, checked dynamically against the registry rather than hardcoded as a permanent exclusion"
    - "Selector branches that are not yet implemented raise NotImplementedError naming their future owner, rather than silently falling through to the default"

key-files:
  created:
    - databasise/seam/__init__.py
    - databasise/seam/query.py
    - databasise/seam/envelope.py
    - databasise/seam/selectors.py
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/tests/seam/__init__.py
    - databasise/tests/seam/conftest.py
    - databasise/tests/seam/test_seam_tracer.py
    - databasise/tests/seam/test_query_object.py
    - databasise/tests/seam/test_envelope_schema.py
  modified:
    - databasise/pyproject.toml
    - databasise/__init__.py

key-decisions:
  - "Checkpoint answer applied verbatim: declare-upfront — the complete §18.2 field set is declared in this plan; resolved_model_identity excluded from the envelope (FA-02 resolved)."
  - "Databasise.query() calls check_consumable() before resolving any selector, even though Task 2's <files> list did not name engine.py — required to satisfy Task 2's own acceptance criterion that resolve_arm is never reached for an empty query object; documented as a deviation below."
  - "The default selector resolves to the naive arm unconditionally; alias/capability/harness raise NotImplementedError naming 04-03 as owner, never falling through to the default silently."

requirements-completed: [API-03]

coverage:
  - id: D1
    description: "A caller constructs Databasise(store_root=..., workspace=...) and awaits .query(QueryObject(text=...)), receiving a ResponseEnvelope with no wiring/arm/node/instance identity crossing the boundary"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_seam_tracer.py#test_a_caller_queries_the_engine_and_receives_a_closed_envelope"
        status: pass
    human_judgment: false
  - id: D2
    description: "An empty query object and each of the four currently-unconsumable members (embedding, predicates, profile_ref, formal_query) are refused by name before any wiring resolves"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_query_object.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Non-ASCII query text round-trips unchanged through the seam into the envelope's answer field"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_query_object.py#test_non_ascii_text_round_trips_unchanged_through_the_seam"
        status: pass
    human_judgment: false
  - id: D4
    description: "The envelope rejects an unknown key at every nesting depth, not only the top level; no declared field name matches RunRecord/NodeTrace's own internal-identity vocabulary"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_envelope_schema.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "run_wiring's module and function docstrings are demoted to machine-internal (D-02), with no behaviour, signature, or return-shape change; the parity harness keeps passing untouched"
    verification:
      - kind: unit
        ref: "cd databasise && uv run pytest -q tests/parity/ -x"
        status: pass
    human_judgment: false
  - id: D6
    description: "The new databasise.seam subpackage imports nothing from v1, and ships in the built wheel via pyproject.toml's packages list"
    verification:
      - kind: unit
        ref: "cd databasise && uv run python -m databasise.tools.check_import_boundary"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-09-06
status: complete
---

# Phase 4 Plan 1: The Seam — Query Object, Closed Envelope, and the Databasise Engine Summary

**The async `Databasise` seam object, a §18.1 `QueryObject`, and a fully-declared §18.2
`ResponseEnvelope` — a real seven-node "naive" run against a synthetic store now goes in as a
query object and comes out as a closed, identity-free envelope, with the empty-query and
unconsumable-member refusals wired in before any wiring resolves.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-09-06 / **Completed:** 2026-09-06
- **Tasks:** 3 (plus one pre-answered checkpoint) / **Files created:** 11 / **Files modified:** 2

## decisions_recorded_here

**Checkpoint: confirm the concrete §18.2 envelope field list before four plans build on it.**

**Answer applied (from `.planning/phases/04-the-seam/04-CHECKPOINT-ANSWERS.md`, recorded by the
owner before execution began): `declare-upfront`.** The complete field set is declared in this
wave; later plans (04-02, 04-04) bind element types into fields that already exist here and MUST
NOT widen the envelope.

**`resolved_model_identity`: EXCLUDED from the envelope (FA-02 resolved).** No requirement in this
phase asks for it, and including it would make which model answered visible to consumers without
that having been decided under §18.3's invariance rule.

**Derived field list** (`databasise/seam/envelope.py`), each line's source noted:

| Field | Type | Source |
|---|---|---|
| `answer` | `str` | Checkpoint context: "the answer text field" — the query response payload itself, implicit in any query seam though not one of §18.2's five named bullets |
| `evidence` | `list[EvidenceRef]` (empty in this plan) | §18.2 bullet 1, "Evidence references" — element type (`ref`, `kind`, `tier`, `score`) filled by 04-02 |
| `trace_token` | `str \| None` | §18.2 bullet 2, "A trace reference" — D-06's opaque token; populated by 04-04 |
| `depth_label` | `str` | §18.2 bullet 3, "The depth label ... per Ruling R-1's three-value vocabulary" |
| `partial` | `bool` | §18.2 bullet 4, "Partial and degraded flags" |
| `degraded` | `bool` | §18.2 bullet 4, "Partial and degraded flags" |
| `stop_reason` | `str \| None` | §18.2 bullet 4, paired with `partial` per RIG §TR.3's required-together shape, mirrored at the seam |
| `degradation_reason` | `str \| None` | §18.2 bullet 4, paired with `degraded` |
| `token_accounting` | `list[TokenAccountingEntry]` (empty in this plan) | §18.2 bullet 5, "`counted_by` on any token number" — Pitfall 5's breakdown shape (never a single summed scalar); populated by 04-02 |
| `seam_events` | `list[SeamEvent]` (empty in this plan) | D-09/MACH-11, "a seam-level event ... per §18.2's envelope shape"; populated by 04-04 |

`EvidenceRef` (nested, per-item): `ref: str`, `kind: str`, `tier: str | None` (§18.2 bullet 3's "the
evidence tier labels", §4's T0–T3 ladder), `score: float | None`.

`TokenAccountingEntry` (nested): `counted_by: str`, `prompt_tokens: int`, `completion_tokens: int`,
`cached_read_tokens: int`, `call_count: int` — Pitfall 5's per-`counted_by` breakdown, never one
summed scalar.

`SeamEvent` (nested): `component: str` (`name@version`), `spend: TokenAccountingEntry | None`,
`outcome: str` — D-09's literal shape.

Every model in `databasise/seam/envelope.py` inherits a shared `_StrictModel`
(`frozen=True, extra="forbid"`), proven at every nesting depth by
`databasise/tests/seam/test_envelope_schema.py`.

## Accomplishments

- `databasise/seam/engine.py`'s `Databasise.query()` generalizes `run_arm.py`'s proven
  resolve→inject→parse→run_wiring→RunRecord sequence, reading `provides` off the raw resolved
  dict (never `ParsedWiring`, which drops it — Pitfall 1), and returns a closed envelope instead of
  the raw run record.
- `databasise/seam/query.py`'s `QueryObject` + `check_consumable()` refuse an empty query object
  and each of the four currently-unconsumable members (`embedding`, `predicates`, `profile_ref`,
  `formal_query`) by name, before any selector or wiring resolves — refusal-by-absence, not a
  permanent exclusion, since the check reads the registry's own declared capabilities each call.
- `databasise/seam/envelope.py`'s `ResponseEnvelope` declares the complete §18.2 field set now
  (per the checkpoint's `declare-upfront` answer), strict and extra-forbidding at every nesting
  depth.
- `databasise/seam/selectors.py` implements the default selector (resolves the `naive` arm); the
  other three raise `NotImplementedError` naming 04-03, never falling through silently.
- `databasise/__init__.py`'s docstrings demote `run_wiring` to machine-internal (D-02) with zero
  behaviour change — `tests/parity/` passes unchanged.
- `databasise/tests/seam/` (20 new tests): the end-to-end tracer against a synthetic store with
  stub clients, the empty-query/unconsumable-member refusal suite (including a non-ASCII
  round-trip and a `resolve_arm`-never-called assertion), and the envelope's structural closed-set
  proof.

## Task Commits

1. **Task 1: End-to-end tracer** — `5fe234b` (feat)
2. **Task 2: Refusal hierarchy and consumption rules** — `5a2392c` (feat)
3. **Task 3: Envelope structural closure + run_wiring demotion** — `324eb86` (docs)

**Plan metadata:** committed after this SUMMARY (see completion report for hash).

## Files Created/Modified

- `databasise/seam/engine.py` — the `Databasise` seam object; `query()` follows `run_arm.py`'s
  exact call shape, redacting into a `ResponseEnvelope` instead of returning the raw run record
- `databasise/seam/query.py` — `QueryObject` + `check_consumable()` (D-14)
- `databasise/seam/envelope.py` — `ResponseEnvelope` + nested `EvidenceRef`/`TokenAccountingEntry`/`SeamEvent`, all inheriting the shared `_StrictModel`
- `databasise/seam/selectors.py` — `Selector` + `resolve_selector()`, default branch only
- `databasise/seam/refusals.py` — `SeamRefusalError`, `EmptyQueryObjectError`, `UnconsumableQueryMemberError`
- `databasise/seam/__init__.py` — public exports: `Databasise`, `QueryObject`, `ResponseEnvelope`, `Selector`
- `databasise/pyproject.toml` — `databasise.seam` added to `[tool.setuptools] packages`
- `databasise/__init__.py` — module and `run_wiring` docstrings demoted to machine-internal
- `databasise/tests/seam/*` — tracer, query-object refusal, and envelope-schema tests plus a shared `synthetic_naive_store` fixture

## Decisions Made

See `decisions_recorded_here` above for the checkpoint answer and the derived field list. Also:

- The four non-`text` query-object members are refused via a capability lookup against the
  registry (`_registered_capabilities`), not a hardcoded `if member in {...}: raise` list — a
  later phase registering a part/store declaring `reads_space`, `formal-query-language`, etc.
  flips one of these to consumable without changing `check_consumable`'s shape, matching the
  plan's own "refusal by absence, not permanent exclusion" instruction.
- `RunRecord.arm_id` is stamped `"seam"` for every seam-driven run (there is no arm name to carry
  once selector resolution replaces arm naming) — internal only, never returned to a consumer.

## Deviations from Plan

**1. [Rule 3 — blocking issue] `Databasise.query()` calls `check_consumable()` even though
Task 2's `<files>` list did not name `databasise/seam/engine.py`.**
- **Found during:** Task 2.
- **Issue:** Task 2's acceptance criteria require a test asserting `resolve_arm` is never called
  when the query object is empty. That assertion is only meaningful if `check_consumable()` runs
  inside the actual query path before selector resolution — which means `engine.py`'s `query()`
  method must call it. Task 2's own `<files>` list omitted `engine.py`, but the call site was
  necessary to satisfy Task 2's own acceptance criteria.
- **Fix:** The call to `check_consumable(query_object, self.registry)` was written into
  `engine.query()` as part of Task 1's implementation (engine.py), so Task 2 only needed to extend
  `query.py`/add `refusals.py`, with no further change to `engine.py` required.
- **Files affected:** `databasise/seam/engine.py` (written in Task 1, not modified again in Task 2).
- **Verification:** `databasise/tests/seam/test_query_object.py::test_resolve_arm_is_never_called_when_the_query_object_is_empty` passes.
- **Commit:** `5fe234b` (the call site), `5a2392c` (the refusal types it raises).

**2. [Sequencing note, not a Rule 1-4 deviation] Task 1's own commit (`5fe234b`) references
`databasise.seam.refusals`, a module not created until Task 2's commit (`5a2392c`).**
- **Why:** `check_consumable()` was designed alongside `QueryObject` in Task 1 for architectural
  coherence (the consumption check is intrinsic to the query object's own contract), rather than
  bolted on afterward. Both commits' working-tree state passed the full test suite at the time
  each was made (the untracked `refusals.py` file was present on disk), and `HEAD` after every
  commit in this plan is fully working — but `5fe234b` checked out in isolation would not import
  cleanly, since its snapshot alone lacks `refusals.py`. This is a minor commit-granularity
  imperfection, not a functional defect: the very next commit in this same plan (`5a2392c`)
  supplies the missing file, and no commit after that point is affected.
- **Impact:** None on the shipped behaviour or the phase's forward plans. Flagged here for
  transparency since strict single-commit-checkout atomicity was not preserved for this one
  boundary.

**Total deviations:** 1 auto-fixed (Rule 3, blocking-issue), 1 sequencing note (no rule applies,
documented for transparency).
**Impact on plan:** None — every task's acceptance criteria and the plan-level `<verification>`
block all pass; `databasise/seam/engine.py`'s final shape matches the plan's own action text
exactly.

## Known Stubs

Both intentional per the checkpoint's `declare-upfront` decision, and already recorded in
`.planning/WINDOWS.md` (entries 1–2, kind `stub`, phase `04`) so they stay visible at ship time:

- `databasise/seam/envelope.py`: `ResponseEnvelope.evidence` and `.token_accounting` are declared
  with their final element types but land as empty lists in this plan — 04-02 populates them from
  a real evidence/token-accounting pass.
- `databasise/seam/envelope.py`: `ResponseEnvelope.trace_token` and `.seam_events` are declared
  but land `None`/empty in this plan — 04-04 mints the opaque trace token and wires the MACH-11
  detection that populates `seam_events`.

Neither stub blocks this plan's own goal (a query object in, a closed envelope out) — the
tracer test asserts against the fields this plan is actually responsible for (`answer`,
`depth_label`, `partial`, `degraded`) and does not assert anything about the still-empty fields.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

04-02 (token accounting + evidence references), 04-03 (alias/capability/harness selectors), 04-04
(trace token + MACH-11 events) and 04-05 (REST transport) can all bind into the envelope, selector,
and refusal shapes this plan declared, without widening them. No blockers.

## Self-Check: PASSED

- `databasise/seam/engine.py`, `databasise/seam/query.py`, `databasise/seam/envelope.py`,
  `databasise/seam/selectors.py`, `databasise/seam/refusals.py`, `databasise/seam/__init__.py` —
  all present (`[ -f ]` verified).
- `databasise/tests/seam/test_seam_tracer.py`, `test_query_object.py`, `test_envelope_schema.py`,
  `conftest.py`, `__init__.py` — all present.
- `git log --oneline --all --grep="04-01"` returns 3 commits (`5fe234b`, `5a2392c`, `324eb86`).
- `cd databasise && uv run pytest -q tests/seam/` — 20 passed.
- `cd databasise && uv run pytest -q tests/parity/ -x` — 126 passed.
- `cd databasise && uv run pytest -q` — 486 passed (baseline 466 + 20 new; above baseline).
- `cd databasise && uv run python -m databasise.tools.check_import_boundary` — exit 0, no violations.
- `cd databasise && uv run python -c "from databasise.seam import Databasise, QueryObject, ResponseEnvelope, Selector; print('ok')"` — prints `ok`.

---
*Phase: 04-the-seam*
*Completed: 2026-09-06*

---
phase: 04-the-seam
plan: 03
subsystem: api
tags: [seam, selectors, ledger, pydantic, refusals, lightrag]

requires:
  - phase: 04-the-seam (plan 01)
    provides: "databasise.seam.Selector's default branch, resolve_selector's shape, the
      SeamRefusalError base class, and the NotImplementedError placeholders this plan replaces"
provides:
  - "databasise.seam.selectors — all four §18.4 selectors: capability, alias, harness, and the
    default with its §8 condition 7 opaque exclusion"
  - "databasise.seam.refusals.UnsatisfiableSelectorError / ForbiddenSelectorInputError"
  - "databasise.ledger.ledger.Ledger.by_alias — the additive-column alias read projection"
  - "databasise/tests/fixtures/wiring-harness.json — the harness selector's only real subject"
affects: [04-04-trace-and-mach11, 04-05-rest-transport, 07-promote-rollback]

actuals:
  tokens: 13278
  tasks: 3
  commits: 3
  plan_head_before: 39833268694ee65193d9c4061f52b5f7c41b0c2b

tech-stack:
  added: []
  patterns:
    - "Smallest-resolved-wiring tie-break for capability matching, documented as deliberate: a
      declared-order tie-break alone would make every arm but naive unreachable, since every
      arm's effect set is not disjoint from its neighbours'"
    - "Optional `candidates` override on `_resolve_default`/`_resolve_capability`/
      `_resolve_harness` so a unit test can prove the opaque-exclusion and harness-matching logic
      directly against a hand-built or fixture wiring, through the exact same functions
      production dispatch calls — never a parallel reimplementation for tests"
    - "Provides-node-only opaque exclusion (not whole-wiring): a wiring is excluded from the
      default candidate set only when its own `provides` position resolves to opaque effective
      depth, distinguishing an answer that comes from an opaque node from a wiring that merely
      contains one elsewhere (naive's own dep-free `embedder-index`)"
    - "Narrow, named per-file exemption on a structural posture guard, updated in the same change
      as the new caller it whitelists (databasise/tests/runner/test_measurement_posture.py + the
      02-MACH-09-POSTURE.md record it pins) — never a directory-wide carve-out or a silently
      relaxed assertion"

key-files:
  created:
    - databasise/tests/seam/test_selectors.py
    - databasise/tests/seam/test_alias_registry.py
    - databasise/tests/fixtures/wiring-harness.json
  modified:
    - databasise/seam/selectors.py
    - databasise/seam/refusals.py
    - databasise/seam/engine.py
    - databasise/ledger/ledger.py
    - databasise/tests/runner/test_measurement_posture.py
    - .planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md

key-decisions:
  - "Checkpoint answer applied verbatim: dedicated-alias-column. See decisions_recorded_here below."
  - "Capability matching is defined over the frozen 17-member Effect vocabulary (FA-04, carried
    forward as an open question — thin, but sufficient to distinguish the five Phase 3 arms and
    therefore the §18.5 falsifier)."
  - "Capability tie-break is smallest-resolved-wiring-wins, not _ARM_NAMES declared order: every
    arm's effect set is a superset of some other arm's (bypass's calls_llm ⊆ every other arm's
    own effects), so a declared-order tie-break would make every arm but naive permanently
    unreachable by capability alone."
  - "The default selector's opaque exclusion (§8 condition 7) is scoped to the wiring's own
    `provides` position, not to 'contains an opaque node anywhere' — naive itself contains the
    dep-free, unrelated embedder-index node at opaque structural depth, and a whole-wiring
    exclusion would have made the default unable to resolve naive at all, breaking 04-01/04-02's
    already-established behaviour. Proven directly by a regression-guard test."
  - "The harness selector is proven only against a new fixture (wiring-harness.json), not any
    production arm (FA-05): every one of the five lightrag arms' own `harnesses` array is empty,
    so the production harness branch always refuses today. The §18.5 falsifier's harness case
    documents this as its own exception rather than silently asserting a claim the codebase
    cannot back."
  - "02-MACH-09-POSTURE.md's ledger-import guard gained one narrow, named, read-only exemption
    for databasise/seam/selectors.py rather than a directory-wide carve-out — the alias branch
    reads Ledger.by_alias but never appends and defines no promotion verb, so the measurement-
    gated promotion path MACH-09 gates has not started to exist."

patterns-established:
  - "A selector-resolution helper accepts an optional explicit candidate pool, defaulting to the
    production pool, so opaque-exclusion and harness-matching logic is testable against the exact
    dispatch function a caller uses, without a parallel test-only reimplementation."

requirements-completed: [API-03]

coverage:
  - id: D1
    description: "A capability selector resolves to a wiring (the smallest arm whose registered
      parts jointly declare the requested effect set) and returns a real, non-empty answer"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_selectors.py::test_a_capability_selector_resolves_to_a_wiring_and_returns_a_real_envelope"
        status: pass
    human_judgment: false
  - id: D2
    description: "An unsatisfiable capability selector raises UnsatisfiableSelectorError and never
      falls through to the default branch, and its message discloses no candidate wiring id or
      node id"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_selectors.py::test_an_unsatisfiable_capability_selector_raises_and_never_falls_through_to_the_default, ::test_the_unsatisfiable_capability_refusal_discloses_no_candidate_wiring_or_node_id"
        status: pass
    human_judgment: false
  - id: D3
    description: "A Selector constructed with an instance-hash-shaped value in alias/harness/
      capability raises pydantic.ValidationError before any resolution runs"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_selectors.py::test_an_instance_hash_shaped_selector_value_raises_validation_error"
        status: pass
    human_judgment: false
  - id: D4
    description: "selectors.py reads provides/harnesses off the raw resolved dict; ParsedWiring
      is proven to carry neither field, so a future refactor toward the validator's snapshot
      fails loudly"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_selectors.py::test_selectors_reads_provides_and_harnesses_off_the_raw_resolved_dict_never_parsed_wiring"
        status: pass
    human_judgment: false
  - id: D5
    description: "The alias selector reads the ledger's additive alias column via Ledger.by_alias
      and resolves the returned record's mutation_id as an arm name; an empty registry and a
      non-matching alias raise the identical refusal, naming only the consumer's own alias"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_alias_registry.py::test_an_empty_registry_refuses_the_alias_by_exception_type, ::test_the_refusal_message_names_the_consumers_alias_and_no_other_mutation_id, ::test_an_alias_absent_from_a_non_empty_registry_raises_the_identical_refusal_type, ::test_a_promoted_alias_resolves_via_the_mutation_id_field_named_at_the_checkpoint"
        status: pass
    human_judgment: false
  - id: D6
    description: "The alias path performs no ledger append, across a direct resolution and a full
      Databasise.query() call"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_alias_registry.py::test_alias_resolution_performs_no_ledger_append, ::test_a_full_query_through_the_alias_selector_performs_no_ledger_append"
        status: pass
    human_judgment: false
  - id: D7
    description: "The harness selector resolves the wiring-harness.json fixture, preserves its
      declared harness order verbatim, refuses an unknown harness name by exception type, and
      dispatches a real run to completion; no production arm satisfies any harness name"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_selectors.py::test_the_harness_selector_resolves_the_fixture_and_preserves_declared_order, ::test_an_unknown_harness_name_raises_the_named_refusal_by_exception_type, ::test_the_harness_fixture_dispatches_a_real_run_end_to_end, ::test_no_production_arm_declares_a_harness_so_the_production_branch_always_refuses"
        status: pass
    human_judgment: false
  - id: D8
    description: "A wiring whose own provides node is opaque-depth is excluded from the default
      candidate set, while the same wiring remains reachable by capability and by harness; naive
      (which contains an unrelated opaque node, embedder-index) remains the resolved default"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_selectors.py::test_a_wiring_whose_provides_node_is_opaque_is_excluded_from_the_default_candidate_set, ::test_the_same_opaque_wiring_remains_reachable_by_capability, ::test_the_same_opaque_wiring_remains_reachable_by_harness, ::test_naive_remains_the_default_because_its_own_provides_node_is_never_opaque"
        status: pass
    human_judgment: false
  - id: D9
    description: "The §18.5 falsifier: each of the four selector forms (default, alias,
      capability, harness) reaches a real run, with the selector value(s) passed proven to
      contain no arm name and no node id from any resolved arm"
    requirement: "API-03"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_selectors.py::test_falsifier_default_selector_reaches_naive_with_no_wiring_named, ::test_falsifier_alias_selector_reaches_bypass_with_no_wiring_named, ::test_falsifier_capability_selector_reaches_bypass_with_no_wiring_named, ::test_falsifier_harness_selector_reaches_the_fixture_with_no_wiring_named"
        status: pass
    human_judgment: false
  - id: D10
    description: "The ledger's append-only triggers and its existing test suite still pass after
      the additive alias column lands; the measurement posture guard's exemption is narrow and
      named, not a relaxation of the promotion-verb or provenance-default checks"
    verification:
      - kind: unit
        ref: "cd databasise && uv run pytest -q tests/ledger/ tests/runner/test_measurement_posture.py -x"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-09-06
status: complete
---

# Phase 4 Plan 3: The Seam — Selectors, Alias Registry, and the §18.5 Falsifier Summary

**All four §18.4 selectors now resolve for real — capability by smallest-satisfying-arm,
alias by a new dedicated ledger column, harness by a documented fixture since no production arm
declares one — and the §18.5 falsifier proves each reaches a real run without any caller naming a
wiring, arm, node, or instance hash.**

## Performance
- **Duration:** ~70 min
- **Started:** 2026-09-06 / **Completed:** 2026-09-06
- **Tasks:** 3 (plus one pre-answered checkpoint) / **Files created:** 3 / **Files modified:** 6

## decisions_recorded_here

**Checkpoint: confirm the alias registry read shape Phase 7 will write to.**

**Answer applied (from `.planning/phases/04-the-seam/04-CHECKPOINT-ANSWERS.md`, recorded by the
owner before execution began): `dedicated-alias-column`.** A small, additive `alias TEXT` column
was added to the ledger schema now, rather than overloading `mutation_id`. Owner's rationale,
recorded verbatim: the ledger is append-only and enforced by `BEFORE UPDATE`/`BEFORE DELETE`
triggers, so a field carrying two meanings can never be disentangled once Phase 7 writes the first
real row; and Phase 7 is a committed roadmap phase, not a speculative caller, so the column is not
speculative surface.

The three concrete items the checkpoint's acceptance criteria require, named exactly:

1. **The exact lookup call the seam makes:** `Ledger(store_root).by_alias(alias)` —
   `databasise/seam/selectors.py:_resolve_alias`. This is a derived active-pointer projection
   (`SELECT * FROM ledger WHERE alias = ? ORDER BY id DESC LIMIT 1`), exactly like
   `Ledger.active_pointer` is keyed on `mutation_id` — never an independently-writable "current
   alias" column.
2. **The exact record field it reads to identify the active wiring:** `LedgerRecord.mutation_id`
   on the record `by_alias` returns — resolved as an arm name via
   `databasise.wirings.resolve.resolve_arm(record.mutation_id)`, the same resolution every other
   selector branch ends at.
3. **What Phase 7 must append for the read to succeed:** a `LedgerRecord` whose `alias` column
   holds the promoted alias string and whose `mutation_id` holds the arm name identifying the
   promoted wiring, on the same row.

The registry stays empty in this phase and every alias lookup refuses — the correct end state per
the checkpoint's own framing, not a defect. This is recorded identically in
`databasise/ledger/ledger.py`'s module docstring and `databasise/seam/selectors.py`'s module
docstring (`_resolve_alias`'s own docstring), per the checkpoint's requirement that both the plan
SUMMARY and `selectors.py` name it.

## Accomplishments

- **The capability selector** (`databasise/seam/selectors.py`): matches a requested effect set
  against the union of each candidate arm's registered parts' own declared effects (never the
  wiring node's own possibly-narrower declaration, CR-01). Ties are broken by smallest resolved
  wiring — documented as deliberate, since every arm's effect set is not disjoint from its
  neighbours' and a declared-order tie-break alone would make every arm but `naive` permanently
  unreachable by capability alone. FA-04's own thinness limitation (the vocabulary is
  machine-facing, not consumer-facing) is carried forward verbatim in the module docstring.
- **The alias selector**: reads the ledger's new additive `alias` column via `Ledger.by_alias`,
  read-only — never appends. Empty registry and non-matching alias raise the identical
  `UnsatisfiableSelectorError`, naming only the consumer's own alias value.
- **The harness selector**: reads the wiring's own ordered `harnesses` array off the raw resolved
  dict, preserving declared order. Proven against a new fixture,
  `databasise/tests/fixtures/wiring-harness.json`, since no production arm in this repository
  declares a harness (FA-05) — the production branch always refuses today, and the fixture's own
  `title` says so plainly.
- **The default selector's opaque exclusion** (§8 condition 7): a candidate is excluded from the
  default set only when its own `provides` position resolves to opaque effective depth — scoped
  to the answer-producing node, not "contains an opaque node anywhere". This matters concretely:
  every arm except `bypass` also contains the dep-free `embedder-index` node at opaque structural
  depth, and a whole-wiring exclusion would have made the default selector unable to resolve
  `naive` at all, breaking 04-01/04-02's already-established behaviour. A regression-guard test
  proves `naive` is still the resolved default.
- **The §18.5 falsifier**: all four selector forms (default, alias, capability, harness) reach a
  real run — `naive`, `bypass` (twice, via alias and via capability), and the harness fixture —
  each proven to have named no arm from `_ARM_NAMES` and no node id from any resolved arm.
- **The `Selector` model's forbidden-input validator** (T-04-12): a value shaped like an instance
  hash (`sha256:`-prefixed or bare 64-hex-char) in `alias`/`harness`/`capability` now raises
  `pydantic.ValidationError` at construction, before any resolution runs.
- **02-MACH-09-POSTURE.md updated**: `databasise/seam/selectors.py`'s alias branch is the first
  non-test module to import the ledger; the posture guard test gained one narrow, named,
  read-only exemption for exactly this file, recorded in both the test's own module docstring and
  the posture document — the promotion-verb and provenance-default guards are untouched.

## Task Commits
1. **Task 1: End-to-end "a consumer selects a capability and reaches an arm without naming a
   wiring"** — `541f5f6` (feat)
2. **Task 2: The alias selector's read path and its empty-registry refusal (D-12, FA-06)** —
   `ba13dae` (feat)
3. **Task 3: The harness selector, the default selector's opaque exclusion, and the §18.5
   falsifier check (D-13, FA-05)** — `fcc3a05` (feat)

**Plan metadata:** committed after this SUMMARY (see completion report for hash).

## Files Created/Modified
- `databasise/seam/selectors.py` — all four §18.4 selectors; `Selector`'s forbidden-input
  validator; `_capability_candidates`/`_wiring_effects`/`_match_capability`/`_resolve_capability`;
  `_is_default_eligible`/`_resolve_default`; `_resolve_alias`; `_wiring_declares_harness`/
  `_match_harness`/`_resolve_harness`
- `databasise/seam/refusals.py` — `UnsatisfiableSelectorError`, `ForbiddenSelectorInputError`
- `databasise/seam/engine.py` — `Databasise.query()` threads `store_root` into `resolve_selector`
- `databasise/ledger/ledger.py` — additive `alias TEXT` column, `ix_ledger_alias` index,
  `Ledger.by_alias`
- `databasise/tests/seam/test_selectors.py` — capability, harness, opaque-exclusion, and §18.5
  falsifier coverage (21 tests)
- `databasise/tests/seam/test_alias_registry.py` — alias read-path and no-append coverage (8
  tests)
- `databasise/tests/fixtures/wiring-harness.json` — the harness selector's only real subject
- `databasise/tests/runner/test_measurement_posture.py` — one narrow, named exemption for the
  alias branch's read-only ledger import
- `.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md` — records the read-only exception

## Decisions Made
See `decisions_recorded_here` and `key-decisions` above.

## Deviations from Plan

**1. [Rule 3 — blocking issue] `Databasise.query()` threads `store_root` into `resolve_selector`,
though `databasise/seam/engine.py` was not in this task's declared `<files>` list.**
- **Found during:** Task 2.
- **Issue:** The alias branch's lookup call (`Ledger(store_root).by_alias(alias)`) needs the
  store's root path to open the ledger. `resolve_selector`'s signature already accepted an
  optional `store_root` (added in Task 1 in anticipation), but nothing threaded a real value
  through until the engine's own call site passed one.
- **Fix:** `engine.py`'s `query()` now calls
  `resolve_selector(selector, registry=self.registry, store_root=self.store_root)`.
- **Files affected:** `databasise/seam/engine.py` (one line).
- **Verification:** `databasise/tests/seam/test_alias_registry.py::test_a_full_query_through_the_alias_selector_performs_no_ledger_append` exercises this call site directly; full suite green.
- **Commit:** `ba13dae`. Precedent: 04-01-SUMMARY.md's own Deviation 1 for the same class of
  cross-cutting wiring need.

**2. [Rule 2 — missing critical functionality, scope-boundary guard] `02-MACH-09-POSTURE.md` and
its guard test required an update not listed in this plan's declared files.**
- **Found during:** Task 2, discovered by the full suite (not by either task's own narrower
  `<verify>` command, both of which only ran the seam-specific test files).
- **Issue:** `databasise/tests/runner/test_measurement_posture.py::test_no_non_test_module_imports_the_ledger`
  is a Phase 2 structural pin: no non-test, non-`ledger/` module may import
  `databasise.ledger.ledger`, because doing so is the guard test's own signal that "the
  measurement-gated promotion path has started to exist." The alias branch's `from
  databasise.ledger.ledger import Ledger` tripped this by design — the test's own docstring
  instructs updating `02-MACH-09-POSTURE.md` in the same change rather than relaxing the test
  without recording why.
- **Fix:** Added one narrow, named, per-file exemption (`_EXEMPT_FILES = ("seam/selectors.py",
  ...)`) scoped only to the ledger-import check — the promotion-verb and
  `promotion_provenance`-has-no-default checks still scan `selectors.py` unchanged — and recorded
  the exception's reasoning in a new "Read-only exception" section of `02-MACH-09-POSTURE.md`.
- **Files affected:** `databasise/tests/runner/test_measurement_posture.py`,
  `.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md`.
- **Verification:** `cd databasise && uv run pytest -q tests/runner/test_measurement_posture.py -x` — 3 passed. Full suite green.
- **Commit:** `ba13dae`.

**3. [Judgment call, not a Rule 1-4 fix] The capability selector's tie-break rule (smallest
resolved wiring wins) departs from the plan's own first-suggested "declared-order" tie-break.**
- **Why:** The plan's action text left the tie-break rule to the implementer ("resolve
  deterministically and state the rule in the module docstring"). A first-in-`_ARM_NAMES`-order
  tie-break would make every arm but `naive` permanently unreachable by capability alone, since
  every arm's effect set is a superset of some other arm's own (`bypass`'s single `calls_llm`
  effect is a subset of every other arm's effects) — meaning the capability branch could never be
  proven to reach anything but the same wiring the default already reaches, undermining Task 1's
  own "reaches an arm without naming a wiring" test. Smallest-wiring-wins resolves to the most
  specific match and lets Task 1's test exercise a genuinely different arm (`bypass`).
- **Files affected:** `databasise/seam/selectors.py` (`_match_capability`).
- **Verification:** `databasise/tests/seam/test_selectors.py::test_a_capability_selector_resolves_to_a_wiring_and_returns_a_real_envelope` asserts the actual reached arm's own stub completion text, not shape alone.
- **Commit:** `541f5f6`.

**4. [Judgment call, not a Rule 1-4 fix] The harness-branch and opaque-exclusion "reachable by
capability/harness" proofs (Task 3's acceptance criteria) call the production matching functions
directly with an injected `candidates` override, rather than through the full `Databasise.query()`
seam or by extending `_ARM_NAMES`.**
- **Why:** `_ARM_NAMES` is `databasise/wirings/resolve.py`'s own frozen tuple of the five
  committed lightrag arms — extending it to admit a test-only fixture is out of this plan's scope
  and would misrepresent the fixture as a sixth published arm. `_resolve_default`/
  `_resolve_capability`/`_resolve_harness` each accept an optional `candidates` parameter
  (defaulting to the real production pool) precisely so a test can drive the *exact* function
  production dispatch calls over a hand-built or fixture candidate list, rather than
  re-implementing the matching logic a second time for tests.
- **Files affected:** `databasise/seam/selectors.py` (the `candidates` parameter on three
  functions), `databasise/tests/seam/test_selectors.py`.
- **Verification:** the opaque-exclusion and harness-fixture tests listed under coverage D7/D8
  above all pass, asserting real values (the fixture's own harness order, the fixture dict
  identity) rather than shape alone.
- **Commit:** `fcc3a05`.

**Total deviations:** 2 auto-fixed (Rule 3 — blocking issue; Rule 2 — missing critical
functionality/scope-boundary guard), 2 documented judgment calls (tie-break rule; test-injection
pattern for the `candidates` override).
**Impact on plan:** None on the plan's own stated goals — every task's acceptance criteria and
the plan-level `<verification>` block all pass; the harness/opaque-exclusion functions are proven
against real fixtures through the same functions production code calls, not a parallel
reimplementation.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
All four §18.4 selectors resolve for real. 04-04 (trace token + MACH-11 events) and 04-05 (REST
transport) can bind into these selector shapes without widening them. Phase 7 (promote/rollback)
inherits a concretely-named alias read contract (`Ledger.by_alias`, `mutation_id` as the resolved
arm name) to write against — no further selector-side negotiation needed. No blockers.

## Self-Check: PASSED

- `databasise/seam/selectors.py`, `databasise/seam/refusals.py`, `databasise/seam/engine.py`,
  `databasise/ledger/ledger.py` — all present (`[ -f ]` verified).
- `databasise/tests/seam/test_selectors.py`, `test_alias_registry.py`,
  `databasise/tests/fixtures/wiring-harness.json` — all present.
- `git log --oneline --all --grep="04-03"` returns 3 commits (`541f5f6`, `ba13dae`, `fcc3a05`).
- `cd databasise && uv run pytest -q tests/seam/ -x` — 63 passed.
- `cd databasise && uv run pytest -q tests/ledger/ tests/runner/test_measurement_posture.py -x` — 45 passed.
- `cd databasise && uv run python -m databasise.tools.check_import_boundary` — exit 0, no
  violations.
- `cd databasise && uv run pytest -q` — 529 passed (baseline 500 + 29 new; at/above the 466-test
  plan-level floor and above the 500-test session baseline).

---
*Phase: 04-the-seam*
*Completed: 2026-09-06*

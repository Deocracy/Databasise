# MACH-09 — Default Measurement Posture

This document records, as a checkable artifact rather than as prose about a future state,
the default measurement posture MACH-09 requires and the structural reason it holds today.

## Posture

Measurement-gated promotion is **OFF by default**, with one exception: **retrieval-side
scoring stays ON by default** (RIG §F3.2). The default-off rule covers exactly two classes:
**answer-level** and **index-side**. Retrieval-side is the only class measurement-gated
promotion runs for out of the box.

## What this disables

Enumerated from RIG §F3.2 item 1, by name:

- The `promote-next` and `promote-now` verbs — the top two rungs of CONTRACT §5's five-verb
  ladder (`check`, `preview`, `run`, `promote-next`, `promote-now`).
- All eight of CONTRACT §5's gate verdicts, at the answer-level and index-side tiers:
  `promote`, `reject`, `inconclusive`, `insufficient-depth`, `below-floor`, `unconfirmed`,
  `regression-veto`, `straddle`.
- The A/A-null-derived promotion floor for those two classes.
- Automatic semver minting at promotion (CONTRACT §0/§6) — a semver is minted only at
  promotion, and a class whose promotion path is off by default never mints one. This
  disables the *automatic*, gate-adjudicated minting path specifically; the manual path
  survives (see below).
- The automated mutation proposer loop.
- Test dimension 11 (PROJECT.md's "self-improvement readiness — representation is mutable,
  budgeted, A/B-testable").
- Empirical dimensions 13-15 (token use, domain retrieval quality, cross-domain synthesis).

## What survives

Enumerated equally completely from RIG §F3.2 item 2:

- `check`, `preview` and `run` — the bottom three rungs of CONTRACT §5's own ladder.
- The entire parallel-run model of RIG §RUN, because comparison as *inspection* is free and
  only adjudication costs.
- The entire trace of RIG §TR, including token and latency attribution.
- Manual promotion via RIG §PR's provenance mechanism (the `operator-asserted` path).
- Rollback.
- Determinism verification — a cache-bypassed re-run costs a re-run and not a bundle, so `T3`
  stamps survive.
- Every structural capability of the machine.

RIG §F3.2's own one-line principle, unabridged: **running and reading are cheap; adjudicating
is what costs.**

## Why the posture holds today without a switch

No measurement-gated promotion path exists anywhere in `databasise/`. `databasise/ledger/ledger.py`
defines the append-only ledger and `LedgerRecord.promotion_provenance` with no default value
(a ledger append can never omit its provenance), but nothing in the package calls
`Ledger.append()` outside tests — the promote/rollback protocol is Phase 7's MACH-07, and
`ledger.py`'s own module docstring states the scope fence explicitly: "Phase 1 does not
exercise a real promotion."

Phase 2 therefore adds **no `measurement_posture` config flag, enum, or settings object**. A
switch with no consumer would record a posture the machine does not actually hold —
02-RESEARCH.md Pitfall 4 names exactly this as the failure mode to avoid. The guard test
`databasise/tests/runner/test_measurement_posture.py` is what keeps this paragraph true: it
pins, structurally, that no non-test module imports the ledger and that no module defines a
`promote`/`promote_next`/`promote_now`/`rollback` verb, so a later change that starts building
the promotion path fails this test rather than silently invalidating this record.

## 07-01-PLAN.md: the operator-asserted write exception (MACH-07)

`databasise/seam/engine.py`'s `Databasise.promote()` is the second non-test, non-`ledger/` module
to import `databasise.ledger.ledger`, and the first to call `Ledger.append()` outside the test
suite. This is MACH-07's own deliverable, landed exactly where 02-CONTEXT.md's D-04 and this
document's own "What survives" section already named it: "Manual promotion via RIG §PR's
provenance mechanism (the `operator-asserted` path)." The posture this document records does not
change — it is made real for the one path RIG §F3.2 already lists as surviving unconditionally.

**Why this does not mean the gate-adjudicated path has started to exist.** `promote()` takes a
`verb` parameter covering CONTRACT §5's five-verb ladder plus the operator-asserted path
(`databasise.seam.promotion.PromotionVerb`). Only `verb="operator-asserted"` (the default) ever
reaches `Ledger.append()`. Every other verb refuses before that line:

- `check`, `preview`, `run` raise `GateVerbNotBuiltError` immediately — no gate implementation
  exists in this milestone, and none is built here.
- `promote-next`, `promote-now` run the same trace-resolution and class-derivation steps the
  operator path does (so the refusal can name the class), then branch on the identical posture
  this document records — `databasise.seam.promotion._MEASUREMENT_POSTURE`, a module constant
  reading `{"retrieval-side": True, "answer-level": False, "index-side": False}`, exactly RIG
  §F3.2. `answer-level`/`index-side` (off by default) raise `MeasurementPostureRefusalError`,
  quoting RIG §F3.2 by name. `retrieval-side` (on by default) raises
  `UncalibratedFloorRefusalError`, since no calibrated A/A floor exists yet (MACH-03 Pending) —
  RIG §AA.2's own rule that a null with unknown bypass status is unusable as a floor.

No branch of `promote()` for any verb other than `operator-asserted` appends a row in this
milestone — proven at runtime, not merely by this document's prose, by
`databasise/tests/seam/test_promotion_posture.py::test_no_gate_verb_appends_a_row` and its sibling
tests for each refusal. The posture constant itself is read at exactly one call site inside
`databasise/seam/promotion.py` and is never reached through an environment variable, a config
file, or a `Databasise` constructor argument (D-11) —
`test_posture_is_not_flippable_at_runtime` pins this by setting a spread of plausible flag names
and asserting the refusal is unchanged.

The guard test's two exemption lists (`_EXEMPT_FILES` for the ledger-import check,
`_PROMOTION_VERB_EXEMPT_FILES` for the promotion-verb-definition check) both name exactly
`seam/engine.py`, with the reason recorded in the test's own module docstring. A third non-test
ledger caller, an `append()` call reachable from a gate-adjudicated verb, or a real
`promote_next`/`promote_now`/`rollback` *implementation* (not merely the string value of a `verb`
parameter) appearing anywhere outside the test suite still fails this test and still means this
document needs another update.

## 07-02-PLAN.md: rollback/retire — the same operator-asserted exception, extended (MACH-07)

`Databasise.rollback()` and `Databasise.retire()` are two more non-test callers of
`Ledger.append()` in `databasise/seam/engine.py` — the same file the 07-01 section above already
names, not a new caller site. Both are RIG §PR.2's own named operations, distinct from CONTRACT
§5's five-verb ladder (`check`/`preview`/`run`/`promote-next`/`promote-now`) that this document's
posture actually gates: `rollback()` repoints an alias to an explicitly named prior generation,
and `retire()` tombstones a generation. Neither carries a `verb` parameter, neither reaches any
gate-adjudicated branch, and neither is reachable from `promote-next`/`promote-now` — they are
their own §18 operations (Phase 4 D-03: one entry per operation), sharing `promote()`'s
operator-asserted precondition checks (`Databasise._resolve_operator_preconditions`) but never its
posture-refusal branch. This document's posture claim is unaffected: both new verbs are already
named in this document's own "What survives" section above (`Rollback`), and `retire()` is the
same class of manual, unmeasured, `promotion_provenance = "operator_asserted"` act rollback and
promote already are.

The guard test's own vocabulary needed one addition, not a relaxation: `_PROMOTION_VERB_NAMES`
(`databasise/tests/runner/test_measurement_posture.py`) already listed `"rollback"` as a name to
scan for — inherited from Phase 2, when it was written as a guess at what the CONTRACT §5
gate-adjudicated ladder's own rollback mechanism might be named, before Phase 7 settled that this
codebase's real `rollback()` is instead RIG §PR.2's operator-asserted path, never a member of that
ladder. `_PROMOTION_VERB_EXEMPT_FILES`'s matching detail set was widened from `{"def
promote(...)"}` to `{"def promote(...)", "def rollback(...)"}` for the one already-named exempt
file, `seam/engine.py` — the same file, the same reasoning, extended to name the second real
operator-asserted verb this phase landed. `retire` needed no exemption at all: it was never in
`_PROMOTION_VERB_NAMES`'s vocabulary, since nothing in Phase 2's own drafting mistook it for a
member of the gate-adjudicated ladder in the first place.

No branch of `rollback()`/`retire()` accepts a `verb` argument or reads
`databasise.seam.promotion._MEASUREMENT_POSTURE` at all — proven at runtime by
`databasise/tests/seam/test_rollback.py` and `databasise/tests/seam/test_retire.py`, which drive
real promote/rollback/retire sequences against the real ledger, not a hand-seeded row. A third verb
appearing under `seam/engine.py` with a `record_kind` outside the three declared constants
(`promotion`/`rollback`/`tombstone`), or a real `promote_next`/`promote_now` implementation
anywhere, still fails the guard test and still means this document needs another update.

## Read-only exception (04-03-PLAN.md, D-12/FA-06)

`databasise/seam/selectors.py`'s alias branch is the first non-test, non-`ledger/` module to
import `databasise.ledger.ledger`. It calls `Ledger.by_alias(alias)` — a derived projection over
the ledger's additive `alias` column, computed the same `ORDER BY id DESC LIMIT 1` way
`active_pointer` already is — and never calls `Ledger.append()`. This is a **read** of the ledger's
existing content to answer "which wiring does this alias name", not a measurement-gated promotion
decision: no `promote`/`promote_next`/`promote_now`/`rollback` verb is defined anywhere in
`databasise/seam/`, and the registry this branch reads is empty until Phase 7's MACH-07 promote
path appends the first real row.

The guard test (`databasise/tests/runner/test_measurement_posture.py::
test_no_non_test_module_imports_the_ledger`) carries one narrow, named exemption for exactly this
file, with the reason recorded in the test's own module docstring — not a directory-wide carve-out,
and not a relaxation of the promotion-verb or provenance-default guards, both of which still scan
`databasise/seam/selectors.py` unchanged. A second non-test ledger caller, or an `append()` call
appearing outside the test suite, still fails this test and still means this document needs another
update — this exception covers exactly one read path, not the general question.

## Degraded labelling — already landed, cited not rebuilt

RIG §TR.3's `partial`/`degraded`/`stop_reason`/`degradation_reason` required-together field set
is implemented, not proposed. `databasise/runner/trace.py`'s `RunRecord.__post_init__` refuses
to construct any record where `partial` and `degraded` disagree, or where either is true
without both `stop_reason` and `degradation_reason` populated, or where either is false while a
reason field is populated — grounded directly in RIG §TR.3's own "required-together set"
wording and the frozen schema's `allOf`/`if`-`then` rule. `databasise/runner/scheduler.py`
populates `degraded` and `degradation_reason` on a budget-halted or partial run (`degraded =
partial`, `degradation_reason = stop_reason`), and the result is schema-validated against
`docs/system-model/rig-trace.schema.json`.

Existing coverage, cited rather than duplicated:

- `databasise/tests/runner/test_run_record.py::test_8_a_degraded_run_names_its_path_a_clean_run_carries_none`
  — the required-together invariant and the degraded-names-its-path case.
- `databasise/tests/runner/test_live_metering.py::test_metered_node_over_allowance_halts_and_the_record_is_a_traced_budget_halt_partial_run`
  — a real budget-halted run carrying `record["degraded"] is True` with a populated
  `record["degradation_reason"]`.

This document adds no new assertions for the labelling half — it is already landed and
already tested.

## The operating mode

Per 02-CONTEXT.md **D-04**: human-in-the-loop verdicts are the operating mode. Under this
posture, the only enabled promotion path for the two default-off classes (answer-level,
index-side) is RIG §PR.3's `operator-asserted` path. Phase 6's comparison output is
verdict-free by design. Automated statistical verdict machinery requires explicit owner
opt-in.

An operator-asserted promotion stays visible in the ledger record as `promotion_provenance =
"operator_asserted"` — unmeasured, and recorded as unmeasured, never disguised as a
gate-adjudicated (`"gate_adjudicated"`) measured promotion.

## Condition for changing the posture

The posture stays off in v1 unless RIG §CM.3's four residual `[inference]` cost-model inputs
— **A1-A4** (the ~4-chars/token tokenizer heuristic, LLM call output-size banding, realized
query-time context utilization, and judge self-disagreement/cost) — are replaced by real
measurements. RIG §F3.2's own reversibility note states this plainly: switching a class on is
a build-time configuration act, not a structural amputation — the full apparatus enumerated
above as "disabled" stays specified in the contract and in this document; nothing about it is
removed.

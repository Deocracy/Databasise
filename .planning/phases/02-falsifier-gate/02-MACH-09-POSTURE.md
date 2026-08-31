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

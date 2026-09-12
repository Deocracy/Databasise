# Promotion Ledger Evidence — Phase 7 Success Criteria 1-3, Against the Committed Code

**Date:** 2026-09-12

`.planning/ROADMAP.md` Phase 7's success criteria, quoted verbatim (criteria 4 and 5 are struck —
see "What this phase does not deliver" below):

> 1. Every generation record in the append-only ledger carries both `change_origin` and
>    `promotion_provenance` — never defaulted, never inferable by absence — a semver is minted at
>    promotion and only at promotion, tombstoned losers are never lifted, and the active pointer
>    answers as a derived query over the ledger rather than a written field
> 2. Owner promotes a wiring by explicit call with `operator_asserted` provenance and non-empty
>    `promotion_trace_ids`, carrying no verdict and no tier-of-decision; the ledger append is the
>    decision and the alias repoint is atomic; rollback follows the same path
> 3. Promote-next and promote-now stay unavailable for answer-level and index-side mutation classes
>    under the default measurement posture, and the refusal names the posture rather than failing
>    silently

This document states, per criterion, whether it holds and **by which committed test** — a pytest
node id, not a prose assertion — following this project's own evidence-document discipline
(`F-14-SEAM-INVARIANCE.md`, `CROSS-MODALITY-EVIDENCE.md`). `tests/evidence/
test_promotion_ledger_record.py` asserts every node id cited below as "Holds" is genuinely
collectible by pytest, so this table cannot drift from the code without failing its own test.

## Criteria

| # | ROADMAP Phase 7 criterion | Holds | Tests |
|---|---|---|---|
| 1 | Every generation record carries `change_origin`/`promotion_provenance`, never defaulted; a semver is minted only at promotion; tombstoned losers are never lifted; the active pointer is a derived query | Holds | `tests/seam/test_promote.py::test_record_carries_change_origin_and_operator_asserted_provenance`, `tests/seam/test_promote.py::test_absent_change_origin_refuses_by_name`, `tests/seam/test_promote.py::test_first_promotion_mints_1_0_0`, `tests/seam/test_promote.py::test_no_path_mints_a_patch`, `tests/seam/test_retire.py::test_never_lifted_repromotion_is_a_new_generation`, `tests/ledger/test_ledger.py::test_3_active_pointer_is_computed_by_a_query_not_a_column` |
| 2 | Owner promotes with `operator_asserted` provenance and non-empty `promotion_trace_ids`, no verdict/tier-of-decision; the ledger append is the decision, the alias repoint is atomic; rollback follows the same path | Holds | `tests/seam/test_promote.py::test_promote_appends_one_row_the_alias_selector_resolves`, `tests/seam/test_promote.py::test_empty_trace_ids_refuses_before_any_write`, `tests/seam/test_rollback.py::test_rollback_repoints_the_alias_to_the_named_generation`, `tests/seam/test_rollback.py::test_rollback_carries_no_verdict` |
| 3 | `promote-next`/`promote-now` stay unavailable for answer-level and index-side classes under the default posture, and the refusal names the posture | Holds | `tests/seam/test_promotion_posture.py::test_promote_next_refuses_at_answer_level_naming_the_posture`, `tests/seam/test_promotion_posture.py::test_promote_next_refuses_at_retrieval_side_naming_the_missing_floor`, `tests/seam/test_promotion_posture.py::test_no_gate_verb_appends_a_row` |

Every row above is `[code-verified]`: read directly from `databasise/seam/engine.py`,
`databasise/seam/promotion.py`, `databasise/ledger/ledger.py` and the cited test files, this
session, not inferred from the plan text.

## API-09: the same three verbs, reachable identically over REST and MCP

Criteria 1-3 above are proven in-process. API-09 is the claim about what a *caller* can do —
reachable identically over REST and MCP, not just in-process — and this plan's own Task 1/2/3 work
proves that separately, over the same store, the same ledger, and the same refusal vocabulary:

- `tests/seam/test_rest_transport.py::test_post_promote_returns_the_same_result_as_the_in_process_call`
  and `test_post_rollback_and_post_retire_round_trip` — REST parity, `[code-verified]`
  `databasise/seam/rest.py`'s three thin routes over the identical `Databasise.promote`/`rollback`/
  `retire` methods.
- `tests/seam/test_dual_transport.py::test_promote_parity_across_three_transports`,
  `test_rollback_parity_across_three_transports`, `test_retire_parity_across_three_transports`,
  `test_refusal_parity_across_three_transports` — the same call, in-process, over REST and over
  MCP, produce field-equal responses and ledger records (every `LedgerRecord` field, since neither
  `id` nor `created_at` is part of that dataclass at all), and the identical refusal class on a
  disagreeing-trace-ids input.
- `tests/mcp/test_tool_growth_invariant.py::test_the_registered_tool_set_equals_tool_names_as_a_set_and_by_count`
  and `.../test_every_tool_has_a_coverage_row_and_every_both_transport_row_has_a_tool` — the roster
  grew by three names for three genuinely new §18 operations (§18.5), not by one name per modality,
  and the `.planning/phases/05-opaque-side-admission/COVERAGE.md` operations record agrees with the
  code.

These four tests require the optional `rest`/`mcp` extras to be installed to collect at all (each
module guards itself with `pytest.importorskip("fastapi")` or the shadow-safe `databasise.mcp`
import-and-skip pattern) — they are cited here in prose, not in the "Criteria" table above, because
`test_promotion_ledger_record.py`'s own collectibility check must pass under a bare `uv run pytest`
with neither extra installed (the exact posture this project's own `<verify>` blocks exercise
between commands), and a node id inside an extras-gated, import-time-skipped module is reported by
`pytest --collect-only` as "found no collectors" — a real collection error, not a graceful skip —
when named individually rather than run as a whole module or suite. All four tests are real,
committed, and pass in this session's own environment (both extras installed) — see "Method and
limits" below.

## What this phase does not deliver

Per `.planning/phases/07-promotion-rollback/07-GATE-AMENDMENT.md`: ROADMAP Phase 7's success
criteria 4 and 5 are struck, and their requirements (HARD-04, HARD-01, HARD-02) are deferred to the
owner's in-depth testing / hardening phase, or the first gate-adjudicated promotion, whichever comes
first. The argument, in one paragraph: an operator-asserted promotion (the only path this milestone
builds) reads no eval bundle, consumes no calibrated A/A floor, and produces no verdict — so nothing
in Phase 7 consumes the owner-corpus layer HARD-04 would add, or the gate-script/ANATOMY-doc repairs
HARD-01/HARD-02 would make. All three requirements stay Pending in `.planning/REQUIREMENTS.md`.

**Every promotion this milestone can make is operator-asserted, provisional, and carries no
verdict.** `PromotionResult`'s closed set (`alias`, `version`, `record_kind`, `provenance`,
`generation_ordinal`) never exposes a verdict field because none exists to expose:
`promotion_provenance` is always `"operator_asserted"` on every record this phase's three verbs can
write, `verdict`/`tier_of_decision`/`evidence_pointer` are always `None` on every such record
(`tests/seam/test_promote.py::test_record_carries_change_origin_and_operator_asserted_provenance`,
`tests/seam/test_rollback.py::test_rollback_carries_no_verdict`), and criterion 3's posture refusal
keeps the gate-adjudicated path — the only path that would ever produce a verdict — genuinely
unreachable under MACH-09's default posture
(`tests/seam/test_promotion_posture.py::test_no_gate_verb_appends_a_row`). Until a real
gate-adjudicated promotion supersedes it, no promoted wiring in this milestone has a measured
verdict behind it.

## Verdict

**ROADMAP Phase 7 success criteria 1, 2 and 3 hold**, each by a named, collectible, currently-
passing test, against the committed code as of this plan. Criteria 4 and 5 do not hold and are not
claimed to — they are struck and deferred per `07-GATE-AMENDMENT.md`, restated above rather than
omitted.

## Method and limits

**Method.** Every cited test in the "Criteria" table and the API-09 section above is a real,
committed test against real code — `databasise/seam/engine.py`'s `promote`/`rollback`/`retire`,
`databasise/seam/promotion.py`'s posture/semver/mutation-class rules, `databasise/ledger/ledger.py`'s
schema and projections, `databasise/seam/rest.py`'s three routes, and `databasise/mcp/server.py`'s
three tools — driven against synthetic, hand-seeded trace records (never a real corpus or a real
LLM call; `tests/seam/test_promote.py`'s own module docstring states why: the query-invariant
dispatched-node-id-set signal a promote call needs is fully expressible without running a wiring).

**Limits, stated plainly:**

- **The "Criteria" table's own collectibility check runs only against extras-free test files** (no
  `rest`/`mcp` extra required) — a deliberate scope narrowing so `test_promotion_ledger_record.py`
  passes under a bare `uv run pytest`, not a claim that the REST/MCP tests are less real; they are
  cited in prose above and are genuinely collected and passing in this session's environment (both
  extras installed).
- **No real corpus, no live LLM/embedding call, no real spend** anywhere in this document's cited
  tests — every promotion target is a hand-seeded trace record naming a real registered arm
  (`naive`/`bypass`), never a fabricated wiring document, but never a live query run either.
- **This document is scoped to ROADMAP Phase 7's criteria 1-3 only.** Criteria 4 and 5 (HARD-04,
  HARD-01, HARD-02) are addressed by restating the deferral, not by any evidence of their own —
  there is none to report, by design (see "What this phase does not deliver").

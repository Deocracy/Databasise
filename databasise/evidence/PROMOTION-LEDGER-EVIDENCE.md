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
| 2 | Owner promotes with `operator_asserted` provenance and non-empty `promotion_trace_ids`, no verdict/tier-of-decision; the ledger append is the decision, the alias repoint is atomic; rollback follows the same path | Holds | `tests/seam/test_promote.py::test_promote_appends_one_row_the_alias_selector_resolves`, `tests/seam/test_promote.py::test_empty_trace_ids_refuses_before_any_write`, `tests/seam/test_rollback.py::test_rollback_repoints_the_alias_to_the_named_generation`, `tests/seam/test_rollback.py::test_rollback_carries_no_verdict`, `tests/seam/test_operator_verb_concurrency.py::test_retire_vs_rollback_race_never_lets_a_rollback_outrun_a_tombstone`, `tests/seam/test_operator_verb_concurrency.py::test_six_concurrent_promotes_mint_six_distinct_versions_with_zero_exceptions`, `tests/ledger/test_ledger_generation_uniqueness.py::test_a_duplicate_non_null_alias_minted_version_pair_is_refused_by_the_database`, `tests/ledger/test_ledger_generation_uniqueness.py::test_reopening_a_database_carrying_the_old_plain_index_enforces_uniqueness` |
| 3 | `promote-next`/`promote-now` stay unavailable for answer-level and index-side classes under the default posture, and the refusal names the posture | Holds | `tests/seam/test_promotion_posture.py::test_promote_next_refuses_at_answer_level_naming_the_posture`, `tests/seam/test_promotion_posture.py::test_promote_next_refuses_at_retrieval_side_naming_the_missing_floor`, `tests/seam/test_promotion_posture.py::test_no_gate_verb_appends_a_row`, `tests/seam/test_promotion_posture.py::test_an_unrecognised_verb_refuses_by_name_before_any_trace_resolution[promote_next_typo]`, `tests/seam/test_dual_transport.py::test_an_out_of_enum_verb_refuses_identically_across_three_transports` |

Every row above is `[code-verified]`: read directly from `databasise/seam/engine.py`,
`databasise/seam/promotion.py`, `databasise/ledger/ledger.py` and the cited test files, this
session, not inferred from the plan text.

Criterion 3's verb-refusal architecture was completed in 07-04 after `07-VERIFICATION.md` scored it
partial (`07-REVIEW.md` CR-01): an out-of-enum `verb` string now refuses by name
(`UnrecognisedPromotionVerbError`) before any trace-id resolution runs, on all three transports,
rather than crashing with a bare `ValueError`.

### G-07-1 correction — 2026-09-12

Criterion 2's row body above is unchanged from how it originally read, per this document's own
append-only discipline (mirroring 06-17's correction note on `06-VERIFICATION.md`). This note states
what was not true before this plan, rather than rewriting or softening the row: **"the ledger append
is the decision, the alias repoint is atomic" was true of the single `INSERT` but not of the
decision until G-07-1 was closed by 07-05-PLAN.md.** The `INSERT` itself was always one atomic
statement; the guard read that decided *what* to insert (the tombstone check, the active-generation
check, the prior-version read the semver mint depends on) ran on a separate autocommit statement
before it, so a concurrent writer could commit between the two. `07-UAT.md` reproduced this against
unmodified library code: a `retire(v)`/`rollback(v)` race committed a rollback row after a tombstone
naming the same generation in 134/200 trials, and six concurrent `promote()` calls minted a
duplicate semver in 13/300 trials. `Ledger.transaction()` (a `BEGIN IMMEDIATE` span enclosing each
verb's guard read through its `append()`) closes this; the four newly-cited node ids above
re-reproduce both races at 20 trials each against the committed code and pass with zero violations.

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

- **The "Criteria" table's own collectibility check runs only against extras-free test files**,
  with one named exception added in 07-04: criterion 3 also cites
  `tests/seam/test_dual_transport.py::test_an_out_of_enum_verb_refuses_identically_across_three_transports`,
  which requires the `rest`/`mcp` extras to collect. That node id proves the three-transport parity
  07-VERIFICATION.md's `missing:` item 3 required; every other cited node id in the table stays
  extras-free. `test_promotion_ledger_record.py`'s own collectibility check runs in this project's
  own dev environment, where both extras are already installed, so this does not change the check's
  own pass/fail outcome here — it is stated so a reader running the check in a bare, extras-free
  environment understands why this one node id would report "found no collectors" there.
- **No real corpus, no live LLM/embedding call, no real spend** anywhere in this document's cited
  tests — every promotion target is a hand-seeded trace record naming a real registered arm
  (`naive`/`bypass`), never a fabricated wiring document, but never a live query run either.
- **This document is scoped to ROADMAP Phase 7's criteria 1-3 only.** Criteria 4 and 5 (HARD-04,
  HARD-01, HARD-02) are addressed by restating the deferral, not by any evidence of their own —
  there is none to report, by design (see "What this phase does not deliver").

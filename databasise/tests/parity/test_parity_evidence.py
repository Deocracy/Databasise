"""Tests for ``databasise/evidence/parity_report.py`` (03-09-PLAN.md Task 2).

All cases here run against hand-built inputs or the real committed ``parity_results/`` directory
already on disk — no venv, no network, no live index. This is deliberate: the plan's own
environment gap (no ``v1/.venv``, ``v1/.parity_working_dir``, ``v1/.parity_v2_store``,
``v1/.env.parity`` on this machine) means the harness itself never produces a "completed"
comparison result in this session, so this suite proves the *renderer's* refusals, provenance
checks, and pure-function stability directly against fixtures shaped either way — never assuming
which shape the committed files happen to carry.
"""

from __future__ import annotations

import json

import pytest
from databasise.evidence import parity_report
from databasise.evidence.parity_report import (
    ARMS,
    DeclaredDeviation,
    StaleDeviationCauseError,
    UnreasonedDeviationError,
    check_results,
    render_deviations_markdown,
    render_markdown,
)


# --------------------------------------------------------------------------------------------- #
# check_results() — the provenance validator
# --------------------------------------------------------------------------------------------- #


def test_the_real_committed_parity_results_directory_passes_the_provenance_check():
    """Non-vacuous proof that the actual committed evidence (Task 1's real output) satisfies its
    own validator — not just a hand-built fixture.
    """
    violations = check_results()
    assert violations == []


def _write_comparison(tmp_path, arm, records):
    (tmp_path / f"{arm}-comparison.json").write_text(json.dumps(records), encoding="utf-8")


def _write_audit(tmp_path, arm, audit):
    (tmp_path / f"{arm}-storage-audit.json").write_text(json.dumps(audit), encoding="utf-8")


_MINIMAL_AUDIT = {
    "arm": "x",
    "command": "x",
    "exit_code": 1,
    "status": "inconclusive",
    "outcome": "environment_precondition_failed",
    "reason": "test fixture",
}

_MINIMAL_INCONCLUSIVE_RECORD = {
    "status": "inconclusive",
    "arm": "x",
    "query_id": "q1",
    "query": "test",
    "corpus_hash": "abc",
    "determinism_setting": "cache-bypassed",
    "concurrency_setting": "sequential",
    "run_count": 0,
    "resolved_model_identities": {},
    "inconclusive_reason": "test fixture precondition failure",
    "chunk_diff": None,
    "entity_diff": None,
    "relation_diff": None,
    "keyword_variance_band": None,
}


def _write_complete_fixture_set(tmp_path):
    for arm in ARMS:
        _write_comparison(tmp_path, arm, [{**_MINIMAL_INCONCLUSIVE_RECORD, "arm": arm}])
        _write_audit(tmp_path, arm, {**_MINIMAL_AUDIT, "arm": arm})


def test_a_complete_hand_built_fixture_set_passes_clean(tmp_path):
    _write_complete_fixture_set(tmp_path)

    assert check_results(results_dir=tmp_path) == []


def test_a_missing_comparison_file_is_reported(tmp_path):
    _write_complete_fixture_set(tmp_path)
    (tmp_path / "naive-comparison.json").unlink()

    violations = check_results(results_dir=tmp_path)

    assert any("naive-comparison.json" in v.file and "does not exist" in v.detail for v in violations)


def test_a_comparison_record_missing_a_required_key_is_reported(tmp_path):
    _write_complete_fixture_set(tmp_path)
    broken = dict(_MINIMAL_INCONCLUSIVE_RECORD)
    del broken["corpus_hash"]
    _write_comparison(tmp_path, "naive", [broken])

    violations = check_results(results_dir=tmp_path)

    assert any("corpus_hash" in v.detail for v in violations)


def test_an_inconclusive_record_carrying_a_comparison_number_is_refused(tmp_path):
    """The plan's own stated prohibition: 'No result file carries a comparison number alongside
    an `inconclusive` outcome.'
    """
    _write_complete_fixture_set(tmp_path)
    tainted = dict(_MINIMAL_INCONCLUSIVE_RECORD)
    tainted["chunk_diff"] = {
        "decomposed_ids": [],
        "original_ids": [],
        "symmetric_difference": [],
        "ranking_agreement": 1.0,
        "first_disagreement_position": None,
    }
    _write_comparison(tmp_path, "naive", [tainted])

    violations = check_results(results_dir=tmp_path)

    assert any("comparison number" in v.detail for v in violations)


def test_an_inconclusive_record_with_no_stated_reason_is_reported(tmp_path):
    _write_complete_fixture_set(tmp_path)
    unreasoned = dict(_MINIMAL_INCONCLUSIVE_RECORD)
    unreasoned["inconclusive_reason"] = None
    _write_comparison(tmp_path, "naive", [unreasoned])

    violations = check_results(results_dir=tmp_path)

    assert any("names no reason" in v.detail for v in violations)


def test_a_storage_audit_file_missing_a_required_key_is_reported(tmp_path):
    _write_complete_fixture_set(tmp_path)
    broken_audit = dict(_MINIMAL_AUDIT)
    del broken_audit["reason"]
    _write_audit(tmp_path, "naive", broken_audit)

    violations = check_results(results_dir=tmp_path)

    assert any("naive-storage-audit.json" in v.file and "reason" in v.detail for v in violations)


_EMPTY_DIFF = {
    "decomposed_ids": [],
    "original_ids": [],
    "symmetric_difference": [],
    "ranking_agreement": 1.0,
    "first_disagreement_position": None,
}


def test_degraded_but_vacuous_arms_flags_a_completed_record_that_crashed_before_retrieving(tmp_path):
    """WR-03 (03-REVIEW.md): a ``status="completed"`` record whose ``decomposed_run_record.degraded``
    is true and whose comparison numbers are all empty diffs passes ``check_results()`` cleanly, but
    :func:`parity_report._degraded_but_vacuous_arms` must still name it so the CLI's "clean" line
    can be qualified rather than reading as "every arm's numbers are trustworthy."
    """
    _write_complete_fixture_set(tmp_path)
    degraded_record = {
        **_MINIMAL_INCONCLUSIVE_RECORD,
        "arm": "hybrid",
        "status": "completed",
        "inconclusive_reason": None,
        "chunk_diff": _EMPTY_DIFF,
        "entity_diff": _EMPTY_DIFF,
        "relation_diff": _EMPTY_DIFF,
        "decomposed_run_record": {"degraded": True, "degradation_reason": "crashed"},
    }
    _write_comparison(tmp_path, "hybrid", [degraded_record])

    assert check_results(results_dir=tmp_path) == []
    assert parity_report._degraded_but_vacuous_arms(results_dir=tmp_path) == ["hybrid"]


def test_degraded_but_vacuous_arms_ignores_a_clean_completed_record(tmp_path):
    _write_complete_fixture_set(tmp_path)
    clean_record = {
        **_MINIMAL_INCONCLUSIVE_RECORD,
        "arm": "hybrid",
        "status": "completed",
        "inconclusive_reason": None,
        "chunk_diff": _EMPTY_DIFF,
        "entity_diff": _EMPTY_DIFF,
        "relation_diff": _EMPTY_DIFF,
        "decomposed_run_record": {"degraded": False},
    }
    _write_comparison(tmp_path, "hybrid", [clean_record])

    assert parity_report._degraded_but_vacuous_arms(results_dir=tmp_path) == []


def test_degraded_but_vacuous_arms_on_the_real_committed_data_names_the_three_known_degraded_arms():
    """Non-vacuous proof against the actual committed evidence: CR-01's crash affects exactly
    ``hybrid``/``local``/``global`` today (see ``PARITY-EVIDENCE.md``'s own Verdict section).
    """
    assert parity_report._degraded_but_vacuous_arms() == ["hybrid", "local", "global"]


# --------------------------------------------------------------------------------------------- #
# render_deviations_markdown() — the CONTRACT §5 refusal
# --------------------------------------------------------------------------------------------- #


def test_zero_deviations_renders_an_explicit_stated_zero_not_an_empty_document():
    """Against the real committed data, which is now a completed run (03-10-PLAN.md Task 1):
    zero deviations reads as "the comparison ran and found no excursion", not "nothing has
    been measured yet" — see the companion inconclusive-fixture test below for the other
    direction.
    """
    text = render_deviations_markdown([])

    assert "Zero declared deviations" in text
    assert "completed comparison that found no excursion" in text
    # CR-01: the known design deviation is renderer-owned, so a re-render never drops it.
    assert "Known design deviation (pending measurement)" in text


def test_zero_deviations_against_an_inconclusive_fixture_states_nothing_measured_yet(
    tmp_path, monkeypatch
):
    """The other direction of the same behavior, proven against a fixture set rather than
    against whatever the committed files happen to hold (03-10-PLAN.md Task 2's own
    instruction).
    """
    _write_complete_fixture_set(tmp_path)  # every arm status="inconclusive"
    monkeypatch.setattr(parity_report, "RESULTS_DIR", tmp_path)

    text = render_deviations_markdown([])

    assert "Zero declared deviations" in text
    assert "no completed comparison run has occurred" in text


def test_committed_deviations_document_matches_a_fresh_render():
    from databasise.evidence.parity_report import DEVIATIONS_PATH, _collect_deviations

    assert DEVIATIONS_PATH.read_text(encoding="utf-8") == render_deviations_markdown(
        _collect_deviations()
    )


def test_a_deviation_with_an_empty_cause_makes_the_render_fail():
    deviation = DeclaredDeviation(arm="hybrid", query_id="q1", description="chunk drift", cause="")

    with pytest.raises(UnreasonedDeviationError):
        render_deviations_markdown([deviation])


@pytest.mark.parametrize(
    "generic_cause",
    ["expected variance", "Expected Variance", "  noise  ", "n/a", "N/A", "unknown", "tbd"],
)
def test_a_deviation_with_a_generic_blanket_cause_makes_the_render_fail(generic_cause):
    deviation = DeclaredDeviation(
        arm="hybrid", query_id="q1", description="chunk drift", cause=generic_cause
    )

    with pytest.raises(UnreasonedDeviationError):
        render_deviations_markdown([deviation])


def test_a_deviation_with_a_specific_named_cause_renders_successfully():
    deviation = DeclaredDeviation(
        arm="local",
        query_id="q2",
        description="chunk sym_diff=1 (chunk-042 present only in the original arm)",
        cause=(
            "join-roundrobin's tie-break on equal rank_position differs from v1's own "
            "sorted-by-src_tgt tie-break when two candidate chunks share an identical score"
        ),
    )

    text = render_deviations_markdown([deviation])

    assert "join-roundrobin's tie-break" in text
    assert "local" in text
    assert "q2" in text


def test_one_bad_cause_among_several_good_ones_still_fails_the_whole_render():
    """The renderer fails the whole document rather than silently dropping the one bad row —
    see module docstring: 'the whole render fails rather than emitting a document with one bad
    row.'
    """
    good = DeclaredDeviation(
        arm="hybrid", query_id="q1", description="d1", cause="a specific named cause"
    )
    bad = DeclaredDeviation(arm="hybrid", query_id="q2", description="d2", cause="expected")

    with pytest.raises(UnreasonedDeviationError):
        render_deviations_markdown([good, bad])


# --------------------------------------------------------------------------------------------- #
# render_markdown() — pure-function stability and required content
# --------------------------------------------------------------------------------------------- #


def test_render_markdown_is_byte_identical_across_two_calls():
    assert render_markdown() == render_markdown()


def test_render_markdown_matches_the_committed_evidence_document_on_disk():
    """Non-vacuous proof the committed PARITY-EVIDENCE.md is not stale — mirrors
    ``test_falsifier2_evidence.py``'s own ``test_committed_evidence_document_matches_a_fresh_render``.
    """
    from databasise.evidence.parity_report import EVIDENCE_PATH

    assert EVIDENCE_PATH.read_text(encoding="utf-8") == render_markdown()


def test_render_markdown_cites_the_gate_amendment():
    assert "03-GATE-AMENDMENT" in render_markdown()


def test_render_markdown_states_the_keyword_variance_bands_own_n_in_the_band_table():
    text = render_markdown()

    assert "N = 5 runs" in text


def test_render_markdown_counts_matched_no_touch_and_over_declared_separately():
    text = render_markdown()

    assert "| arm | matched | no-touch | over-declared | outcome |" in text


def test_render_markdown_never_emits_a_pass_or_fail_verdict_for_an_inconclusive_fixture_set(
    tmp_path, monkeypatch
):
    """The real committed data is now a completed run (03-10-PLAN.md Task 1), so this proves
    D-02's refusal-over-verdict prohibition against a fixture set rather than against whatever
    the committed files happen to hold — the plan's own instruction for this rewrite.
    """
    _write_complete_fixture_set(tmp_path)  # every arm status="inconclusive"
    monkeypatch.setattr(parity_report, "RESULTS_DIR", tmp_path)

    text = render_markdown()

    assert "No parity verdict is recorded" in text
    assert "environment-precondition refusal" in text


def test_render_markdown_names_every_arm():
    text = render_markdown()

    for arm in ARMS:
        assert f"`{arm}`" in text


# --------------------------------------------------------------------------------------------- #
# render_markdown() — the completed direction, proven against the real committed data
# --------------------------------------------------------------------------------------------- #


def test_render_markdown_completed_direction_carries_real_storage_audit_counts():
    """Task 2's own acceptance criterion: the real storage-audit counts for hybrid appear as
    rendered cells, not the pre-run 'matched=0 no-touch=0 over-declared=0' narrative.
    """
    text = render_markdown()

    assert "matched=12" in text
    assert "no-touch=5" in text


def test_render_markdown_states_not_applicable_for_an_arm_with_no_keywords_node():
    """`naive`/`bypass` are completed but have no `keywords` node — their null band cell reads
    as not-applicable, never as an echo of the record's own status (the pre-fix bug this test
    guards: 'not run — completed' is meaningless for a completed record).
    """
    text = render_markdown()

    assert "not applicable — naive's wiring has no `keywords` node" in text
    assert "not run — completed" not in text


def test_render_markdown_states_the_hybrid_local_global_degradation_rather_than_a_clean_pass():
    """`hybrid`/`local`/`global`'s decomposed runs degraded before completing a real retrieval
    (entity-hydrate-expand / relation-hydrate-expand crashed) — the zero symmetric_difference on
    those three arms is not read as a validated retrieval-level match.
    """
    text = render_markdown()

    assert "Degraded run" in text
    assert "not read as exact retrieval-level agreement" in text


# --------------------------------------------------------------------------------------------- #
# _run_state() and StaleDeviationCauseError (03-10-PLAN.md Task 2)
# --------------------------------------------------------------------------------------------- #


def test_run_state_on_the_real_committed_data_is_completed():
    assert parity_report._run_state() == "completed"


def test_run_state_on_an_all_inconclusive_fixture_is_inconclusive(tmp_path, monkeypatch):
    _write_complete_fixture_set(tmp_path)
    monkeypatch.setattr(parity_report, "RESULTS_DIR", tmp_path)

    assert parity_report._run_state() == "inconclusive"


def test_run_state_on_a_mixed_fixture_is_mixed(tmp_path, monkeypatch):
    _write_complete_fixture_set(tmp_path)
    completed = dict(_MINIMAL_INCONCLUSIVE_RECORD)
    completed["status"] = "completed"
    completed["chunk_diff"] = {
        "decomposed_ids": [],
        "original_ids": [],
        "symmetric_difference": [],
        "ranking_agreement": 1.0,
        "first_disagreement_position": None,
    }
    _write_comparison(tmp_path, "naive", [completed])
    monkeypatch.setattr(parity_report, "RESULTS_DIR", tmp_path)

    assert parity_report._run_state() == "mixed"


def test_a_completed_excursion_whose_recorded_cause_no_longer_matches_the_measurement_raises_stale(
    tmp_path, monkeypatch
):
    """03-10-PLAN.md Task 1/Task 2: a re-run that changes the measured symmetric_difference
    invalidates a recorded cause rather than silently inheriting it.
    """
    stale_record = dict(_MINIMAL_INCONCLUSIVE_RECORD)
    stale_record.update(
        status="completed",
        arm="naive",
        query_id="q1",
        resolved_model_identities={
            "decomposed_generate": "m",
            "original_arm_llm_model": "m",
            "original_arm_embedding_model": "e",
        },
        chunk_diff={
            "decomposed_ids": [],
            "original_ids": ["a"],
            "symmetric_difference": ["a"],
            "ranking_agreement": 1.0,
            "first_disagreement_position": 0,
        },
    )
    for arm in ARMS:
        if arm == "naive":
            _write_comparison(tmp_path, arm, [stale_record])
        else:
            _write_comparison(tmp_path, arm, [{**_MINIMAL_INCONCLUSIVE_RECORD, "arm": arm}])
        _write_audit(tmp_path, arm, {**_MINIMAL_AUDIT, "arm": arm})

    findings_path = tmp_path / "human_findings.json"
    findings_path.write_text(
        json.dumps(
            {
                "declared_causes": [
                    {
                        "arm": "naive",
                        "query_id": "q1",
                        "field": "chunk_diff",
                        "symmetric_difference": ["b"],  # stale: measured is now ["a"]
                        "cause": "some previously-recorded, now-stale cause text",
                    }
                ],
                "answer_spotchecks": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(parity_report, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(parity_report, "HUMAN_FINDINGS_PATH", findings_path)

    with pytest.raises(StaleDeviationCauseError):
        parity_report._collect_deviations()


# --------------------------------------------------------------------------------------------- #
# _render_answer_spotcheck() / AnswerSpotCheck (03-10-PLAN.md Task 3)
# --------------------------------------------------------------------------------------------- #


def test_answer_spotcheck_section_names_both_queries_as_unrecorded_by_default():
    text = render_markdown()

    assert "Human spot-check of answer substance" in text
    assert "human_findings.json" in text
    assert "03-VALIDATION.md" in text
    assert "### `q1`" in text
    assert "### `q2`" in text
    assert "Not yet recorded" in text
    # No judgment is rendered as if it were the recorded verdict for an unrecorded query.
    assert "**Judgment:" not in text


def test_a_recorded_answer_spotcheck_entry_renders_its_judgment_and_notes(tmp_path, monkeypatch):
    findings_path = tmp_path / "human_findings.json"
    findings_path.write_text(
        json.dumps(
            {
                "declared_causes": [],
                "answer_spotchecks": [
                    {
                        "query_id": "q1",
                        "arm": "hybrid",
                        "judgment": "match",
                        "notes": "both answers name the same nationality and cite the same facts",
                        "recorded_by": "owner",
                        "recorded_at": "2026-09-02",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(parity_report, "HUMAN_FINDINGS_PATH", findings_path)

    text = parity_report._render_answer_spotcheck()

    assert "**Judgment: `match`**" in text
    assert "both answers name the same nationality" in text
    assert "### `q2`" in text  # the other query still renders as unrecorded
    assert "Not yet recorded" in text  # for q2, since only q1 was written


def test_an_invalid_judgment_value_raises_rather_than_rendering(tmp_path, monkeypatch):
    findings_path = tmp_path / "human_findings.json"
    findings_path.write_text(
        json.dumps(
            {
                "declared_causes": [],
                "answer_spotchecks": [
                    {
                        "query_id": "q1",
                        "arm": "hybrid",
                        "judgment": "sort of agrees",  # not a valid judgment value
                        "notes": "",
                        "recorded_by": "owner",
                        "recorded_at": "2026-09-02",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(parity_report, "HUMAN_FINDINGS_PATH", findings_path)

    with pytest.raises(parity_report.InvalidJudgmentError):
        parity_report._render_answer_spotcheck()


# --------------------------------------------------------------------------------------------- #
# 03-10 fix cycle (adversarial-audit findings 1-8)
# --------------------------------------------------------------------------------------------- #

_KEYWORD_BAND = {
    "run_count": 5,
    "high_level_frequency": {},
    "low_level_frequency": {},
    "high_level_size_mean": 2.0,
    "high_level_size_stdev": 0.0,
    "low_level_size_mean": 2.0,
    "low_level_size_stdev": 0.0,
    "any_cache_served": False,
}

_ZERO_DIFF = {
    "decomposed_ids": [],
    "original_ids": [],
    "symmetric_difference": [],
    "ranking_agreement": 1.0,
    "first_disagreement_position": None,
}

_RESOLVED_IDENTITIES = {
    "decomposed_generate": "m",
    "original_arm_llm_model": "m",
    "original_arm_embedding_model": "e",
}


def _completed_record(arm, query_id, **overrides):
    record = dict(_MINIMAL_INCONCLUSIVE_RECORD)
    record.update(
        status="completed",
        arm=arm,
        query_id=query_id,
        resolved_model_identities=dict(_RESOLVED_IDENTITIES),
        decomposed_run_record={
            "degraded": False,
            "degradation_reason": None,
            "stop_reason": None,
            "nodes": [],
        },
        original_arm_result={"answer": "an answer"},
        original_arm_instrumentation="harness-external",
    )
    record.update(overrides)
    return record


def _write_clean_completed_fixture_set(tmp_path):
    """Every arm `completed`, no arm's `decomposed_run_record.degraded` set — the direction
    03-10 fix cycle finding 2 requires: a clean fixture set renders no crash assertion.
    """
    for arm in ("naive", "bypass", "hybrid", "local", "global"):
        records = [_completed_record(arm, "q1"), _completed_record(arm, "q2")]
        if arm == "bypass":
            for record in records:
                record["retrieval_note"] = "no retrieval to compare"
        elif arm == "naive":
            for record in records:
                record["chunk_diff"] = dict(_ZERO_DIFF)
        else:  # hybrid, local, global
            for record in records:
                record["chunk_diff"] = dict(_ZERO_DIFF)
                record["entity_diff"] = dict(_ZERO_DIFF)
                record["relation_diff"] = dict(_ZERO_DIFF)
                record["keyword_variance_band"] = dict(_KEYWORD_BAND)
        _write_comparison(tmp_path, arm, records)
        _write_audit(
            tmp_path,
            arm,
            {
                **_MINIMAL_AUDIT,
                "arm": arm,
                "status": "completed",
                "outcome": "clean",
                "matched_count": 1,
                "no_touch_count": 0,
                "over_declared_count": 0,
                "rows": [],
            },
        )


def test_render_markdown_for_a_clean_completed_fixture_set_asserts_no_crash(tmp_path, monkeypatch):
    """03-10 fix cycle finding 2: the degradation disclosure must be derived, not hardcoded —
    proven by re-rendering the completed-and-NOT-degraded direction and asserting no crash claim
    survives (this is the exact defect the fix cycle closes: hardcoded prose asserting a crash
    that did not happen).
    """
    _write_clean_completed_fixture_set(tmp_path)
    monkeypatch.setattr(parity_report, "RESULTS_DIR", tmp_path)

    text = render_markdown()

    assert "NodeExecutionError" not in text
    assert "Degraded run" not in text
    assert "crash-truncated" not in text
    assert "validated exact retrieval-level agreement" in text


def test_render_markdown_for_an_inconclusive_fixture_set_asserts_no_pass_or_fail_verdict_word(
    tmp_path, monkeypatch
):
    """03-10 fix cycle finding 4: the companion test above (`..._never_emits_a_pass_or_fail...`)
    only proves the refusal strings are present; a literal 'VERDICT: PASS' injected into the
    inconclusive branch would leave that test green. This proves the absence too.
    """
    _write_complete_fixture_set(tmp_path)  # every arm status="inconclusive"
    monkeypatch.setattr(parity_report, "RESULTS_DIR", tmp_path)

    text = parity_report._render_verdict()

    assert "No parity verdict is recorded" in text
    for banned in ("VERDICT: PASS", "VERDICT: FAIL", "**PASS**", "**FAIL**"):
        assert banned not in text


def test_a_completed_excursion_with_no_declared_cause_makes_the_whole_render_fail(
    tmp_path, monkeypatch
):
    """CONTRACT §5's central refusal (03-10-PLAN.md must_haves truth 3 / prohibition 1; 03-10 fix
    cycle finding 3): a completed excursion with no recorded cause aborts the render entirely —
    proven directly here rather than only by the plan's own manual <verify> step of emptying
    human_findings.json.
    """
    record = _completed_record(
        "naive",
        "q1",
        chunk_diff={
            "decomposed_ids": [],
            "original_ids": ["a"],
            "symmetric_difference": ["a"],
            "ranking_agreement": 1.0,
            "first_disagreement_position": 0,
        },
    )
    for arm in ARMS:
        if arm == "naive":
            _write_comparison(tmp_path, arm, [record])
        else:
            _write_comparison(tmp_path, arm, [{**_MINIMAL_INCONCLUSIVE_RECORD, "arm": arm}])
        _write_audit(tmp_path, arm, {**_MINIMAL_AUDIT, "arm": arm})

    findings_path = tmp_path / "human_findings.json"
    findings_path.write_text(
        json.dumps({"declared_causes": [], "answer_spotchecks": []}), encoding="utf-8"
    )

    monkeypatch.setattr(parity_report, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(parity_report, "HUMAN_FINDINGS_PATH", findings_path)

    deviations = parity_report._collect_deviations()
    with pytest.raises(UnreasonedDeviationError) as exc_info:
        render_deviations_markdown(deviations)
    assert str(findings_path) in str(exc_info.value)


def test_an_orphan_declared_cause_entry_makes_the_render_fail(tmp_path, monkeypatch):
    """03-10 fix cycle finding 7: a `declared_causes` entry whose (arm, query_id, field) triple
    matches no measured excursion must refuse, not silently sit in the file describing nothing.
    """
    for arm in ARMS:
        _write_comparison(tmp_path, arm, [{**_MINIMAL_INCONCLUSIVE_RECORD, "arm": arm}])
        _write_audit(tmp_path, arm, {**_MINIMAL_AUDIT, "arm": arm})

    findings_path = tmp_path / "human_findings.json"
    findings_path.write_text(
        json.dumps(
            {
                "declared_causes": [
                    {
                        "arm": "naive",
                        "query_id": "q1",
                        "field": "chunk_diff",
                        "symmetric_difference": ["a"],
                        "cause": "a cause for an excursion that was never actually measured",
                    }
                ],
                "answer_spotchecks": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(parity_report, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(parity_report, "HUMAN_FINDINGS_PATH", findings_path)

    with pytest.raises(parity_report.OrphanDeviationCauseError):
        parity_report._collect_deviations()

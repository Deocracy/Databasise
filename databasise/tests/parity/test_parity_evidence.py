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
from databasise.evidence.parity_report import (
    ARMS,
    DeclaredDeviation,
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


# --------------------------------------------------------------------------------------------- #
# render_deviations_markdown() — the CONTRACT §5 refusal
# --------------------------------------------------------------------------------------------- #


def test_zero_deviations_renders_an_explicit_stated_zero_not_an_empty_document():
    text = render_deviations_markdown([])

    assert "Zero declared deviations" in text
    assert "no completed comparison run has occurred" in text


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


def test_render_markdown_never_emits_a_pass_or_fail_verdict_for_the_current_inconclusive_state():
    text = render_markdown()

    assert "No parity verdict is recorded" in text
    assert "environment-precondition refusal" in text


def test_render_markdown_names_every_arm():
    text = render_markdown()

    for arm in ARMS:
        assert f"`{arm}`" in text

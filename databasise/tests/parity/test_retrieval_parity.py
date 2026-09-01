"""Tests for ``databasise/parity/run_comparison.py`` (03-07-PLAN.md Task 3).

Split into two groups, per this module's own docstring convention (see e.g.
``databasise/tests/stores/test_graph_frozen_bugs.py``):

- **Deterministic group** — the retrieval-diff arithmetic and the index-identity precondition
  gate, run against hand-built inputs and a stub ``verify_fn``. No ``v1/`` venv, no imported
  index, no network; carries no skip marker. This group is what keeps this plan's own
  verification non-vacuous on any machine.
- **Environment-dependent group** — the full two-arm comparison against the real imported index
  and both live endpoints. Uses the plan 03-02 conftest fixtures
  (``v1_venv_python``/``v2_parity_store_dir``/``v1_env_parity_path``) and skips cleanly when the
  venv, the index, or the endpoints are absent — the same skip-guard shape
  ``test_naive_arm_end_to_end.py`` and ``test_import_verification.py`` already use.
"""

from __future__ import annotations

import pytest
from databasise.parity.import_index import VerificationResult, Violation
from databasise.parity.run_comparison import (
    _no_retrieval_to_compare_note,
    compare_arm_on_query,
    diff_ranked_ids,
)
from databasise.wirings.resolve import resolve_arm

# --------------------------------------------------------------------------------------------- #
# Deterministic group — no venv, no index, no network
# --------------------------------------------------------------------------------------------- #


def test_an_arm_with_a_chunk_source_node_gets_no_retrieval_note():
    assert _no_retrieval_to_compare_note("hybrid", has_chunk_node=True) is None


def test_an_arm_with_no_chunk_source_node_gets_a_distinct_note_not_a_computed_diff():
    note = _no_retrieval_to_compare_note("bypass", has_chunk_node=False)

    assert note is not None
    assert "bypass" in note
    assert "no retrieval" in note


def test_the_bypass_arms_resolved_node_set_actually_has_no_chunk_source_node():
    """Regression guard for the fact ``_no_retrieval_to_compare_note`` depends on: if a future
    wiring change ever adds a ``rerank`` node to ``bypass``, this test — not a silent perfect-
    agreement diff — is what should fail first.
    """
    resolved = resolve_arm("bypass")
    assert "rerank" not in resolved.get("nodes", {})


def test_identical_ranked_lists_report_zero_symmetric_difference_and_full_agreement():
    diff = diff_ranked_ids(["c1", "c2", "c3"], ["c1", "c2", "c3"])

    assert diff.symmetric_difference == ()
    assert diff.ranking_agreement == 1.0
    assert diff.first_disagreement_position is None


def test_disjoint_ranked_lists_report_full_symmetric_difference_and_no_agreement():
    diff = diff_ranked_ids(["a", "b"], ["c", "d"])

    assert set(diff.symmetric_difference) == {"a", "b", "c", "d"}
    assert diff.ranking_agreement == 0.0
    assert diff.first_disagreement_position == 0


def test_both_empty_ranked_lists_report_zero_symmetric_difference_and_full_agreement():
    diff = diff_ranked_ids([], [])

    assert diff.symmetric_difference == ()
    assert diff.ranking_agreement == 1.0
    assert diff.first_disagreement_position is None


def test_partial_overlap_reports_symmetric_difference_ranking_agreement_and_first_disagreement():
    # decomposed keeps b before a (swapped relative to original) and adds an extra id c;
    # original has an extra id d instead.
    diff = diff_ranked_ids(["b", "a", "c"], ["a", "b", "d"])

    assert set(diff.symmetric_difference) == {"c", "d"}
    # Among the two common ids (a, b): decomposed orders b-then-a, original orders a-then-b —
    # the one pair disagrees, so the concordance fraction is 0.0.
    assert diff.ranking_agreement == 0.0
    # Position-by-position: index 0 is "b" vs "a" — first disagreement is at position 0.
    assert diff.first_disagreement_position == 0


def test_prefix_agreement_reports_first_disagreement_at_the_length_of_the_shorter_list():
    diff = diff_ranked_ids(["a", "b"], ["a", "b", "c"])

    assert diff.symmetric_difference == ("c",)
    assert diff.first_disagreement_position == 2


def test_diff_ranked_ids_is_reachable_with_no_client_or_store_wired_at_all():
    """The retrieval-level diff makes no LLM call, no store call, no client call of any kind
    (criterion 6 / D-10) — proven here by calling it with nothing but two plain lists, no
    ``NodeContext``, no clients dict, no store at all.
    """
    diff = diff_ranked_ids(["x"], ["x"])
    assert diff.ranking_agreement == 1.0


async def test_a_forced_precondition_failure_yields_inconclusive_and_records_no_comparison_number():
    async def _forced_failing_verify(**kwargs: object) -> VerificationResult:
        return VerificationResult(
            status="inconclusive",
            violations=(
                Violation(assertion="chunk-text", detail="forced test failure", offending_id="chunk-1"),
            ),
        )

    record = await compare_arm_on_query(
        "naive", "q-forced-fail", "does not matter — the gate refuses before this is used",
        verify_fn=_forced_failing_verify,
    )

    assert record.status == "inconclusive"
    assert record.inconclusive_reason is not None
    assert "forced test failure" in record.inconclusive_reason
    assert record.run_count == 0
    assert record.chunk_diff is None
    assert record.entity_diff is None
    assert record.relation_diff is None
    assert record.decomposed_run_record is None
    assert record.original_arm_result is None
    assert record.pinned_keywords is None


async def test_a_refused_precondition_also_yields_inconclusive_never_a_plain_verdict():
    async def _refused_verify(**kwargs: object) -> VerificationResult:
        return VerificationResult(status="refused")

    record = await compare_arm_on_query(
        "naive", "q-refused", "irrelevant query text", verify_fn=_refused_verify
    )

    assert record.status == "inconclusive"
    assert record.chunk_diff is None


# --------------------------------------------------------------------------------------------- #
# Environment-dependent group — real index, real endpoints, skip-guarded
# --------------------------------------------------------------------------------------------- #


async def test_real_naive_arm_comparison_runs_end_to_end_against_the_real_index(
    v1_venv_python, v2_parity_store_dir, v1_env_parity_path, corpus_snapshot
):
    del v1_venv_python  # presence asserted by the fixture itself; not read directly here
    query = corpus_snapshot.queries[0]

    record = await compare_arm_on_query(
        "naive",
        query.id,
        query.question,
        corpus_hash=corpus_snapshot.corpus_hash,
        env_path=v1_env_parity_path,
    )

    assert record.status == "completed"
    assert record.chunk_diff is not None
    assert record.decomposed_run_record is not None
    assert record.original_arm_result is not None
    assert record.original_arm_result["instrumentation"] == "harness-external"

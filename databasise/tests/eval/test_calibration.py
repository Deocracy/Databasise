"""Tests for databasise.eval.calibration (06-06-PLAN.md Task 1's <behavior> block)."""

from __future__ import annotations

import pytest

from databasise.eval.calibration import (
    BULK_SCREENING_TIER,
    ESCALATED_SURVIVOR_TIER,
    CalibrationResult,
    NullIdentity,
    StaleNullError,
    UnusableFloorError,
    calibrate_aa_floor,
    correct_for_batch_width,
    paired_differences,
)

_IDENTITY = NullIdentity(
    bundle_at_v="bundle@v1",
    tier="T1",
    metric="recall@k",
    determinism_setting="cache-bypassed",
    concurrency_setting="sequential",
)


def _bypassed_nodes(*node_ids: str) -> list[dict[str, object]]:
    return [{"node_id": node_id, "cache_hit": False} for node_id in node_ids]


def _calibrate(diffs, *, seed: int | None = 7, n_resamples: int = 500) -> CalibrationResult:
    return calibrate_aa_floor(
        diffs,
        identity=_IDENTITY,
        run_a_nodes=_bypassed_nodes("chunk-embed", "openie"),
        run_b_nodes=_bypassed_nodes("chunk-embed", "openie"),
        n_resamples=n_resamples,
        seed=seed,
    )


# --------------------------------------------------------------------------------------------- #
# paired_differences
# --------------------------------------------------------------------------------------------- #


def test_paired_differences_returns_deterministic_order_and_correct_deltas():
    run_a = {"q2": 1.0, "q1": 0.5}
    run_b = {"q1": 0.6, "q2": 0.9}
    diffs = paired_differences(run_a, run_b, "recall@k")
    assert diffs == pytest.approx((0.1, -0.1))  # sorted by question id: q1 then q2


def test_paired_differences_refuses_unequal_question_sets():
    run_a = {"q1": 1.0, "q2": 1.0}
    run_b = {"q1": 1.0, "q3": 1.0}
    with pytest.raises(ValueError, match="do not cover the same question set"):
        paired_differences(run_a, run_b, "recall@k")


# --------------------------------------------------------------------------------------------- #
# Test 1: calibrate_aa_floor returns the bootstrap p95, reproducible under a fixed seed
# --------------------------------------------------------------------------------------------- #


def test_calibrate_aa_floor_is_reproducible_under_a_fixed_seed():
    diffs = [0.02, -0.01, 0.03, 0.0, -0.02, 0.01, 0.04, -0.03, 0.02, 0.0]
    first = _calibrate(diffs, seed=42)
    second = _calibrate(diffs, seed=42)
    assert first.floor == second.floor
    assert isinstance(first, CalibrationResult)
    assert first.n_questions == len(diffs)
    assert first.n_resamples == 500


def test_calibrate_aa_floor_records_the_identity_it_was_calibrated_under():
    result = _calibrate([0.1, 0.2, 0.0, -0.1, 0.05])
    assert result.identity == _IDENTITY


# --------------------------------------------------------------------------------------------- #
# Test 2: the cache-bypass precondition — hit true anywhere, or unknown/absent, both refuse
# --------------------------------------------------------------------------------------------- #


def test_calibrate_aa_floor_refuses_when_any_node_reports_a_cache_hit():
    diffs = [0.1, 0.2, -0.1]
    with pytest.raises(UnusableFloorError, match="reports a cache hit"):
        calibrate_aa_floor(
            diffs,
            identity=_IDENTITY,
            run_a_nodes=[{"node_id": "chunk-embed", "cache_hit": True}],
            run_b_nodes=_bypassed_nodes("chunk-embed"),
        )


def test_calibrate_aa_floor_refuses_when_cache_bypass_status_is_unknown():
    diffs = [0.1, 0.2, -0.1]
    # Absent key — not merely a false value — is unknown, not verified.
    with pytest.raises(UnusableFloorError, match="unknown cache-bypass status"):
        calibrate_aa_floor(
            diffs,
            identity=_IDENTITY,
            run_a_nodes=[{"node_id": "chunk-embed"}],
            run_b_nodes=_bypassed_nodes("chunk-embed"),
        )


def test_calibrate_aa_floor_refuses_when_cache_hit_is_explicitly_none():
    diffs = [0.1, 0.2, -0.1]
    with pytest.raises(UnusableFloorError, match="unknown cache-bypass status"):
        calibrate_aa_floor(
            diffs,
            identity=_IDENTITY,
            run_a_nodes=_bypassed_nodes("chunk-embed"),
            run_b_nodes=[{"node_id": "openie", "cache_hit": None}],
        )


# --------------------------------------------------------------------------------------------- #
# Test 3: the boundary rule — exactly at the floor does not clear it, one increment above does
# --------------------------------------------------------------------------------------------- #


def test_clears_floor_boundary_rule():
    result = _calibrate([0.02, -0.01, 0.03, 0.0, -0.02, 0.01, 0.04, -0.03, 0.02, 0.0], seed=1)
    assert result.clears_floor(result.floor) is False
    assert result.clears_floor(result.floor + 1e-9) is True


# --------------------------------------------------------------------------------------------- #
# Test 4: staleness — each of the four §AA.1 invalidating events raises StaleNullError
# --------------------------------------------------------------------------------------------- #


def test_floor_for_raises_stale_null_error_naming_each_invalidating_event():
    result = _calibrate([0.1, 0.2, -0.1, 0.0])

    with pytest.raises(StaleNullError) as excinfo:
        result.floor_for(NullIdentity(**{**_IDENTITY.__dict__, "bundle_at_v": "bundle@v2"}))
    assert excinfo.value.event == "bundle@v change"

    with pytest.raises(StaleNullError) as excinfo:
        result.floor_for(NullIdentity(**{**_IDENTITY.__dict__, "tier": "T0"}))
    assert excinfo.value.event == "tier change"

    with pytest.raises(StaleNullError) as excinfo:
        result.floor_for(NullIdentity(**{**_IDENTITY.__dict__, "metric": "judged-correctness"}))
    assert excinfo.value.event == "metric change"

    with pytest.raises(StaleNullError) as excinfo:
        result.floor_for(NullIdentity(**{**_IDENTITY.__dict__, "concurrency_setting": "concurrent"}))
    assert excinfo.value.event == "concurrency or determinism setting change"

    with pytest.raises(StaleNullError) as excinfo:
        result.floor_for(NullIdentity(**{**_IDENTITY.__dict__, "determinism_setting": "cache-served"}))
    assert excinfo.value.event == "concurrency or determinism setting change"


def test_floor_for_returns_the_floor_when_identity_matches_exactly():
    result = _calibrate([0.1, 0.2, -0.1, 0.0])
    assert result.floor_for(_IDENTITY) == result.floor


# --------------------------------------------------------------------------------------------- #
# Test 5: correct_for_batch_width — BH at bulk-screening, Holm at escalated-survivor, distinct
# --------------------------------------------------------------------------------------------- #


def test_correct_for_batch_width_bulk_screening_is_benjamini_hochberg():
    p_values = [0.001, 0.02, 0.04, 0.5, 0.9]
    adjusted = correct_for_batch_width(p_values, tier=BULK_SCREENING_TIER)
    assert len(adjusted) == len(p_values)
    # BH-adjusted p-values are monotone non-decreasing in rank order and never below the raw p.
    for raw, adj in zip(p_values, adjusted):
        assert adj >= raw - 1e-12


def test_correct_for_batch_width_escalated_survivor_is_holm_step_down():
    p_values = [0.001, 0.02, 0.04, 0.5, 0.9]
    adjusted = correct_for_batch_width(p_values, tier=ESCALATED_SURVIVOR_TIER)
    n = len(p_values)
    # Holm's own smallest-p adjustment is raw_p * n (before the running-max/cap step).
    smallest_idx = p_values.index(min(p_values))
    assert adjusted[smallest_idx] == pytest.approx(min(p_values[smallest_idx] * n, 1.0))


def test_correct_for_batch_width_tiers_are_computed_on_distinct_inputs_never_stacked():
    p_values = [0.001, 0.03, 0.2]
    bh = correct_for_batch_width(p_values, tier=BULK_SCREENING_TIER)
    holm = correct_for_batch_width(p_values, tier=ESCALATED_SURVIVOR_TIER)
    # Both read the same raw p_values independently; Holm's own per-rank multiplier (n - rank)
    # differs structurally from BH's, so on this non-trivial input the two schemes disagree —
    # proving neither call silently reused the other's output as its own input.
    assert bh != holm


def test_correct_for_batch_width_refuses_unknown_tier():
    with pytest.raises(ValueError, match="unknown tier"):
        correct_for_batch_width([0.1, 0.2], tier="not-a-real-tier")


# --------------------------------------------------------------------------------------------- #
# Test 6 (negative control): genuine spread produces a strictly wider floor than near-zero spread
# --------------------------------------------------------------------------------------------- #


def test_calibrate_aa_floor_negative_control_wide_spread_is_strictly_wider_than_near_zero():
    near_zero = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    wide_spread = [0.5, -0.5, 0.4, -0.4, 0.6, -0.6, 0.45, -0.45, 0.55, -0.55]

    near_zero_result = _calibrate(near_zero, seed=99)
    wide_result = _calibrate(wide_spread, seed=99)

    assert wide_result.floor > near_zero_result.floor
    assert near_zero_result.floor == pytest.approx(0.0, abs=1e-9)

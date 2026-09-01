"""Tests for ``databasise/parity/run_comparison.py``'s keyword-variance band (03-07-PLAN.md Task 3).

**Entirely deterministic** — every case here runs against hand-built ``KeywordsResult`` values, no
``v1/`` venv, no imported index, no network, and carries no skip marker (Task 3's own acceptance
criterion: this module reports zero skipped tests in its deterministic group, because it has no
other group — the band computation itself is pure arithmetic over already-recorded keyword
outputs, never a live call).
"""

from __future__ import annotations

import pytest
from databasise.parity.run_comparison import (
    KeywordsResult,
    SingleRunBandError,
    compute_keyword_variance_band,
)


def test_band_reports_correct_per_keyword_frequency_across_runs():
    runs = [
        KeywordsResult(("retrieval", "graph"), ("Ed Wood",), False),
        KeywordsResult(("retrieval",), ("Ed Wood", "films"), False),
        KeywordsResult(("retrieval", "graph"), ("films",), False),
    ]

    band = compute_keyword_variance_band(runs)

    assert band.run_count == 3
    assert band.high_level_frequency == {"retrieval": 3, "graph": 2}
    assert band.low_level_frequency == {"Ed Wood": 2, "films": 2}


def test_band_reports_correct_mean_and_spread_of_list_sizes():
    runs = [
        KeywordsResult(("a", "b"), ("x",), False),
        KeywordsResult(("a",), ("x", "y"), False),
        KeywordsResult(("a", "b", "c"), (), False),
    ]

    band = compute_keyword_variance_band(runs)

    # high-level sizes: [2, 1, 3] -> mean 2.0
    assert band.high_level_size_mean == pytest.approx(2.0)
    assert band.high_level_size_stdev == pytest.approx(1.0)
    # low-level sizes: [1, 2, 0] -> mean 1.0
    assert band.low_level_size_mean == pytest.approx(1.0)
    assert band.low_level_size_stdev == pytest.approx(1.0)


def test_band_refuses_to_report_when_the_run_count_is_one():
    """PITFALLS 2 / criterion 2's whole reason: a band over one run is not a band."""
    with pytest.raises(SingleRunBandError):
        compute_keyword_variance_band([KeywordsResult(("a",), ("b",), False)])


def test_band_refuses_to_report_when_the_run_count_is_zero():
    with pytest.raises(SingleRunBandError):
        compute_keyword_variance_band([])


def test_a_band_computed_over_cache_served_runs_is_reported_as_cache_served():
    runs = [
        KeywordsResult(("a",), ("b",), True),
        KeywordsResult(("a",), ("b",), False),
    ]

    band = compute_keyword_variance_band(runs)

    assert band.any_cache_served is True


def test_a_band_with_no_cache_served_runs_is_reported_as_clean():
    runs = [
        KeywordsResult(("a",), ("b",), False),
        KeywordsResult(("a",), ("b",), False),
    ]

    band = compute_keyword_variance_band(runs)

    assert band.any_cache_served is False


def test_band_run_count_travels_with_every_serialised_figure():
    """A band figure without its run count cannot be read (this module's own prohibition) —
    proven here by asserting ``run_count`` survives ``to_dict()`` serialisation alongside every
    other figure.
    """
    band = compute_keyword_variance_band(
        [KeywordsResult(("a",), ("b",), False), KeywordsResult(("a",), ("b",), False)]
    )

    payload = band.to_dict()

    assert payload["run_count"] == 2
    assert "high_level_size_mean" in payload
    assert "low_level_size_mean" in payload

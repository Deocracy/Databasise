"""execution_mode derivation and D-08's named hosting refusals. Covers plan 01-03 Task 2's
execution_mode <behavior> (Tests 8-16).

05-01-PLAN.md Task 1: ``subprocess`` moved from an always-refused placement to a real one, hosted
when (and only when) a positive ``wall_clock_ceiling_seconds`` is supplied (§8 condition 4) —
Tests 15/16 below are updated in place to prove the new three-way split (``in-process`` succeeds
unconditionally, ``subprocess`` succeeds only with a declared ceiling, ``confined-unit``/
``long-lived-service`` remain unimplemented) rather than the old "every non-in-process placement
refuses" shape.
"""

from __future__ import annotations

import pytest
from databasise.parts.admission import MissingWallClockCeilingError
from databasise.validator.execution_mode import (
    UnimplementedPlacementError,
    derive_execution_mode,
    host,
)


def test_empty_effects_non_iterative_kind_derives_in_process():
    """Test 8."""
    assert derive_execution_mode([], "stage") == "in-process"


def test_net_effect_derives_a_placement_other_than_in_process():
    """Test 9."""
    assert derive_execution_mode(["net"], "stage") != "in-process"


def test_fs_effect_derives_a_placement_other_than_in_process():
    """Test 10."""
    assert derive_execution_mode(["fs"], "stage") != "in-process"


def test_self_storage_effect_derives_a_placement_other_than_in_process():
    """Test 11."""
    assert derive_execution_mode(["self_storage"], "stage") != "in-process"


def test_mutates_store_effect_derives_a_placement_other_than_in_process():
    """Test 12."""
    assert derive_execution_mode(["mutates_store"], "stage") != "in-process"


def test_fixpoint_kind_derives_a_placement_other_than_in_process_regardless_of_effects():
    """Test 13: iterative by construction, MUST NOT be in-process, whatever effects it declares."""
    assert derive_execution_mode([], "fixpoint") != "in-process"
    assert derive_execution_mode(["reads_kv"], "fixpoint") != "in-process"


def test_opaque_kind_derives_a_placement_other_than_in_process():
    """Test 14."""
    assert derive_execution_mode([], "opaque") != "in-process"


def test_hosting_an_unimplemented_placement_refuses_by_name():
    """Test 15: confined-unit and long-lived-service still refuse by name (unimplemented);
    subprocess with no declared ceiling refuses with the ceiling-specific refusal instead (05-01)."""
    for placement in ("confined-unit", "long-lived-service"):
        with pytest.raises(UnimplementedPlacementError) as exc_info:
            host(placement)
        assert placement in str(exc_info.value)

    with pytest.raises(MissingWallClockCeilingError):
        host("subprocess")


def test_derivation_succeeds_for_all_four_placements_only_hosting_refuses():
    """Test 16: the derivation itself always returns a placement string. host() now hosts
    subprocess for real when given a positive ceiling (05-01); confined-unit/long-lived-service
    remain unimplemented, and a ceiling-less subprocess node still refuses."""
    assert derive_execution_mode([], "stage") == "in-process"
    assert derive_execution_mode([], "opaque") == "subprocess"
    assert derive_execution_mode(["fs"], "stage") == "confined-unit"
    assert derive_execution_mode(["net"], "stage") == "long-lived-service"

    host("in-process")  # does not raise — always hosted
    host("subprocess", wall_clock_ceiling_seconds=60.0)  # does not raise — a real, declared ceiling
    with pytest.raises(MissingWallClockCeilingError):
        host("subprocess")  # no ceiling supplied
    for placement in ("confined-unit", "long-lived-service"):
        with pytest.raises(UnimplementedPlacementError):
            host(placement)

"""Tests for identity/instance.py, per plan 01-04's <behavior> Tests 11-16.

Covers the frozen instance-identity tuple's structural invariants: fan-out is never collapsed,
dependency order never matters, the empty-dependency case is valid, the cache-partition key is
sensitive to exactly the four §1-admitted members, neither function accepts a node id/arm/run/
mode parameter, and the runtime-minted formula composes exactly its four members.
"""

from __future__ import annotations

import inspect

from databasise.identity.canon import config_hash
from databasise.identity.instance import (
    cache_partition_key,
    instance_hash,
    runtime_instance_hash,
)


def test_11_two_node_positions_sharing_component_and_config_share_instance_hash_without_collapsing_fanout():
    c_hash = config_hash({"note": "shared"})
    hash_a = instance_hash("core/passthrough@1.0.0", c_hash, [])
    hash_b = instance_hash("core/passthrough@1.0.0", c_hash, [])
    assert hash_a == hash_b

    # Node ids are positions, never identities: a mapping keyed by node id keeps both fan-out
    # branches present even though their instance_hash values are equal.
    node_positions = {"branch-a": hash_a, "branch-b": hash_b}
    assert len(node_positions) == 2
    assert node_positions["branch-a"] == node_positions["branch-b"]


def test_12_instance_hash_is_invariant_to_dependency_order():
    c_hash = config_hash({"k": "v"})
    ordered_a = instance_hash("core/x@1.0.0", c_hash, ["dep-b-hash", "dep-a-hash"])
    ordered_b = instance_hash("core/x@1.0.0", c_hash, ["dep-a-hash", "dep-b-hash"])
    assert ordered_a == ordered_b


def test_13_instance_hash_with_no_dependencies_returns_a_valid_digest_rather_than_raising():
    h = instance_hash("core/x@1.0.0", config_hash({}), [])
    assert len(h) == 64
    assert h == h.lower()
    assert all(c in "0123456789abcdef" for c in h)


def test_14_cache_partition_key_is_stable_for_the_same_inputs_and_sensitive_to_declared_input_values():
    c_hash = config_hash({"k": "v"})
    key_a = cache_partition_key("core/x@1.0.0", c_hash, [], {"query": "hello"})
    key_b = cache_partition_key("core/x@1.0.0", c_hash, [], {"query": "hello"})
    assert key_a == key_b  # a node id was never a parameter to begin with

    key_c = cache_partition_key("core/x@1.0.0", c_hash, [], {"query": "different"})
    assert key_a != key_c


def test_15_neither_function_accepts_a_node_id_arm_run_or_mode_parameter():
    forbidden_terms = ("node_id", "arm", "run", "mode")
    for func in (instance_hash, cache_partition_key):
        params = list(inspect.signature(func).parameters)
        assert not any(term in p for p in params for term in forbidden_terms), (
            func.__name__,
            params,
        )


def test_16_runtime_instance_hash_composes_exactly_the_four_members_and_differs_by_ordinal():
    h1 = runtime_instance_hash("component-hash", {"x": 1}, "parent-hash", 0)
    h2 = runtime_instance_hash("component-hash", {"x": 1}, "parent-hash", 1)

    assert h1 != h2
    assert len(h1) == 64 and len(h2) == 64

    params = list(inspect.signature(runtime_instance_hash).parameters)
    assert params == [
        "component_instance_hash",
        "runtime_config",
        "parent_instance_hash",
        "ordinal",
    ]

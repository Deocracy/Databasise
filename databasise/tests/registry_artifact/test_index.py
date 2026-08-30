"""RED: the artifact registry — CONTRACT §7's field set, three scopes, scope-filtered discovery.

Tests 1-10 are this plan's numbered <behavior> tests. Tests 11-13 cover acceptance-criteria-only
assertions (the transient-effect refusal, the write-path authorization gate, and the discover()
signature check) that are not separately numbered in <behavior> but are required by
<acceptance_criteria>.
"""

from __future__ import annotations

import inspect
import sqlite3

import pytest
from databasise.registry_artifact.index import (
    REGISTER_AUTHORIZATION,
    ArtifactRegistry,
    Pin,
    TransientWriteNotRegistrableError,
    UnauthorizedRegisterCallError,
)


def _kwargs(**overrides):
    base = {
        "_authorization": REGISTER_AUTHORIZATION,
        "effect": "writes_artifact",
        "content_hash": "a" * 64,
        "namespace": "shared-abc123",
        "scope": "shared",
        "sa2_chunker": "chunker@1.0.0",
        "sa2_extraction": "extraction@1.0.0",
        "sa2_embedding": "embedding@1.0.0",
        "corpus_id": "corpus-1",
        "space_id": "space-1",
        "producer_instance_hash": "b" * 64,
        "recipe_hash": "c" * 64,
        "retention_tier": "runnable",
    }
    base.update(overrides)
    return base


def test_1_registering_an_artifact_stores_every_section_7_field_and_reads_it_back(store_root):
    registry = ArtifactRegistry(store_root)
    record = registry.register(**_kwargs())

    assert record.content_hash == "a" * 64
    assert record.namespace == "shared-abc123"
    assert record.scope == "shared"
    assert record.sa2_chunker == "chunker@1.0.0"
    assert record.sa2_extraction == "extraction@1.0.0"
    assert record.sa2_embedding == "embedding@1.0.0"
    assert record.corpus_id == "corpus-1"
    assert record.space_id == "space-1"
    assert record.producer_instance_hash == "b" * 64
    assert record.recipe_hash == "c" * 64
    assert record.retention_tier == "runnable"


def test_2_a_scope_outside_the_three_values_is_refused_by_the_schema_itself(store_root):
    registry = ArtifactRegistry(store_root)
    with pytest.raises(sqlite3.IntegrityError):  # raised by the CHECK constraint
        registry.register(**_kwargs(scope="public", namespace="public-xyz"))


def test_3_discovery_by_an_arbitrary_caller_returns_only_shared_entries(store_root):
    registry = ArtifactRegistry(store_root)
    registry.register(**_kwargs(content_hash="1" * 64, namespace="shared-1", scope="shared"))
    registry.register(
        **_kwargs(
            content_hash="2" * 64,
            namespace="quarantined-1",
            scope="quarantined",
            recipe_hash="d" * 64,
        )
    )
    registry.register(
        **_kwargs(
            content_hash="3" * 64,
            namespace="self-1",
            scope="self_storage",
            recipe_hash="e" * 64,
        )
    )

    results = registry.discover(caller_instance_hash="z" * 64)

    assert {r.scope for r in results} == {"shared"}


def test_4_discovery_with_an_explicit_pin_returns_that_instances_quarantined_entry_only(
    store_root,
):
    registry = ArtifactRegistry(store_root)
    registry.register(
        **_kwargs(
            content_hash="1" * 64,
            namespace="quarantined-1",
            scope="quarantined",
            producer_instance_hash="p1" * 32,
            recipe_hash="d" * 64,
        )
    )
    registry.register(
        **_kwargs(
            content_hash="2" * 64,
            namespace="quarantined-2",
            scope="quarantined",
            producer_instance_hash="p2" * 32,
            recipe_hash="e" * 64,
        )
    )

    pin = Pin(content_hash="1" * 64, namespace="quarantined-1", producer_instance_hash="p1" * 32)
    results = registry.discover(caller_instance_hash="caller" * 8, pins=[pin])

    assert len(results) == 1
    assert results[0].content_hash == "1" * 64
    assert results[0].producer_instance_hash == "p1" * 32


def test_5_discovery_by_the_producing_instance_returns_its_own_self_storage_entry_only(
    store_root,
):
    registry = ArtifactRegistry(store_root)
    registry.register(
        **_kwargs(
            content_hash="1" * 64,
            namespace="self-1",
            scope="self_storage",
            producer_instance_hash="inst1" * 12,
            recipe_hash="d" * 64,
        )
    )

    own = registry.discover(caller_instance_hash="inst1" * 12)
    other = registry.discover(caller_instance_hash="inst2" * 12)

    assert len(own) == 1
    assert other == []


def test_6_every_discovery_result_carries_scope_stamps_space_id_instance_tier_and_pin_flag(
    store_root,
):
    registry = ArtifactRegistry(store_root)
    registry.register(**_kwargs(content_hash="1" * 64, namespace="shared-1", scope="shared"))

    [result] = registry.discover(caller_instance_hash="anyone" * 8)

    assert result.scope == "shared"
    assert result.sa2_chunker == "chunker@1.0.0"
    assert result.sa2_extraction == "extraction@1.0.0"
    assert result.sa2_embedding == "embedding@1.0.0"
    assert result.space_id == "space-1"
    assert result.producer_instance_hash == "b" * 64
    assert result.retention_tier == "runnable"
    assert result.pin_required is False


def test_7_hash_identical_recipes_resolve_to_one_shared_row(store_root):
    registry = ArtifactRegistry(store_root)
    same_kwargs = _kwargs(content_hash="1" * 64, namespace="shared-1", scope="shared", recipe_hash="s" * 64)

    first = registry.register(**same_kwargs)
    second = registry.register(**same_kwargs)

    assert first.id == second.id

    other = registry.register(
        **_kwargs(
            content_hash="2" * 64, namespace="shared-2", scope="shared", recipe_hash="t" * 64
        )
    )
    assert other.id != first.id


def test_8_same_content_hash_under_two_namespaces_produces_two_rows(store_root):
    registry = ArtifactRegistry(store_root)
    dup_content = "9" * 64

    first = registry.register(
        **_kwargs(content_hash=dup_content, namespace="shared-1", scope="shared", recipe_hash="u" * 64)
    )
    second = registry.register(
        **_kwargs(content_hash=dup_content, namespace="shared-2", scope="shared", recipe_hash="v" * 64)
    )

    assert first.id != second.id
    assert first.content_hash == second.content_hash == dup_content


def test_9_delete_removes_the_row_and_leaves_no_trace(store_root):
    registry = ArtifactRegistry(store_root)
    registry.register(**_kwargs(content_hash="1" * 64, namespace="shared-1", scope="shared"))

    registry.delete("1" * 64, "shared-1")

    assert registry.discover(caller_instance_hash="anyone" * 8) == []


def test_10_space_id_none_is_valid_and_queryable_and_distinguishes_corpora(store_root):
    registry = ArtifactRegistry(store_root)
    registry.register(
        **_kwargs(
            content_hash="1" * 64,
            namespace="shared-1",
            scope="shared",
            space_id=None,
            corpus_id="corpus-a",
            recipe_hash="w" * 64,
        )
    )
    registry.register(
        **_kwargs(
            content_hash="2" * 64,
            namespace="shared-2",
            scope="shared",
            space_id=None,
            corpus_id="corpus-b",
            recipe_hash="x" * 64,
        )
    )

    all_results = registry.discover(caller_instance_hash="anyone" * 8)
    assert len(all_results) == 2
    assert {r.space_id for r in all_results} == {None}

    only_a = registry.discover(caller_instance_hash="anyone" * 8, corpus_id="corpus-a")
    assert len(only_a) == 1
    assert only_a[0].corpus_id == "corpus-a"


def test_11_registering_a_transient_store_effect_is_refused_naming_section_7(store_root):
    registry = ArtifactRegistry(store_root)
    with pytest.raises(TransientWriteNotRegistrableError, match="§7"):
        registry.register(**_kwargs(effect="writes_kv"))


def test_12_a_direct_register_call_without_authorization_is_refused(store_root):
    registry = ArtifactRegistry(store_root)
    kwargs = _kwargs()
    kwargs.pop("_authorization")
    with pytest.raises(UnauthorizedRegisterCallError):
        registry.register(**kwargs)


def test_13_discover_has_no_parameter_that_disables_the_scope_filter():
    names = set(inspect.signature(ArtifactRegistry.discover).parameters)
    assert not any(
        keyword in name.lower() for name in names for keyword in ("disable", "skip", "bypass", "unfiltered")
    )

"""RED: D-02's second blast-radius enforcement site — the artifact-write path itself."""

from __future__ import annotations

import pytest

from databasise.registry_artifact.index import ArtifactRegistry, UnauthorizedRegisterCallError
from databasise.registry_artifact.write_path import BlastRadiusRefusal, write_artifact
from databasise.stores.blob import FilesystemBlobStore
from databasise.validator.blast_radius import blast_radius_violations
from databasise.validator.errors import CODE_BLAST_RADIUS_REFUSAL


def _stores(store_root):
    blob_store = FilesystemBlobStore(namespace="blobs", workspace="tracer", store_root=store_root)
    registry = ArtifactRegistry(store_root)
    return blob_store, registry


def _kwargs(**overrides):
    base = {
        "content": b"hello world",
        "scope": "shared",
        "effective_depth": "stage",
        "namespace": "shared-abc",
        "sa2_chunker": "chunker@1.0.0",
        "sa2_extraction": "extraction@1.0.0",
        "sa2_embedding": "embedding@1.0.0",
        "corpus_id": "corpus-1",
        "space_id": None,
        "producer_instance_hash": "p" * 64,
        "recipe_hash": "r" * 64,
    }
    base.update(overrides)
    return base


def _blob_file_count(blob_store: FilesystemBlobStore) -> int:
    return sum(1 for f in blob_store._blobs_root.rglob("*") if f.is_file())


def test_1_shared_write_at_stage_depth_succeeds_and_produces_a_blob_and_a_registry_row(
    store_root,
):
    blob_store, registry = _stores(store_root)

    record = write_artifact(**_kwargs(), blob_store=blob_store, registry=registry)

    assert blob_store.get(record.content_hash) == b"hello world"
    results = registry.discover(caller_instance_hash="p" * 64)
    assert len(results) == 1
    assert results[0].content_hash == record.content_hash


def test_2_shared_write_at_opaque_depth_is_refused_with_no_blob_or_row(store_root):
    blob_store, registry = _stores(store_root)

    with pytest.raises(BlastRadiusRefusal):
        write_artifact(
            **_kwargs(effective_depth="opaque"), blob_store=blob_store, registry=registry
        )

    assert _blob_file_count(blob_store) == 0
    assert registry.discover(caller_instance_hash="p" * 64) == []


def test_3_shared_write_at_evidence_depth_is_refused(store_root):
    blob_store, registry = _stores(store_root)

    with pytest.raises(BlastRadiusRefusal):
        write_artifact(
            **_kwargs(effective_depth="evidence"), blob_store=blob_store, registry=registry
        )

    assert _blob_file_count(blob_store) == 0
    assert registry.discover(caller_instance_hash="p" * 64) == []


def test_4_quarantined_write_from_an_opaque_depth_node_succeeds(store_root):
    blob_store, registry = _stores(store_root)

    record = write_artifact(
        **_kwargs(scope="quarantined", effective_depth="opaque", namespace="quarantined-abc"),
        blob_store=blob_store,
        registry=registry,
    )

    assert blob_store.get(record.content_hash) == b"hello world"


def test_5_self_storage_write_from_an_opaque_depth_node_succeeds(store_root):
    blob_store, registry = _stores(store_root)

    record = write_artifact(
        **_kwargs(scope="self_storage", effective_depth="opaque", namespace="self-abc"),
        blob_store=blob_store,
        registry=registry,
    )

    assert blob_store.get(record.content_hash) == b"hello world"


def test_6_a_direct_register_call_from_outside_write_path_is_refused(store_root):
    _, registry = _stores(store_root)

    with pytest.raises(UnauthorizedRegisterCallError):
        registry.register(
            effect="writes_artifact",
            content_hash="x" * 64,
            namespace="shared-x",
            scope="shared",
            sa2_chunker="c",
            sa2_extraction="e",
            sa2_embedding="m",
            corpus_id="corpus",
            space_id=None,
            producer_instance_hash="p" * 64,
            recipe_hash="r" * 64,
            retention_tier="runnable",
        )


def test_7_a_write_with_missing_effective_depth_at_shared_scope_is_refused_not_defaulted(
    store_root,
):
    blob_store, registry = _stores(store_root)

    with pytest.raises(BlastRadiusRefusal):
        write_artifact(**_kwargs(effective_depth=None), blob_store=blob_store, registry=registry)

    assert _blob_file_count(blob_store) == 0
    assert registry.discover(caller_instance_hash="p" * 64) == []


def test_8_load_time_and_write_path_refusals_carry_the_same_violation_code(store_root):
    blob_store, registry = _stores(store_root)

    with pytest.raises(BlastRadiusRefusal) as excinfo:
        write_artifact(
            **_kwargs(effective_depth="opaque"), blob_store=blob_store, registry=registry
        )
    write_path_code = excinfo.value.violation.code

    from databasise.parts.schema import Part, WiringNode
    from databasise.validator.parse import ParsedWiring

    parsed = ParsedWiring(
        nodes={
            "n": WiringNode(
                component="x@1.0.0", kind="stage", effects=["writes_artifact"], deps=[]
            )
        },
        parts={
            "n": Part(
                name_at_version="x@1.0.0",
                kind="stage",
                structural_depth="opaque",
                effects=["writes_artifact"],
                upstream_ref=None,
                artifact_scope="shared",
            )
        },
        deps={"n": ()},
        node_order=("n",),
    )
    load_time_violations = blast_radius_violations(parsed, {"n": "opaque"})

    assert load_time_violations[0].code == write_path_code == CODE_BLAST_RADIUS_REFUSAL

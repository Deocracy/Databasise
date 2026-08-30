"""Tests for databasise/namespaces.py: RIG §RUN.1 namespace derivation and the
one-directory-per-namespace layout (D-07). One test per <behavior> claim in 01-05-PLAN.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from databasise.namespaces import (
    artifacts_overlap,
    derive_namespace,
    gc_namespace,
    namespace_dir,
)

_BASE_KWARGS = {
    "sa1_instance_hash": "a" * 64,
    "sa2_chunker": "chunker@1.0.0",
    "sa2_extraction": "extraction@1.0.0",
    "sa2_embedding": "embedding@1.0.0",
    "corpus_id": "corpus-1",
    "space_id": "space-1",
    "scope": "shared",
}


def test_1_hash_identical_recipes_derive_the_same_namespace():
    assert derive_namespace(**_BASE_KWARGS) == derive_namespace(**_BASE_KWARGS)


def test_2_any_single_differing_recipe_field_derives_a_different_namespace():
    baseline = derive_namespace(**_BASE_KWARGS)
    for field in (
        "sa1_instance_hash",
        "sa2_chunker",
        "sa2_extraction",
        "sa2_embedding",
        "corpus_id",
        "space_id",
        "scope",
    ):
        varied = dict(_BASE_KWARGS)
        varied[field] = str(varied[field]) + "x"
        assert derive_namespace(**varied) != baseline, f"field {field} did not change namespace"


def test_3_changing_only_the_sa2_embedding_stamp_changes_the_namespace():
    baseline = derive_namespace(**_BASE_KWARGS)
    varied = dict(_BASE_KWARGS, sa2_embedding="embedding@2.0.0")
    assert derive_namespace(**varied) != baseline


def test_4_corpus_and_space_id_each_change_the_namespace_and_none_space_id_is_valid():
    baseline = derive_namespace(**_BASE_KWARGS)

    assert derive_namespace(**dict(_BASE_KWARGS, corpus_id="corpus-2")) != baseline
    assert derive_namespace(**dict(_BASE_KWARGS, space_id="space-2")) != baseline

    none_space = dict(_BASE_KWARGS, space_id=None)
    ns_none = derive_namespace(**none_space)
    assert ns_none  # a real, stable value — not an error
    assert derive_namespace(**none_space) == ns_none


def test_5_shared_and_quarantined_scopes_from_identical_inputs_differ(tmp_path: Path):
    ns_shared = derive_namespace(**dict(_BASE_KWARGS, scope="shared"))
    ns_quarantined = derive_namespace(**dict(_BASE_KWARGS, scope="quarantined"))

    assert ns_shared != ns_quarantined
    assert namespace_dir(tmp_path, ns_shared) != namespace_dir(tmp_path, ns_quarantined)


def test_6_namespace_dir_stays_inside_store_root_and_refuses_escape_attempts(tmp_path: Path):
    ns = derive_namespace(**_BASE_KWARGS)
    result = namespace_dir(tmp_path, ns)
    assert result.parent == tmp_path

    for bad_namespace in ("../escape", "a/b", "..", "a/../b"):
        with pytest.raises(ValueError):
            namespace_dir(tmp_path, bad_namespace)


def test_7_two_namespaces_under_one_store_root_are_ls_inspectable_and_distinguishable(
    tmp_path: Path,
):
    ns1 = derive_namespace(**dict(_BASE_KWARGS, corpus_id="corpus-a"))
    ns2 = derive_namespace(**dict(_BASE_KWARGS, corpus_id="corpus-b"))

    namespace_dir(tmp_path, ns1).mkdir()
    namespace_dir(tmp_path, ns2).mkdir()

    entries = sorted(p.name for p in tmp_path.iterdir())
    assert entries == sorted([ns1, ns2])
    assert entries[0] != entries[1]


def test_8_gc_namespace_removes_exactly_that_namespace_dir_and_leaves_siblings_intact(
    tmp_path: Path,
):
    ns1 = derive_namespace(**dict(_BASE_KWARGS, corpus_id="corpus-a"))
    ns2 = derive_namespace(**dict(_BASE_KWARGS, corpus_id="corpus-b"))

    dir1 = namespace_dir(tmp_path, ns1)
    dir2 = namespace_dir(tmp_path, ns2)
    dir1.mkdir()
    (dir1 / "some_file").write_text("data")
    dir2.mkdir()
    (dir2 / "some_file").write_text("data")

    gc_namespace(tmp_path, ns1)

    assert not dir1.exists()
    assert dir2.exists()
    assert (dir2 / "some_file").exists()


def test_artifacts_overlap_is_exact_hash_equality_only():
    """Not one of the 8 numbered <behavior> tests, but exercised directly by the plan's own
    bash acceptance criterion — kept here too so `pytest` alone proves it, not only the CLI check.
    """
    assert artifacts_overlap("ab" * 32, "ab" * 32)
    assert not artifacts_overlap("ab" * 32, "ab" * 31 + "ac")

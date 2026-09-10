"""06-08-PLAN.md Task 2: RIG.md ``## §RUN.1``/``## §RUN.2``'s per-modality isolation properties,
extended from 06-01-PLAN.md's own synthetic proof (``tests/seam/test_store_isolation.py``) to the
real corpus-built indexes.

**Deferred reality (06-08-SUMMARY.md, owner decision `defer-and-record-blocked`).** No real
HippoRAG index has been built against the Phase 3 parity corpus in this environment — Task 1's own
``build_hipporag_index.py`` was written but never invoked (one real invocation requires live
``v1/.env.parity`` credentials and was not authorized during this plan's execution). The tests
below that assert against the real built indexes are guarded by ``_real_hipporag_index_present()``
and skip cleanly on every machine where that build has not run — currently every machine,
including this one — mirroring ``databasise/tests/parity/conftest.py``'s own skip-if-absent
discipline (``v2_parity_store_dir`` etc.) rather than failing collection. The guard check itself
touches only a file's existence — it never constructs a store (which would create an empty
directory as a side effect), so merely collecting this module never mutates the real parity store.

The tests that follow exercise the identical isolation logic
(``preflight``'s directory-disjointness check, ``artifacts_overlap``, the cross-read negative
control) against synthetic, hand-seeded stores instead — no real corpus, no network, no spend —
the sanctioned half of this plan's owner-authorized deviation: testing the harness's own logic
against stubbed/fake data is correct and expected; fabricating evidence of a real run is not.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from databasise.namespaces import artifacts_overlap
from databasise.parity import import_index
from databasise.parity.run_cross_modality import (
    _HIPPORAG_VECTOR_NAMESPACES,
    _LIGHTRAG_VECTOR_NAMESPACES,
    _index_recipe_hash,
    _resolved_store_dirs,
    preflight,
)
from databasise.seam.engine import _build_stores
from databasise.wirings.resolve import load_wiring, resolve_arm

_WORKSPACE = "cross-modality-isolation-test"


def _real_hipporag_index_present() -> bool:
    """A pure path-existence check — never constructs a store, so collecting this module never
    creates a directory under the real parity store root as a side effect."""
    try:
        workspace = import_index._import_workspace()
    except Exception:
        return False
    index_file = Path(import_index.DEFAULT_STORE_ROOT) / workspace / "hipporag-chunks" / "vector.faiss"
    return index_file.exists()


_skip_without_real_index = pytest.mark.skipif(
    not _real_hipporag_index_present(),
    reason=(
        "no real HippoRAG index built at the parity store root — run "
        "databasise.parity.build_hipporag_index first (06-08-PLAN.md Task 1, deferred per "
        "06-08-SUMMARY.md's owner decision `defer-and-record-blocked`)"
    ),
)


# --------------------------------------------------------------------------------------------- #
# Against the real built indexes — currently always skipped (deferred reality, see module docstring)
# --------------------------------------------------------------------------------------------- #


@_skip_without_real_index
def test_no_store_root_directory_is_written_by_both_arms_against_the_real_built_indexes():
    store_root = import_index.DEFAULT_STORE_ROOT
    workspace = import_index._import_workspace()
    result = preflight(store_root=store_root, workspace=workspace)
    assert result.directories_disjoint


@_skip_without_real_index
def test_artifacts_overlap_is_false_against_the_real_built_indexes():
    store_root = import_index.DEFAULT_STORE_ROOT
    workspace = import_index._import_workspace()
    result = preflight(store_root=store_root, workspace=workspace)
    assert result.artifacts_overlap is False


# --------------------------------------------------------------------------------------------- #
# Synthetic-store tests: the harness's own isolation logic — no real corpus, no spend, no network
# --------------------------------------------------------------------------------------------- #


def test_directories_disjoint_check_against_synthetic_seeded_stores(store_root):
    """Every identifier LightRAG's arm retrieves resolves in a LightRAG namespace and in no
    HippoRAG namespace, and the converse — proven at the directory level, mirroring
    ``test_store_isolation.py``'s own regression pin but exercised through this harness's own
    ``_resolved_store_dirs`` helper rather than a hand-written literal comparison."""
    lightrag_resolved = resolve_arm("naive")
    hipporag_resolved = load_wiring("hipporag")

    lightrag_dirs = _resolved_store_dirs(
        store_root, _WORKSPACE, lightrag_resolved, _LIGHTRAG_VECTOR_NAMESPACES
    )
    hipporag_dirs = _resolved_store_dirs(
        store_root, _WORKSPACE, hipporag_resolved, _HIPPORAG_VECTOR_NAMESPACES
    )

    assert not (lightrag_dirs & hipporag_dirs)


def test_artifacts_overlap_is_false_for_the_two_structurally_different_recipes():
    """RIG.md ## §RUN.2's iff rule, exercised against the two real resolved wirings this plan
    compares — two structurally different recipes sharing no resolved input, so zero overlap is
    the expected, observed result."""
    lightrag_hash = _index_recipe_hash(resolve_arm("naive"))
    hipporag_hash = _index_recipe_hash(load_wiring("hipporag"))

    assert lightrag_hash != hipporag_hash
    assert artifacts_overlap(lightrag_hash, hipporag_hash) is False


def test_artifacts_overlap_is_true_for_two_identical_recipe_hashes():
    """Regression pin: artifacts_overlap is a genuine iff, not a function that always returns
    False — proves the False result above is not vacuous."""
    one_hash = _index_recipe_hash(load_wiring("hipporag"))
    assert artifacts_overlap(one_hash, one_hash) is True


async def test_cross_read_negative_control_against_synthetic_seeded_stores(store_root):
    """Mirrors ``test_store_isolation.py``'s own cross-read refusal proof: seeding one modality's
    graph namespace leaves the other's empty, so the isolation assertions above are not passing
    vacuously on two empty stores (this plan's own acceptance criterion)."""
    lightrag_stores = _build_stores(store_root, _WORKSPACE, resolve_arm("naive"))
    hipporag_stores = _build_stores(store_root, _WORKSPACE, load_wiring("hipporag"))

    await hipporag_stores["graph"].upsert_node("entity:seeded-only-in-hipporag", {})
    await hipporag_stores["graph"].index_done_callback()

    assert await hipporag_stores["graph"].get_all_labels() == ["entity:seeded-only-in-hipporag"]
    assert await lightrag_stores["graph"].get_all_labels() == []

    await lightrag_stores["graph"].upsert_node("lightrag-only-node", {})
    await lightrag_stores["graph"].index_done_callback()

    assert await lightrag_stores["graph"].get_all_labels() == ["lightrag-only-node"]
    # The reverse direction: LightRAG's own write did not leak into HippoRAG's namespace either.
    assert await hipporag_stores["graph"].get_all_labels() == ["entity:seeded-only-in-hipporag"]

    for store in (*lightrag_stores.values(), *hipporag_stores.values()):
        await store.finalize()

"""Phase 10 review WR-09: no parity path leaves a graph store (the shared pycozo client) or a kv
connection open, and none opens a raw ``Client`` on a path the registry may hold.

The cross-module sequence the review found (``_resolved_store_dirs``, then import, then verify in one
process) is exercised end to end; the harnesses that build stores before their ``try`` are driven
with a ``_build_stores`` that opens one store and then fails.
"""

from __future__ import annotations

import pytest

from databasise.parity import build_hipporag_index, run_arm, run_comparison, storage_audit
from databasise.parity.import_index import _import_graph, import_v1_index, verify_import
from databasise.parity.run_cross_modality import _resolved_store_dirs
from databasise.parts.registry import default_registry
from databasise.stores.graph import CozoGraphStore, _ClientRegistry
from databasise.stores.kv import SqliteKVStore
from databasise.tests.parity.test_import_verification import _WORKSPACE, synthetic_v1_index  # noqa: F401 - fixture
from databasise.wirings.resolve import load_wiring, resolve_arm

_LIGHTRAG_NAMESPACES = ("chunks", "entities", "relationships")
_HIPPORAG_NAMESPACES = ("hipporag-chunks", "hipporag-entities", "hipporag-facts")


def _held_under(root) -> list[str]:
    """Registry paths still held under ``root`` (the registry is process-wide, so a leak in one
    test must not read as a leak in the next: every test uses its own ``store_root``)."""
    return [key for key in _ClientRegistry._entries if key.startswith(str(root))]


def test_resolved_store_dirs_holds_no_graph_client(store_root):
    for resolved, namespaces in (
        (resolve_arm("naive"), _LIGHTRAG_NAMESPACES),
        (load_wiring("hipporag"), _HIPPORAG_NAMESPACES),
    ):
        _resolved_store_dirs(store_root, "ws", resolved, namespaces)

    assert _held_under(store_root) == []


async def test_resolved_store_dirs_then_import_and_verify_in_one_process(synthetic_v1_index, store_root):  # noqa: F811
    _resolved_store_dirs(store_root, _WORKSPACE, resolve_arm("naive"), _LIGHTRAG_NAMESPACES)

    await import_v1_index(synthetic_v1_index, store_root, workspace=_WORKSPACE)
    result = await verify_import(synthetic_v1_index, store_root, workspace=_WORKSPACE)

    assert result.status == "verified", result.violations
    assert _held_under(store_root) == []


async def test_a_failed_graph_import_still_releases_the_shared_client(synthetic_v1_index, store_root, monkeypatch):  # noqa: F811
    async def _boom(self, *args, **kwargs):
        raise RuntimeError("upsert failed")

    monkeypatch.setattr(CozoGraphStore, "upsert_node", _boom)

    with pytest.raises(RuntimeError, match="upsert failed"):
        await _import_graph(synthetic_v1_index, store_root, _WORKSPACE)

    assert _held_under(store_root) == []


async def test_import_and_verify_finalize_every_kv_store_they_open(synthetic_v1_index, store_root, monkeypatch):  # noqa: F811
    opened, finalized = [], []
    real_init, real_finalize = SqliteKVStore.__init__, SqliteKVStore.finalize

    def _init(self, *args, **kwargs):
        opened.append(self)
        real_init(self, *args, **kwargs)

    async def _finalize(self):
        finalized.append(self)
        await real_finalize(self)

    monkeypatch.setattr(SqliteKVStore, "__init__", _init)
    monkeypatch.setattr(SqliteKVStore, "finalize", _finalize)

    await import_v1_index(synthetic_v1_index, store_root, workspace=_WORKSPACE)
    await verify_import(synthetic_v1_index, store_root, workspace=_WORKSPACE)

    assert opened and len(opened) == len({id(s) for s in finalized})
    assert {id(s) for s in opened} == {id(s) for s in finalized}


class _SpyStore:
    def __init__(self) -> None:
        self.finalized = 0

    async def finalize(self) -> None:
        self.finalized += 1


def _build_that_opens_one_store_then_fails(spy: _SpyStore):
    def _build(*args, into=None, **kwargs):
        stores = into if into is not None else {}
        stores["kv"] = spy
        raise RuntimeError("graph open failed")

    return _build


async def test_build_index_finalizes_a_store_opened_before_a_failed_open(store_root, monkeypatch):
    spy = _SpyStore()
    monkeypatch.setattr(build_hipporag_index, "_build_stores", _build_that_opens_one_store_then_fails(spy))

    with pytest.raises(RuntimeError, match="graph open failed"):
        await build_hipporag_index.build_index(store_root=store_root, workspace="ws", clients={})

    assert spy.finalized == 1


async def test_run_decomposed_arm_finalizes_a_store_opened_before_a_failed_open(store_root, monkeypatch):
    spy = _SpyStore()
    monkeypatch.setattr(run_comparison, "_build_stores", _build_that_opens_one_store_then_fails(spy))

    with pytest.raises(RuntimeError, match="graph open failed"):
        await run_comparison._run_decomposed_arm(
            "naive",
            "q",
            pinned_hl_keywords=[],
            pinned_ll_keywords=[],
            registry=default_registry(),
            store_root=store_root,
            workspace="ws",
            clients={},
        )

    assert spy.finalized == 1


async def test_run_audit_finalizes_a_store_opened_before_a_failed_open(store_root, monkeypatch):
    spy = _SpyStore()
    monkeypatch.setattr(run_arm, "_build_stores", _build_that_opens_one_store_then_fails(spy))

    with pytest.raises(RuntimeError, match="graph open failed"):
        await storage_audit.run_audit("naive", store_root=store_root, workspace="ws", clients={})

    assert spy.finalized == 1

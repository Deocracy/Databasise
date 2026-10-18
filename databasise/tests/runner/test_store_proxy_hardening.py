"""Phase 10 review WR-02: the capability proxy exposes no private state. ``_target``, ``_mode`` and
any underscore attribute of the wrapped store are refused, attribute assignment is refused, and
``unwrap_store_handle`` is the one (tests and engine only) way back to the raw store."""

from __future__ import annotations

import pytest

from databasise.parts_core import CapabilityScopedStores, UndeclaredEffectError, unwrap_store_handle
from databasise.stores.kv import SqliteKVStore


@pytest.fixture
async def kv(store_root):
    store = SqliteKVStore(namespace="ns", workspace="ws", store_root=store_root)
    yield store
    await store.finalize()


@pytest.mark.parametrize("effect", ["reads_kv", "writes_kv"])
@pytest.mark.parametrize("name", ["_target", "_mode", "_kind", "_declared", "_conn", "_pending_upserts"])
def test_underscore_attributes_are_not_exposed_on_either_mode(kv, effect, name):
    handle = CapabilityScopedStores({"kv": kv}, [effect]).require(effect)

    with pytest.raises(UndeclaredEffectError):
        getattr(handle, name)


def test_attribute_assignment_and_deletion_are_refused(kv):
    handle = CapabilityScopedStores({"kv": kv}, ["reads_kv"]).require("reads_kv")

    with pytest.raises(UndeclaredEffectError):
        handle._mode = "w"
    with pytest.raises(UndeclaredEffectError):
        handle.anything = 1
    with pytest.raises(UndeclaredEffectError):
        del handle._mode
    with pytest.raises(UndeclaredEffectError, match="writes_kv"):
        handle.upsert


def test_unwrap_store_handle_returns_the_raw_store(kv):
    handle = CapabilityScopedStores({"kv": kv}, ["reads_kv"]).require("reads_kv")

    assert unwrap_store_handle(handle) is kv


def test_a_selected_child_is_hardened_too(store_root):
    from databasise.stores.vector import MultiNamespaceVectorStore

    vector = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)
    child = CapabilityScopedStores({"vector": vector}, ["reads_vector"]).require("reads_vector").select("chunks")

    with pytest.raises(UndeclaredEffectError):
        child._target
    assert unwrap_store_handle(child) is vector.select("chunks")

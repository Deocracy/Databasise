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


@pytest.mark.parametrize("effect", ["reads_kv", "writes_kv"])
@pytest.mark.parametrize("name", ["_no_such_marker", "no_such_method"])
def test_an_attribute_the_target_lacks_is_an_attribute_error(kv, effect, name):
    # Iteration-2 IN-02: hasattr and getattr-with-default must work on a handle.
    handle = CapabilityScopedStores({"kv": kv}, [effect]).require(effect)

    assert not hasattr(handle, name)
    assert getattr(handle, name, "default") == "default"
    with pytest.raises(AttributeError):
        getattr(handle, name)


def test_a_known_but_disallowed_attribute_still_raises_undeclared_effect(kv):
    reader = CapabilityScopedStores({"kv": kv}, ["reads_kv"]).require("reads_kv")
    writer = CapabilityScopedStores({"kv": kv}, ["writes_kv"]).require("writes_kv")

    for handle, name in ((reader, "upsert"), (reader, "_conn"), (writer, "finalize"), (writer, "_target")):
        with pytest.raises(UndeclaredEffectError):
            getattr(handle, name)
        with pytest.raises(UndeclaredEffectError):
            hasattr(handle, name)  # hasattr only swallows AttributeError


def test_every_public_store_method_is_allowlisted_engine_only_or_write_vocabulary():
    # Drift guard for IN-02: a store method outside all three sets would turn a refusal into an
    # AttributeError on a read proxy.
    import inspect

    from databasise import parts_core
    from databasise.stores.graph import CozoGraphStore
    from databasise.stores.vector import FaissVectorStore, MultiNamespaceVectorStore

    known = set(parts_core._ENGINE_ONLY) | set(parts_core._WRITE_VOCABULARY)
    for allowed in parts_core._READ_ALLOWLIST.values():
        known |= allowed
    classes = (SqliteKVStore, CozoGraphStore, FaissVectorStore, MultiNamespaceVectorStore)
    public = {c: {n for n, _ in inspect.getmembers(c, callable) if not n.startswith("_")} for c in classes}
    every_name = set().union(*public.values())
    for cls in classes:  # a name another kind has but this one lacks must still be refused, not missing
        assert every_name - public[cls] <= known, (cls.__name__, sorted(every_name - public[cls] - known))


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

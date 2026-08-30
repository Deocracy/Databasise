"""Cozo 0.7.6 frozen-bug regression suite, ported forward against
``databasise.stores.graph.CozoGraphStore`` (upstream_ref: v1/tests/kg/test_cozo_graph_storage.py).

Cozo 0.7.6 is pinned exactly in ``pyproject.toml`` (D-05) and is architecture-frozen: it ships
four known correctness bugs with no upstream fix expected. The four query-shape constraints these
tests bind are therefore permanent constraints on any query construction in this package, not
workarounds awaiting an upstream fix. Every test in this module runs against the new adapter
directly — not merely against the original v1 class — because 01-RESEARCH.md's Pitfall 2 names
the risk as a *new* adapter reintroducing one of these four query shapes.

No test in this module may carry a pytest skip or xfail marker. These are silent-wrong-result
bugs, not exceptions — a skipped test here would read as green while the defect is live, which is
exactly the failure mode this suite exists to prevent.

Bugs bound here:
    #244       aggregation returning zero rows silently
    #296/#269  UUID sort/coercion
    #253       JSON key-order loss
    #275       wrong DataValue types on round-trip
"""

from __future__ import annotations

import inspect
import re
import sys

from databasise.stores import graph as graph_module
from databasise.stores.graph import CozoGraphStore

# ---------------------------------------------------------------------------
# Bug #244 — aggregation returning zero rows silently
# ---------------------------------------------------------------------------


async def test_bug244_node_degree_and_labels_correct_on_populated_graph(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    await store.upsert_node("A", {"kind": "entity"})
    await store.upsert_node("B", {"kind": "entity"})
    await store.upsert_edge("A", "B", {"weight": "1.0"})
    await store.index_done_callback()

    assert await store.node_degree("A") == 1
    assert await store.get_all_labels() == ["A", "B"]
    await store.finalize()


async def test_bug244_node_degree_and_labels_correct_on_empty_graph(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)

    assert await store.node_degree("Nonexistent") == 0
    assert await store.get_all_labels() == []
    await store.finalize()


def test_bug244_adapter_source_contains_no_count_aggregation():
    """The mitigation: the adapter never uses Cozo's ``count()`` aggregation, which silently
    returns zero rows rather than the correct count on this pinned version (#244)."""
    source = inspect.getsource(graph_module)
    # Strip comments and triple-quoted docstrings (which discuss the bug in prose) so the
    # assertion is about actual query construction — the single/double-quoted CozoScript string
    # literals passed to ``self._client.run`` are left intact and would still be caught.
    no_comments = re.sub(r"#.*", "", source)
    no_docstrings = re.sub(r'("""|\'\'\')(?:(?!\1).)*\1', "", no_comments, flags=re.DOTALL)
    assert "count(" not in no_docstrings


# ---------------------------------------------------------------------------
# Bug #296/#269 — UUID sort and coercion
# ---------------------------------------------------------------------------


async def test_bug296_269_uuid_like_keys_stored_and_returned_as_identical_strings(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    uuid_like_ids = [
        "550e8400-e29b-41d4-a716-446655440000",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "not-a-uuid-at-all",
    ]
    for node_id in uuid_like_ids:
        await store.upsert_node(node_id, {"kind": "entity"})
    await store.index_done_callback()

    labels = await store.get_all_labels()

    # Stored as String (never coerced to a UUID type), sorted correctly, and each id round-trips
    # byte-identical.
    assert labels == sorted(uuid_like_ids)
    for node_id in uuid_like_ids:
        assert await store.has_node(node_id) is True
        node = await store.get_node(node_id)
        assert isinstance(node, dict)
    await store.finalize()


# ---------------------------------------------------------------------------
# Bug #253 — JSON key-order loss
# ---------------------------------------------------------------------------


async def test_bug253_json_attrs_round_trip_regardless_of_key_order(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    # Deliberately non-alphabetical key order.
    attrs = {
        "zebra": "last-alphabetically",
        "apple": "first-alphabetically",
        "middle": "in-between",
        "source_id": "doc1",
    }

    await store.upsert_node("TestNode", attrs)
    await store.index_done_callback()

    retrieved = await store.get_node("TestNode")

    # Compared as a dict — never by serialised key order, which is exactly the property #253
    # destroys.
    assert retrieved == attrs
    for key, value in attrs.items():
        assert retrieved is not None
        assert retrieved[key] == value


# ---------------------------------------------------------------------------
# Bug #275 — wrong DataValue types on round-trip
# ---------------------------------------------------------------------------


async def test_bug275_every_value_type_round_trips_with_correct_python_type(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    attrs = {
        "a_string": "text",
        "an_int": 42,
        "a_float": 3.14,
        "a_bool": True,
        "a_null": None,
        "a_nested_object": {"inner": "value", "count": 2},
        "a_list": [1, 2, "three"],
    }

    await store.upsert_node("Typed", attrs)
    await store.index_done_callback()

    retrieved = await store.get_node("Typed")

    assert retrieved is not None
    assert isinstance(retrieved["a_string"], str) and retrieved["a_string"] == "text"
    assert isinstance(retrieved["an_int"], int) and retrieved["an_int"] == 42
    assert isinstance(retrieved["a_float"], float) and retrieved["a_float"] == 3.14
    assert isinstance(retrieved["a_bool"], bool) and retrieved["a_bool"] is True
    assert retrieved["a_null"] is None
    assert isinstance(retrieved["a_nested_object"], dict)
    assert retrieved["a_nested_object"] == {"inner": "value", "count": 2}
    assert isinstance(retrieved["a_list"], list)
    assert retrieved["a_list"] == [1, 2, "three"]
    await store.finalize()


# ---------------------------------------------------------------------------
# Meta-test — non-skippable
# ---------------------------------------------------------------------------


def test_no_skip_or_xfail_markers_in_this_module():
    source = inspect.getsource(sys.modules[__name__])
    # Built via concatenation so this assertion's own source line does not trip the check it
    # performs on the rest of the module.
    skip_marker = "mark" + "." + "skip"
    xfail_marker = "mark" + "." + "xfail"
    assert skip_marker not in source
    assert xfail_marker not in source

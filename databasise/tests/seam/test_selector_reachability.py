"""13-02 (WIRE-01, D-01): each of the six query candidates is reachable by a production §18.4
capability selector without a promote."""

from __future__ import annotations

import pytest

from databasise.parts.registry import default_registry
from databasise.seam import selectors as selectors_module
from databasise.seam.selectors import Selector, resolve_selector
from databasise.wirings.resolve import all_wirings

_CANDIDATES = [
    ("naive", ["reads_vector"]),
    ("bypass", ["calls_llm"]),
    ("local", ["reads_vector:entities"]),
    ("global", ["reads_vector:relationships"]),
    ("hybrid", ["reads_vector:entities", "reads_vector:relationships"]),
    ("hipporag", ["reads_graph", "reads_kv"]),
]


def _resolve(capability):
    """The resolved dict, or the caught exception (so a failure is an assertion, not an error)."""
    try:
        return resolve_selector(Selector(capability=capability), registry=default_registry())
    except Exception as exc:  # noqa: BLE001 - captured to assert on its type name
        return exc


def _arm(name):
    return dict(all_wirings())[name]


@pytest.mark.parametrize("name,capability", _CANDIDATES, ids=[name for name, _ in _CANDIDATES])
def test_each_candidate_has_a_selector(name, capability):
    result = _resolve(capability)
    assert not isinstance(result, Exception), type(result).__name__
    assert result == _arm(name)


def test_documented_reads_graph_mappings():
    assert _resolve(["reads_graph"]) == _arm("hipporag")
    assert _resolve(["reads_graph", "calls_llm"]) == _arm("hipporag")
    assert _resolve(["reads_graph", "calls_rerank"]) == _arm("local")
    refused = _resolve(["writes_graph"])
    assert isinstance(refused, Exception)
    assert type(refused).__name__ == "UnsatisfiableSelectorError"


def test_namespace_token_order_does_not_matter():
    forward = _resolve(["reads_vector:entities", "reads_vector:relationships"])
    reverse = _resolve(["reads_vector:relationships", "reads_vector:entities"])
    assert reverse == _arm("hybrid")
    assert forward == reverse


def test_an_entity_token_never_selects_global_and_a_relation_token_never_selects_local():
    entity_only = _resolve(["reads_vector:entities"])
    relation_only = _resolve(["reads_vector:relationships"])
    assert not isinstance(entity_only, Exception) and entity_only != _arm("global")
    assert not isinstance(relation_only, Exception) and relation_only != _arm("local")


def test_a_chunks_token_selects_naive():
    assert _resolve(["reads_vector:chunks"]) == _arm("naive")


def test_docstring_states_every_mapping():
    doc = selectors_module.__doc__ or ""
    for needle in (
        "reads_vector:entities",
        "reads_vector:relationships",
        "all_wirings()",
        "naive",
        "bypass",
        "hybrid",
        "local",
        "global",
        "hipporag",
        "one-node margin",
    ):
        assert needle in doc, needle
    assert "sufficient to distinguish" not in doc

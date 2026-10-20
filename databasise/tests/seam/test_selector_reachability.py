"""13-02 (WIRE-01, D-01): each of the six query candidates is reachable by a production §18.4
capability selector without a promote."""

from __future__ import annotations

import pytest

from databasise.parts.registry import default_registry
from databasise.seam.selectors import Selector, resolve_selector
from databasise.wirings.resolve import all_wirings

_CANDIDATES = [
    ("naive", ["reads_vector"]),
    ("bypass", ["calls_llm"]),
    ("local", ["reads_vector:entities"]),
    pytest.param("global", ["reads_vector:relationships"], marks=pytest.mark.xfail(strict=True)),
    pytest.param(
        "hybrid",
        ["reads_vector:entities", "reads_vector:relationships"],
        marks=pytest.mark.xfail(strict=True),
    ),
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


@pytest.mark.parametrize("name,capability", _CANDIDATES, ids=["naive", "bypass", "local", "global", "hybrid", "hipporag"])
def test_each_candidate_has_a_selector(name, capability):
    result = _resolve(capability)
    assert not isinstance(result, Exception), type(result).__name__
    assert result == _arm(name)

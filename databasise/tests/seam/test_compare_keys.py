"""09-08-PLAN.md (SEAM-11, D-09, D-10): ``compare`` checks every comparison key before any arm
runs, resolves each selector once and executes exactly the wiring it resolved. A refused comparison
spends nothing, and the response-shape rule (envelope versus keyed map) is stated where consumers
read it.
"""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("fastapi")

from databasise.seam import engine as engine_module
from databasise.seam.compare import comparison_keys
from databasise.seam.engine import Databasise
from databasise.seam.refusals import DuplicateComparisonKeyError, EmptyComparisonRequestError
from databasise.seam.rest import create_app
from databasise.seam.selectors import Selector
from databasise.tests.seam._probes import counting_clients, promote_alias, trace_row_count
from databasise.tests.seam.conftest import synthetic_naive_store  # noqa: F401 - fixture
from databasise.wirings.resolve import resolve_arm
from fastapi.testclient import TestClient

_QUERY = {"text": "who directed Ed Wood?"}
_PAIRS = [
    ([{}, {}], "default"),
    ([{"alias": "default"}, {}], "default"),
    ([{"alias": "x"}, {"harness": "x"}], "x"),
    ([{"alias": "a+b"}, {"capability": ["a", "b"]}], "a+b"),
]


@pytest.fixture
def compare_setup(synthetic_naive_store):  # noqa: F811
    store = synthetic_naive_store
    clients = counting_clients(store["query_vector"])
    app = create_app(store_root=store["store_root"], workspace=store["workspace"], clients=clients)
    return TestClient(app), clients, store["store_root"]


# ---------------------------------------------------------------------------------------------- #
# The pure pre-check
# ---------------------------------------------------------------------------------------------- #


def test_keys_differing_only_in_case_do_not_collide():
    assert comparison_keys([Selector(alias="X"), Selector(alias="x")]) == ["X", "x"]


def test_the_repeat_is_reported_at_its_second_occurrence_in_caller_order():
    with pytest.raises(DuplicateComparisonKeyError) as exc_info:
        comparison_keys([Selector(), Selector(alias="a"), Selector()])
    assert exc_info.value.key == "default"
    assert comparison_keys([Selector(alias="b"), Selector(alias="a")]) == ["b", "a"]


def test_zero_selectors_are_refused_and_two_defaults_always_collide():
    with pytest.raises(EmptyComparisonRequestError):
        comparison_keys([])
    with pytest.raises(DuplicateComparisonKeyError):
        comparison_keys([Selector(), Selector()])


# ---------------------------------------------------------------------------------------------- #
# REST: every refusal precedes the first arm
# ---------------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(("selectors", "key"), _PAIRS)
async def test_a_colliding_pair_is_refused_before_any_arm_spends_anything(compare_setup, selectors, key):
    client, clients, root = compare_setup
    for alias in ("default", "x", "a+b"):
        await promote_alias(root, alias)
    rows_before = trace_row_count(root)

    response = client.post("/compare", json={"query": _QUERY, "selectors": selectors})

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["refusal_type"] == "DuplicateComparisonKeyError"
    assert repr(key) in str(body)
    assert clients["llm"].calls == 0
    assert clients["embedding"].calls == 0
    assert trace_row_count(root) == rows_before


# ---------------------------------------------------------------------------------------------- #
# Resolve once, in caller order
# ---------------------------------------------------------------------------------------------- #


async def test_a_two_selector_compare_resolves_each_selector_exactly_once(compare_setup, monkeypatch):
    client, _clients, root = compare_setup
    await promote_alias(root, "x")
    real_resolve = engine_module.resolve_selector
    resolve_calls: list[Selector] = []

    def counting_resolve(selector, **kwargs):
        resolve_calls.append(selector)
        return real_resolve(selector, **kwargs)

    monkeypatch.setattr(engine_module, "resolve_selector", counting_resolve)

    response = client.post(
        "/compare",
        json={"query": _QUERY, "selectors": [{"alias": "x"}, {"capability": ["reads_vector"]}]},
    )

    assert response.status_code == 200, response.text
    assert len(resolve_calls) == 2
    assert list(response.json()) == ["x", "reads_vector"]


def test_resolved_execution_never_resolves_a_selector_itself():
    assert "resolve_selector" not in inspect.getsource(Databasise._execute_resolved)

"""09-07-PLAN.md Task 2 (SEAM-12): ``POST /promote`` refuses an alias no ``Selector`` could carry (the
empty alias, or one shaped like an instance hash) before any ledger write, so every alias that can
be promoted is selectable afterwards.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from databasise.ledger.ledger import Ledger
from databasise.seam.engine import Databasise
from databasise.seam.refusals import InvalidPromotionAliasError, UnrecognisedPromotionVerbError
from databasise.seam.rest import create_app
from databasise.seam.selectors import Selector
from databasise.tests.seam._probes import counting_clients
from databasise.tests.seam.conftest import synthetic_naive_store  # noqa: F401 - fixture
from databasise.tests.seam.test_rest_transport import _seed_trace
from fastapi.testclient import TestClient

_HASH_ALIAS = "sha256:" + "b" * 64


def _ledger_rows(store_root) -> int:
    return Ledger(store_root)._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]


def _promote(client, store_root, alias, **overrides):
    body = {"alias": alias, "trace_ids": [_seed_trace(store_root, "naive")], "change_origin": "human_edit"}
    body.update(overrides)
    return client.post("/promote", json=body)


@pytest.fixture
def store(synthetic_naive_store):  # noqa: F811
    clients = counting_clients(synthetic_naive_store["query_vector"])
    app = create_app(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=clients,
    )
    return TestClient(app), synthetic_naive_store["store_root"], synthetic_naive_store, clients


@pytest.mark.parametrize("alias", ["", _HASH_ALIAS, "b" * 64])
def test_an_unselectable_alias_is_refused_and_writes_no_ledger_row(store, alias):
    client, root, _, _ = store
    rows_before = _ledger_rows(root)

    response = _promote(client, root, alias)

    assert response.status_code == 422, response.text
    assert response.json()["refusal_type"] == "InvalidPromotionAliasError"
    assert _ledger_rows(root) == rows_before


def test_a_promotable_alias_is_selectable_afterwards(store):
    client, root, _, clients = store

    assert _promote(client, root, "good-alias").status_code == 200

    response = client.post("/query", json={"query": {"text": "q"}, "selector": {"alias": "good-alias"}})
    assert response.status_code == 200, response.text


def test_the_promote_check_uses_the_exact_pattern_selector_uses(store):
    client, root, _, _ = store
    one_short = "sha256:" + "b" * 63

    assert Selector(alias=one_short).alias == one_short
    assert _promote(client, root, one_short).status_code == 200
    response = client.post("/query", json={"query": {"text": "q"}, "selector": {"alias": one_short}})
    assert response.status_code == 200, response.text


async def test_refusal_order_is_verb_then_alias_then_trace_resolution(tmp_path):
    engine = Databasise(store_root=tmp_path, workspace="alias-order")

    with pytest.raises(UnrecognisedPromotionVerbError):
        await engine.promote("", [_seed_trace(tmp_path, "naive")], "human_edit", verb="nope")
    with pytest.raises(InvalidPromotionAliasError) as exc_info:
        await engine.promote("", ["unknown-trace"], "human_edit")
    assert exc_info.value.alias == ""
    assert _ledger_rows(tmp_path) == 0


async def test_mcp_promote_with_an_empty_alias_is_refused(synthetic_naive_store):  # noqa: F811
    from databasise.mcp import create_server
    from databasise.mcp._sdk import import_sdk

    root = synthetic_naive_store["store_root"]
    server = create_server(store_root=root, workspace=synthetic_naive_store["workspace"])
    tool_error = import_sdk("mcp.server.mcpserver.exceptions").ToolError

    with pytest.raises(tool_error) as exc_info:
        await server.call_tool(
            "promote",
            {"args": {"alias": "", "trace_ids": [_seed_trace(root, "naive")], "change_origin": "human_edit"}},
        )

    text = str(exc_info.value)
    assert json.loads(text[text.index("{") :])["refusal_type"] == "InvalidPromotionAliasError"
    assert _ledger_rows(root) == 0

"""Fuzz F2 follow-up (phase09 N-3 / phase16): once a store holds a ``ledger.db`` (one promotion),
a caller string carrying a lone surrogate (``"\\ud800"``) in ``version`` (rollback, retire) or in
``alias`` (``POST /ledger/history``) reaches sqlite's parameter binding and raises there. Each must
be the named 422 ``NonEncodableTextError`` on REST and the same refusal over MCP, never a 500. The
promotion is seeded with ``test_dual_transport``'s fixed trace helper so the operator verbs pass
their trace-id preconditions and reach the ledger read."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.seam.engine import Databasise
from databasise.seam.rest import create_app
from databasise.tests.seam.test_dual_transport import _mcp_available, _seed_fixed_trace

_JSON = {"content-type": "application/json"}
_ALIAS = "surrogate-after-promotion-alias"


@pytest.fixture
async def promoted_root(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    seed = _seed_fixed_trace(root, "naive", token="fixed-surrogate-seed")
    await Databasise(store_root=root, workspace="surrogate-seed").promote(_ALIAS, [seed], "human_edit")
    _seed_fixed_trace(root, "naive", token="fixed-surrogate-evidence")
    return root


def _operator_body(version: str) -> bytes:
    return (
        '{"alias": "%s", "version": "%s", "trace_ids": ["fixed-surrogate-evidence"], '
        '"change_origin": "human_edit"}' % (_ALIAS, version)
    ).encode("ascii")


def _assert_refused(response, field: str) -> None:
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["refusal_type"] == "NonEncodableTextError", body
    assert body["field"] == field


@pytest.mark.parametrize("route", ["/rollback", "/retire"])
async def test_a_surrogate_version_is_the_named_422_on_rest_after_a_promotion(promoted_root, route):
    client = TestClient(
        create_app(store_root=promoted_root, workspace="surrogate-rest"), raise_server_exceptions=False
    )

    response = client.post(route, content=_operator_body("\\ud800"), headers=_JSON)

    _assert_refused(response, "version")


async def test_a_surrogate_history_alias_is_the_named_422_on_the_operator_route(promoted_root, tmp_path):
    log = tmp_path / "server.log"
    log.write_text("", encoding="utf-8")
    client = TestClient(
        create_app(store_root=promoted_root, workspace="surrogate-op", operator=True, log_path=log),
        raise_server_exceptions=False,
    )

    response = client.post("/ledger/history", content=b'{"alias": "\\ud800"}', headers=_JSON)

    _assert_refused(response, "alias")


@pytest.mark.parametrize("tool", ["rollback", "retire"])
async def test_a_surrogate_version_is_the_named_refusal_over_mcp_after_a_promotion(promoted_root, tool):
    if not _mcp_available():
        pytest.skip("the `mcp` extra is not installed")
    from databasise.mcp import create_server
    from databasise.mcp._sdk import import_sdk

    ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError
    server = create_server(store_root=promoted_root, workspace="surrogate-mcp")
    args = json.loads(_operator_body("\\ud800"))

    with pytest.raises(ToolError) as exc_info:
        await server.call_tool(tool, {"args": args})

    text = str(exc_info.value)
    detail = json.loads(text[text.index("{") :])
    assert detail["refusal_type"] == "NonEncodableTextError"
    assert detail["field"] == "version"

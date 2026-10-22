"""Phase 16 lane A review fixes for the operator routes in ``databasise/seam/operator_rest.py``."""

from __future__ import annotations

from pathlib import Path

import pytest
from databasise.seam.rest import _FAULT_RESPONSES, create_app

# WR-04: only the graph reads raise StoreBusyError, so only they declare 409. The 502/503 machine-fault
# pair stays on every store-reading route, as 16-CONTEXT's OpenAPI decision states.
_FAULTS = {"502", "503"}
_DECLARED = {
    ("get", "/info"): set(),
    ("get", "/wirings"): set(),
    ("get", "/ledger/aliases"): _FAULTS,
    ("post", "/ledger/history"): _FAULTS,
    ("get", "/traces"): _FAULTS,
    ("post", "/promote/preview"): _FAULTS,
    ("post", "/chunks"): _FAULTS,
    ("post", "/graph/nodes"): _FAULTS | {"409"},
    ("post", "/graph/node"): _FAULTS | {"409"},
    ("get", "/log"): _FAULTS,
}


@pytest.mark.parametrize(("method", "path"), sorted(_DECLARED))
def test_operator_openapi_declares_409_on_the_graph_routes_only(tmp_path: Path, method: str, path: str) -> None:
    before = {k: dict(v) for k, v in _FAULT_RESPONSES.items()}
    app = create_app(store_root=tmp_path, workspace="ws", operator=True, log_path=tmp_path / "server.log")
    responses = app.openapi()["paths"][path][method]["responses"]
    assert set(responses) & {"409", "502", "503"} == _DECLARED[(method, path)]
    assert {k: dict(v) for k, v in _FAULT_RESPONSES.items()} == before

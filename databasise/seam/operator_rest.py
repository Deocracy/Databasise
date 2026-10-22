"""The operator read routes (16-01, D-01..D-05): the surface behind the GUI connectors.

Mounted only by ``create_app(operator=True)`` / ``databasise-rest --operator`` (D-01); without the
flag every path here is a 404. These routes are an operator exception to §18.2: wiring names, arms
and aliases appear on this surface and nowhere else (D-02). Every operation is REST-only; none has
an MCP tool (D-03). Every route body is one awaited engine call, which
``databasise/tests/seam/test_console_surface.py`` enforces by AST (D-04), so no route reads the
ledger, trace store, registry or stores itself.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query

from databasise.seam.corpus import checked_page
from databasise.seam.rest import (
    _FAULT_RESPONSES,
    PromoteRequest,
    RefusalBody,
    _RequestModel,
)
from databasise.seam.selectors import Selector

# Store-reading operator routes: the machine faults plus a busy store. A new dict, so the shared
# _FAULT_RESPONSES that the seam routes use is never mutated.
_OPERATOR_STORE_RESPONSES: dict[int | str, dict[str, Any]] = {
    **_FAULT_RESPONSES,
    409: {
        "model": RefusalBody,
        "description": "Store busy: the store is held by another process (StoreBusyError)",
    },
}


class LedgerHistoryRequest(_RequestModel):
    """Body of POST /ledger/history: the alias and the page bounds, checked by ``checked_page``."""

    alias: str
    limit: int = 50
    offset: int = 0


class ChunksRequest(_RequestModel):
    """Body of POST /chunks: which modality (the selector) and the page bounds, checked by
    ``checked_page``."""

    selector: Selector | None = None
    limit: int = 50
    offset: int = 0


class GraphNodesRequest(_RequestModel):
    """Body of POST /graph/nodes: which modality (the selector), an optional id prefix and the page
    bounds, checked by ``checked_page``."""

    selector: Selector | None = None
    prefix: str = ""
    limit: int = 50
    offset: int = 0


def add_operator_routes(app: FastAPI, engine: Any) -> None:
    """Adds the operator routes to ``app``, each a thin adapter over ``engine``. New routes are
    appended at the end of this function, one awaited engine call per route body."""

    @app.get("/info")
    async def get_info() -> dict[str, Any]:
        """Version, workspace and which model clients were configured at startup."""
        return await engine.info()

    @app.get("/wirings")
    async def get_wirings() -> list[dict[str, Any]]:
        """One row per wiring: node count, default arm and selector reachability."""
        return await engine.wirings()

    @app.get("/ledger/aliases", responses=_OPERATOR_STORE_RESPONSES)
    async def get_ledger_aliases() -> list[dict[str, Any]]:
        """One row per alias: its active version, record kind, generation ordinal and time."""
        return await engine.ledger_aliases()

    @app.post("/ledger/history", responses=_OPERATOR_STORE_RESPONSES)
    async def post_ledger_history(body: LedgerHistoryRequest) -> dict[str, Any]:
        """One page of an alias's ledger rows with active and tombstoned flags."""
        return await engine.ledger_history(body.alias, checked_page(body.limit, body.offset))

    @app.get("/traces", responses=_OPERATOR_STORE_RESPONSES)
    async def get_traces(limit: int = Query(default=50), offset: int = Query(default=0)) -> dict[str, Any]:
        """One page of recent traces, newest first: token, time, partial, degraded and stop reason."""
        return await engine.list_traces(checked_page(limit, offset))

    @app.post(
        "/promote/preview",
        responses=_OPERATOR_STORE_RESPONSES,
        description=(
            "A dry run of POST /promote: the arm, mutation class and next version, and whether it is "
            "promotable with a named reason. Writes nothing. It is not the unbuilt ladder verb "
            "'preview'. next_version holds only if no ledger write lands before the promotion."
        ),
    )
    async def post_promote_preview(body: PromoteRequest) -> dict[str, Any]:
        return await engine.preview_promotion(body.alias, body.trace_ids, body.change_origin, verb=body.verb)

    @app.post("/chunks", responses=_OPERATOR_STORE_RESPONSES)
    async def post_chunks(body: ChunksRequest) -> dict[str, Any]:
        """One page of chunk references for the selected modality; each opens via /evidence/resolve."""
        return await engine.chunk_page(body.selector, checked_page(body.limit, body.offset))

    @app.post("/graph/nodes", responses=_OPERATOR_STORE_RESPONSES)
    async def post_graph_nodes(body: GraphNodesRequest) -> dict[str, Any]:
        """One page of graph nodes with degrees for the selected modality, optionally by id prefix."""
        return await engine.graph_nodes(body.selector, body.prefix, checked_page(body.limit, body.offset))

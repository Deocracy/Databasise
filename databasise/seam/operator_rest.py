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

from fastapi import FastAPI

from databasise.seam.rest import _FAULT_RESPONSES, RefusalBody

# Store-reading operator routes: the machine faults plus a busy store. A new dict, so the shared
# _FAULT_RESPONSES that the seam routes use is never mutated.
_OPERATOR_STORE_RESPONSES: dict[int | str, dict[str, Any]] = {
    **_FAULT_RESPONSES,
    409: {
        "model": RefusalBody,
        "description": "Store busy: the store is held by another process (StoreBusyError)",
    },
}


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

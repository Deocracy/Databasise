"""Explicit in-code part registry (D-13): an in-memory dict mapping ``name@version`` to a
``Part``. No dynamic-import fallback and no entry_points discovery — that is exactly the
extensibility D-13 rejects for this milestone: every part in this milestone is authored by this
project, so a plain dict costs nothing an editable install or entry_points-based approach would
have imposed for extensibility nothing needs yet. entry_points can be added later without
changing the Part interface.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part


class UnknownPartError(KeyError):
    """Raised by ``PartRegistry.get`` for a ``name@version`` with no registered Part."""

    def __init__(self, name_at_version: str, known: list[str]):
        self.name_at_version = name_at_version
        self.known = sorted(known)
        super().__init__(
            f"unknown part {name_at_version!r}; registered parts: {self.known}"
        )


async def _passthrough_body(ctx: NodeContext) -> dict[str, Any]:
    """The tracer's zero-effect reference part: relays its inputs verbatim."""
    return {"node_id": ctx.node_id, "inputs": dict(ctx.inputs)}


async def _kv_writer_body(ctx: NodeContext) -> dict[str, Any]:
    """The tracer's writes_kv reference part: writes its own output to the run's KV store."""
    store = ctx.stores["kv"]
    value = {"node_id": ctx.node_id, "inputs": dict(ctx.inputs)}
    await store.upsert({ctx.node_id: value})
    return value


class PartRegistry:
    """In-memory dict mapping ``name@version -> Part`` (D-13). Registers the tracer's two
    reference parts: a passthrough at ``stage`` depth with no declared effects, and a KV-writer
    at ``stage`` depth declaring ``writes_kv``.
    """

    def __init__(self) -> None:
        self._parts: dict[str, Part] = {
            "core/passthrough@1.0.0": Part(
                name_at_version="core/passthrough@1.0.0",
                kind="passthrough",
                structural_depth="stage",
                effects=[],
                upstream_ref=None,
                body=_passthrough_body,
            ),
            "core/kv-writer@1.0.0": Part(
                name_at_version="core/kv-writer@1.0.0",
                kind="kv-writer",
                structural_depth="stage",
                effects=["writes_kv"],
                upstream_ref=None,
                body=_kv_writer_body,
            ),
        }

    def get(self, name_at_version: str) -> Part:
        try:
            return self._parts[name_at_version]
        except KeyError:
            raise UnknownPartError(name_at_version, list(self._parts.keys())) from None

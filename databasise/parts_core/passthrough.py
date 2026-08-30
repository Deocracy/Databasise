"""D-04's zero-effect reference part: the minimal node the scheduler dispatches and the control
every other ``parts_core`` reference part is compared against.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part


async def _passthrough_body(ctx: NodeContext) -> dict[str, Any]:
    """Return the node's own inputs unchanged."""
    return dict(ctx.inputs)


PASSTHROUGH_PART = Part(
    name_at_version="parts-core/passthrough@1.0.0",
    kind="passthrough",
    structural_depth="stage",
    effects=[],
    upstream_ref=None,
    body=_passthrough_body,
)

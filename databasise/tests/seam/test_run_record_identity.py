"""WIRE-12 (D-17): a run that records ``concurrency_setting: sequential`` runs one node body at a
time. This file holds the concurrency leg; later plans add the identity and trace_token legs.
"""

from __future__ import annotations

import asyncio

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.runner import scheduler
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring


async def test_a_sequential_run_never_has_two_node_bodies_in_flight():
    in_flight = {"current": 0, "peak": 0}

    async def body(ctx: NodeContext):
        in_flight["current"] += 1
        in_flight["peak"] = max(in_flight["peak"], in_flight["current"])
        await asyncio.sleep(0.02)
        in_flight["current"] -= 1
        return {}

    part = Part(
        name_at_version="test/counter@1.0.0",
        kind="passthrough",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    nodes = {n: WiringNode(component="test/counter@1.0.0", kind="passthrough", deps=[]) for n in ("one", "two")}
    parsed = ParsedWiring(
        nodes=nodes,
        parts={n: part for n in nodes},
        deps={n: () for n in nodes},
        node_order=("one", "two"),
        report=ValidationReport(),
    )

    result = await scheduler.run_wiring(
        parsed, PartRegistry(), {}, determinism_setting="cache-bypassed", concurrency_setting="sequential"
    )

    assert len(result["nodes"]) == 2
    assert in_flight["peak"] == 1

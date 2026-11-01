"""Phase 09 D-04 (security audit finding N-1): the node fault text the scheduler persists in the
trace must name the exception type but never an absolute path or URL, because the engine returns
the raw record to any caller who sets ``debug=True`` on ``resolve_trace``.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.runner import scheduler
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring

_PATH = "/home/user/secret/index.faiss"
_URL = "https://vectors.internal:8443/v1/index"


def _failing(message: str) -> Part:
    async def body(ctx: NodeContext) -> dict[str, Any]:
        raise OSError(message)

    return Part(
        name_at_version="test/failing@1.0.0",
        kind="stage",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )


async def _fault_text(part: Part) -> str:
    node = WiringNode(component=part.name_at_version, kind=part.kind, effects=[], config=None, deps=[])
    parsed = ParsedWiring(
        nodes={"n1": node}, parts={"n1": part}, deps={"n1": ()}, node_order=("n1",), report=ValidationReport()
    )
    result = await scheduler.run_wiring(
        parsed, PartRegistry(), {}, determinism_setting="cache-bypassed", concurrency_setting="sequential"
    )
    trace = result["nodes"][0]
    assert trace.status == "failed"
    return trace.cross_process_failure_cause


async def test_node_fault_text_keeps_the_type_but_not_the_path():
    cause = await _fault_text(_failing(f"[Errno 2] No such file or directory: '{_PATH}'"))

    assert "OSError" in cause
    assert "/home/" not in cause
    assert "index.faiss" not in cause


async def test_node_fault_text_drops_an_endpoint_url():
    cause = await _fault_text(_failing(f"connection refused: {_URL}"))

    assert "OSError" in cause
    assert "vectors.internal" not in cause
    assert "https://" not in cause

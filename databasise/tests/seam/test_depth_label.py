"""13-05 Task 1 (WIRE-04, D-06): ``ResponseEnvelope.depth_label`` is null when no provides node
returned a completion, the answering node's effective depth otherwise, and typed as the ``Depth``
literal (no free text).

Every test collects and fails by assertion at the phase base: only names that exist there are
imported, and exceptions are captured and asserted on rather than expected with ``pytest.raises``.
"""

from __future__ import annotations

from databasise.runner.trace import NodeTrace, TokenAccounting
from databasise.seam import Databasise, QueryObject, ResponseEnvelope
from databasise.seam.engine import _select_answer
from databasise.tests.seam._probes import counting_clients


def _node_trace(node_id: str, *, effective_depth: str) -> NodeTrace:
    return NodeTrace(
        node_id=node_id,
        instance_hash=f"sha256:fake-{node_id}",
        depth="stage",
        effective_depth=effective_depth,
        wall_clock_ms=0,
        cache_hit=False,
        guards_fired=[],
        budget_state="completed",
        realised_budget_share=0.0,
        cross_process_failure_cause=None,
        resumable=True,
        tokens=TokenAccounting(),
    )


async def test_a_run_whose_provides_node_failed_reports_null_depth(synthetic_naive_store):
    engine = Databasise(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=None,
    )

    envelope = await engine.query(QueryObject(text="Which films did Ed Wood direct?"))

    assert envelope.partial is True
    assert envelope.depth_label is None


async def test_a_naive_run_reports_the_answering_nodes_depth(synthetic_naive_store):
    engine = Databasise(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=counting_clients(synthetic_naive_store["query_vector"]),
    )

    envelope = await engine.query(QueryObject(text="Which films did Ed Wood direct?"))

    assert envelope.partial is False
    assert envelope.depth_label == "stage"


def test_an_envelope_refuses_a_free_text_depth():
    caught: Exception | None = None
    try:
        ResponseEnvelope(answer="", depth_label="bogus", partial=False, degraded=False)
    except Exception as exc:  # noqa: BLE001 - the type name is the assertion
        caught = exc

    assert caught is not None
    assert type(caught).__name__ == "ValidationError"


def test_an_envelope_requires_a_depth_label():
    caught: Exception | None = None
    try:
        ResponseEnvelope(answer="", partial=False, degraded=False)
    except Exception as exc:  # noqa: BLE001
        caught = exc

    assert caught is not None
    assert type(caught).__name__ == "ValidationError"


def test_an_empty_completion_counts_as_answered():
    """Flagged assumption: a provides node that returns an empty completion string answered."""
    node_by_id = {"g": _node_trace("g", effective_depth="evidence")}

    answer, depth_label = _select_answer(["g"], {"g": {"completion": ""}}, node_by_id)

    assert answer == ""
    assert depth_label == "evidence"


def test_no_answering_node_selects_a_null_depth():
    answer, depth_label = _select_answer(["g"], {"g": None}, {"g": _node_trace("g", effective_depth="stage")})

    assert answer == ""
    assert depth_label is None

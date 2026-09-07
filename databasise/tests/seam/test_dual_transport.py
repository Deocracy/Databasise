"""04-05-PLAN.md Task 3: the dual-transport conformance test (D-17, EMBED-02, ROADMAP criterion 5)
— "the same seam reachable two ways with identical behavior." Runs the identical query object
against the identical synthetic store and stub clients twice: once through
``Databasise.query()`` in-process, once through the REST ``/query`` endpoint. Compares every field
``ResponseEnvelope`` declares, introspected from the model itself at test time (never a
hand-written field list, so a field added to the envelope later is compared automatically without
this test needing an update), excluding only the trace reference — the one field this phase's own
design (D-06) requires to differ between two independent runs.

**What is excluded, and why each exclusion is legitimate (04-RESEARCH.md Pattern 5).**
``ResponseEnvelope``'s own declared field set (``databasise/seam/envelope.py``) carries no field
derived from wall-clock time at all — ``answer``, ``evidence``, ``trace_token``, ``depth_label``,
``partial``, ``degraded``, ``stop_reason``, ``degradation_reason``, ``token_accounting``,
``seam_events``. The only field excluded from the envelope comparison is ``trace_token``: each of
the two runs below mints its own fresh ``secrets.token_urlsafe`` reference
(``databasise/seam/trace_store.py``), and D-06 explicitly forbids that reference being derived
from the run's own content — two independent runs minting the *same* token would mean the token
was not random, exactly the property D-06 forbids.

Timing genuinely does exist one level down, behind the reference: ``NodeTrace.wall_clock_ms``
(``databasise/runner/trace.py``) is a real per-node wall-clock measurement, present only in the
*resolved trace record* each ``trace_token`` exchanges for (via ``resolve_trace(debug=True)``),
never in the envelope itself. The separate trace-record comparison below excludes exactly that
field, plus ``run_id`` (a fresh ``uuid4`` ``RunRecord`` mints per run, never derived from content)
— naming both explicitly, the same way the envelope-level exclusion names ``trace_token``
explicitly. Every other field in the resolved record — ``wiring_id``, ``wiring_instance_hash``,
``arm_id``, and every node's own ``instance_hash``/``depth``/``effective_depth``/``tokens``/etc.
— is a deterministic function of the identical resolved wiring and injected query, and is
asserted equal.
"""

from __future__ import annotations

import pytest

# Skips this entire module cleanly (never a collection error) when the `rest` extra is not
# installed — see tests/seam/test_rest_transport.py's identical guard for why.
pytest.importorskip("fastapi")

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam.engine import Databasise
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.query import QueryObject
from databasise.seam.rest import create_app
from fastapi.testclient import TestClient

_QUERY_TEXT = "Which films did Ed Wood direct?"
_STUB_COMPLETION = "This is a stub completion for the dual-transport conformance test."

# See module docstring: the only envelope-level field that legitimately differs between two
# independent runs.
_ENVELOPE_EXCLUDED_FIELDS = frozenset({"trace_token"})

# See module docstring: the resolved trace record's own timing-derived field and run-unique
# identity field.
_RUN_RECORD_TOP_LEVEL_EXCLUDED_FIELDS = frozenset({"run_id"})
_NODE_EXCLUDED_FIELDS = frozenset({"wall_clock_ms"})


class _StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self.vector = vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    async def chat(self, messages, **kwargs):
        return ChatResult(
            text=_STUB_COMPLETION,
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


def _stub_clients(synthetic_naive_store) -> dict[str, object]:
    return {
        "embedding": _StubEmbeddingClient(vector=synthetic_naive_store["query_vector"]),
        "llm": _StubLLMClient(),
    }


def _derived_envelope_fields() -> list[str]:
    """Every field ``ResponseEnvelope`` declares, introspected from the model itself — never a
    hand-written list, so a field added to the envelope later is compared automatically."""
    return list(ResponseEnvelope.model_fields.keys())


def test_the_derived_field_list_is_non_empty_and_the_exclusion_set_is_named_explicitly():
    fields = _derived_envelope_fields()
    assert fields
    assert _ENVELOPE_EXCLUDED_FIELDS == {"trace_token"}
    assert _ENVELOPE_EXCLUDED_FIELDS <= set(fields)


async def test_both_transports_produce_the_same_envelope_for_the_same_query(synthetic_naive_store):
    in_process_engine = Databasise(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=_stub_clients(synthetic_naive_store),
    )
    in_process_envelope = await in_process_engine.query(QueryObject(text=_QUERY_TEXT))
    in_process_dump = in_process_envelope.model_dump()

    rest_app = create_app(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=_stub_clients(synthetic_naive_store),
    )
    client = TestClient(rest_app)
    rest_response = client.post("/query", json={"query": {"text": _QUERY_TEXT}})
    assert rest_response.status_code == 200
    rest_body = rest_response.json()

    compared_fields = [
        field for field in _derived_envelope_fields() if field not in _ENVELOPE_EXCLUDED_FIELDS
    ]
    assert compared_fields, "the compared field set must never be vacuously empty"
    for field in compared_fields:
        assert in_process_dump[field] == rest_body[field], (
            f"envelope field {field!r} diverged between the two transports: "
            f"{in_process_dump[field]!r} != {rest_body[field]!r}"
        )
    # Real values proven present, never a vacuous pass over empty containers on both sides.
    assert in_process_dump["evidence"] and rest_body["evidence"]
    assert in_process_dump["token_accounting"] and rest_body["token_accounting"]

    # The excluded field is present, non-empty, and — per D-06 — distinct on both sides; a
    # trace_token equal across two independent runs would itself be a bug this test would miss
    # if it only asserted equality everywhere.
    assert in_process_dump["trace_token"] and rest_body["trace_token"]
    assert in_process_dump["trace_token"] != rest_body["trace_token"]

    # Separately: each transport's own trace reference independently resolves, through the same
    # seam, to a record whose non-timing/non-run-identity fields agree (see module docstring).
    in_process_record = await in_process_engine.resolve_trace(
        in_process_dump["trace_token"], debug=True
    )
    rest_record = client.post(
        "/trace/resolve", json={"trace_reference": rest_body["trace_token"], "debug": True}
    ).json()

    top_level_fields = [
        key
        for key in in_process_record
        if key != "nodes" and key not in _RUN_RECORD_TOP_LEVEL_EXCLUDED_FIELDS
    ]
    assert top_level_fields
    for key in top_level_fields:
        assert in_process_record[key] == rest_record[key], f"trace record field {key!r} diverged"

    assert in_process_record["nodes"] and len(in_process_record["nodes"]) == len(
        rest_record["nodes"]
    )
    for in_process_node, rest_node in zip(in_process_record["nodes"], rest_record["nodes"]):
        node_fields = [key for key in in_process_node if key not in _NODE_EXCLUDED_FIELDS]
        assert node_fields
        for key in node_fields:
            assert in_process_node[key] == rest_node[key], f"trace node field {key!r} diverged"

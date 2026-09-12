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

import json
from datetime import UTC, datetime

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.runner.trace import TokenAccounting
from databasise.seam.engine import Databasise
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.query import QueryObject
from databasise.seam.refusals import DisagreeingPromotionTraceIdsError
from databasise.seam.rest import create_app
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings
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


# --------------------------------------------------------------------------------------------- #
# 07-03-PLAN.md Task 3: promote/rollback/retire in-process/REST/MCP parity, and refusal parity.
#
# A trace token is inserted directly rather than through `TraceStore.persist()` (which mints a
# fresh `secrets.token_urlsafe()` reference every call, D-06) — a fixed, caller-chosen token lets
# three independent, isolated store roots each resolve the identical `promotion_trace_ids` value,
# which is what makes "ledger records equal on every column except `id` and `created_at`" true
# literally, including `promotion_trace_ids` and `alias` themselves, rather than only up to the
# unavoidable per-store randomness `TraceStore.persist()` would otherwise introduce.
# --------------------------------------------------------------------------------------------- #


def _seed_fixed_trace(store_root, arm_name: str, *, token: str) -> str:
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    node_ids = sorted(resolved.get("nodes", {}).keys())
    fake_record = {
        "run_id": f"fake-run-{arm_name}",
        "wiring_id": resolved.get("wiring_id"),
        "wiring_instance_hash": f"sha256:{'0' * 63}{len(node_ids) % 10}",
        "arm_id": "seam",
        "nodes": [{"node_id": node_id} for node_id in node_ids],
    }
    trace_store = TraceStore(store_root)
    trace_store._conn.execute(
        "INSERT INTO traces (token, run_record, created_at) VALUES (?, ?, ?)",
        (token, json.dumps(fake_record), datetime.now(UTC).isoformat()),
    )
    trace_store._conn.commit()
    return token


def _mcp_available() -> bool:
    try:
        import databasise.mcp  # noqa: F401
    except ImportError:
        return False
    return True


async def _mcp_server(**kwargs):
    from databasise.mcp import create_server

    return create_server(**kwargs)


def _mcp_tool_json(result) -> dict:
    text = "".join(getattr(item, "text", "") or "" for item in result.content)
    return json.loads(text)


_PROMOTION_RESPONSE_EXCLUDED_FIELDS = frozenset({"generation_ordinal"})


def _assert_ledger_records_equal_across_transports(records: dict[str, LedgerRecord]) -> None:
    """Every `LedgerRecord` field (never `id`/`created_at` — neither is a dataclass field at all)
    must be identical across every named transport's own store."""
    compared_fields = list(LedgerRecord.__dataclass_fields__)
    assert compared_fields
    for field in compared_fields:
        values = {name: getattr(record, field) for name, record in records.items()}
        assert len(set(map(str, values.values()))) == 1, f"ledger field {field!r} diverged: {values}"


async def test_promote_parity_across_three_transports(tmp_path):
    if not _mcp_available():
        pytest.skip("the `mcp` extra is not installed")

    alias = "three-transport-promote-alias"
    roots = {name: tmp_path / f"promote-{name}" for name in ("in_process", "rest", "mcp")}
    for root in roots.values():
        root.mkdir()

    trace_ip = _seed_fixed_trace(roots["in_process"], "naive", token="fixed-promote-trace")
    in_process_engine = Databasise(store_root=roots["in_process"], workspace="promote-3t-ip")
    in_process_result = await in_process_engine.promote(alias, [trace_ip], "human_edit")

    trace_rest = _seed_fixed_trace(roots["rest"], "naive", token="fixed-promote-trace")
    rest_app = create_app(store_root=roots["rest"], workspace="promote-3t-rest")
    rest_response = TestClient(rest_app).post(
        "/promote", json={"alias": alias, "trace_ids": [trace_rest], "change_origin": "human_edit"}
    )
    assert rest_response.status_code == 200
    rest_body = rest_response.json()

    trace_mcp = _seed_fixed_trace(roots["mcp"], "naive", token="fixed-promote-trace")
    mcp_server = await _mcp_server(store_root=roots["mcp"], workspace="promote-3t-mcp")
    mcp_body = _mcp_tool_json(
        await mcp_server.call_tool(
            "promote",
            {"args": {"alias": alias, "trace_ids": [trace_mcp], "change_origin": "human_edit"}},
        )
    )

    in_process_body = in_process_result.model_dump()
    compared_fields = [f for f in in_process_body if f not in _PROMOTION_RESPONSE_EXCLUDED_FIELDS]
    assert compared_fields
    for field in compared_fields:
        assert in_process_body[field] == rest_body[field] == mcp_body[field], (
            f"promote response field {field!r} diverged across transports"
        )

    _assert_ledger_records_equal_across_transports(
        {name: Ledger(root).by_alias(alias) for name, root in roots.items()}
    )


async def test_rollback_parity_across_three_transports(tmp_path):
    if not _mcp_available():
        pytest.skip("the `mcp` extra is not installed")

    alias = "three-transport-rollback-alias"
    roots = {name: tmp_path / f"rollback-{name}" for name in ("in_process", "rest", "mcp")}
    for root in roots.values():
        root.mkdir()

    # Two identically-seeded promotions per store (1.0.0, then 1.1.0 — same arm, MINOR bump),
    # then roll back to 1.0.0.
    for name, root in roots.items():
        trace_1 = _seed_fixed_trace(root, "naive", token=f"fixed-rollback-seed-1-{name}")
        trace_2 = _seed_fixed_trace(root, "naive", token=f"fixed-rollback-seed-2-{name}")
        seed_engine = Databasise(store_root=root, workspace=f"rollback-3t-seed-{name}")
        await seed_engine.promote(alias, [trace_1], "human_edit")
        await seed_engine.promote(alias, [trace_2], "human_edit")

    trace_ip = _seed_fixed_trace(roots["in_process"], "naive", token="fixed-rollback-trace")
    in_process_engine = Databasise(store_root=roots["in_process"], workspace="rollback-3t-ip")
    in_process_result = await in_process_engine.rollback(alias, "1.0.0", [trace_ip], "human_edit")

    trace_rest = _seed_fixed_trace(roots["rest"], "naive", token="fixed-rollback-trace")
    rest_app = create_app(store_root=roots["rest"], workspace="rollback-3t-rest")
    rest_response = TestClient(rest_app).post(
        "/rollback",
        json={
            "alias": alias,
            "version": "1.0.0",
            "trace_ids": [trace_rest],
            "change_origin": "human_edit",
        },
    )
    assert rest_response.status_code == 200
    rest_body = rest_response.json()

    trace_mcp = _seed_fixed_trace(roots["mcp"], "naive", token="fixed-rollback-trace")
    mcp_server = await _mcp_server(store_root=roots["mcp"], workspace="rollback-3t-mcp")
    mcp_body = _mcp_tool_json(
        await mcp_server.call_tool(
            "rollback",
            {
                "args": {
                    "alias": alias,
                    "version": "1.0.0",
                    "trace_ids": [trace_mcp],
                    "change_origin": "human_edit",
                }
            },
        )
    )

    in_process_body = in_process_result.model_dump()
    compared_fields = [f for f in in_process_body if f not in _PROMOTION_RESPONSE_EXCLUDED_FIELDS]
    assert compared_fields
    for field in compared_fields:
        assert in_process_body[field] == rest_body[field] == mcp_body[field], (
            f"rollback response field {field!r} diverged across transports"
        )

    _assert_ledger_records_equal_across_transports(
        {name: Ledger(root).by_alias(alias) for name, root in roots.items()}
    )


async def test_retire_parity_across_three_transports(tmp_path):
    if not _mcp_available():
        pytest.skip("the `mcp` extra is not installed")

    alias = "three-transport-retire-alias"
    roots = {name: tmp_path / f"retire-{name}" for name in ("in_process", "rest", "mcp")}
    for root in roots.values():
        root.mkdir()

    # naive (1.0.0) then bypass (2.0.0, MAJOR — differing declared surface), so the active
    # generation is not the one being retired (1.0.0).
    for name, root in roots.items():
        trace_naive = _seed_fixed_trace(root, "naive", token=f"fixed-retire-seed-naive-{name}")
        trace_bypass = _seed_fixed_trace(root, "bypass", token=f"fixed-retire-seed-bypass-{name}")
        seed_engine = Databasise(store_root=root, workspace=f"retire-3t-seed-{name}")
        await seed_engine.promote(alias, [trace_naive], "human_edit")
        await seed_engine.promote(alias, [trace_bypass], "human_edit")

    trace_ip = _seed_fixed_trace(roots["in_process"], "naive", token="fixed-retire-trace")
    in_process_engine = Databasise(store_root=roots["in_process"], workspace="retire-3t-ip")
    in_process_result = await in_process_engine.retire(alias, "1.0.0", [trace_ip], "human_edit")

    trace_rest = _seed_fixed_trace(roots["rest"], "naive", token="fixed-retire-trace")
    rest_app = create_app(store_root=roots["rest"], workspace="retire-3t-rest")
    rest_response = TestClient(rest_app).post(
        "/retire",
        json={
            "alias": alias,
            "version": "1.0.0",
            "trace_ids": [trace_rest],
            "change_origin": "human_edit",
        },
    )
    assert rest_response.status_code == 200
    rest_body = rest_response.json()

    trace_mcp = _seed_fixed_trace(roots["mcp"], "naive", token="fixed-retire-trace")
    mcp_server = await _mcp_server(store_root=roots["mcp"], workspace="retire-3t-mcp")
    mcp_body = _mcp_tool_json(
        await mcp_server.call_tool(
            "retire",
            {
                "args": {
                    "alias": alias,
                    "version": "1.0.0",
                    "trace_ids": [trace_mcp],
                    "change_origin": "human_edit",
                }
            },
        )
    )

    in_process_body = in_process_result.model_dump()
    compared_fields = [f for f in in_process_body if f not in _PROMOTION_RESPONSE_EXCLUDED_FIELDS]
    assert compared_fields
    for field in compared_fields:
        assert in_process_body[field] == rest_body[field] == mcp_body[field], (
            f"retire response field {field!r} diverged across transports"
        )

    # by_alias() deliberately excludes tombstoned rows (07-01-SUMMARY.md) — it would return the
    # still-active `bypass`/2.0.0 seed generation, not the tombstone this test wrote. The tombstone
    # is the latest record naming the (alias, "1.0.0") generation specifically.
    _assert_ledger_records_equal_across_transports(
        {name: Ledger(root).generation_state(alias, "1.0.0") for name, root in roots.items()}
    )


async def test_refusal_parity_across_three_transports(tmp_path):
    """One refusing input — a disagreeing trace-id pair — refuses on all three transports, all
    three naming the identical refusal class, with nothing written to the ledger. A single shared
    store is safe here: a refusal fires before any write (test_promote.py's own
    `test_disagreeing_trace_ids_refuse_rather_than_pick_one` proves the identical property
    in-process), so driving all three transports against it accumulates no state."""
    if not _mcp_available():
        pytest.skip("the `mcp` extra is not installed")

    store_root = tmp_path / "refusal-3t-store"
    store_root.mkdir()
    trace_naive = _seed_fixed_trace(store_root, "naive", token="fixed-refusal-naive")
    trace_bypass = _seed_fixed_trace(store_root, "bypass", token="fixed-refusal-bypass")
    alias = "three-transport-refusal-alias"
    body = {"alias": alias, "trace_ids": [trace_naive, trace_bypass], "change_origin": "human_edit"}

    in_process_engine = Databasise(store_root=store_root, workspace="refusal-3t-ip")
    with pytest.raises(DisagreeingPromotionTraceIdsError) as in_process_exc_info:
        await in_process_engine.promote(alias, [trace_naive, trace_bypass], "human_edit")
    assert type(in_process_exc_info.value).__name__ == "DisagreeingPromotionTraceIdsError"

    rest_app = create_app(store_root=store_root, workspace="refusal-3t-rest")
    rest_response = TestClient(rest_app).post("/promote", json=body)
    assert rest_response.status_code == 422
    assert rest_response.json()["refusal_type"] == "DisagreeingPromotionTraceIdsError"

    from databasise.mcp import create_server
    from databasise.mcp._sdk import import_sdk

    ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError
    mcp_server = create_server(store_root=store_root, workspace="refusal-3t-mcp")
    with pytest.raises(ToolError) as mcp_exc_info:
        await mcp_server.call_tool("promote", {"args": body})
    mcp_detail_text = str(mcp_exc_info.value)
    mcp_detail = json.loads(mcp_detail_text[mcp_detail_text.index("{") :])
    assert mcp_detail["refusal_type"] == "DisagreeingPromotionTraceIdsError"

    assert Ledger(store_root)._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == 0

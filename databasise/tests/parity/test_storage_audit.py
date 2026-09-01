"""Tests for D-15's per-node storage-ownership audit (03-08-PLAN.md Task 1).

Three groups: (1) the cross-check logic (``audit_run``/``_declared_handles``) in isolation,
against synthetic ``Part``s — no real run needed; (2) the scheduler's own recorder threading and
the proof that an undeclared touch fails the run rather than ever reaching the audit; (3) the
full ``naive`` arm driven end to end through ``storage_audit.run_audit`` against a synthetic
store with stub clients — the non-negotiable, any-machine path, mirroring
``test_naive_arm_end_to_end.py``'s own stub-client convention.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parity import storage_audit
from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.parts_core import UndeclaredEffectError
from databasise.runner import scheduler
from databasise.runner.trace import TokenAccounting
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring

# --------------------------------------------------------------------------------------------- #
# Group 1: audit_run / _declared_handles cross-check logic, in isolation
# --------------------------------------------------------------------------------------------- #


def _part(node_id: str, effects: list[str]) -> Part:
    return Part(
        name_at_version=f"test/{node_id}@0.1.0",
        kind="retriever",
        structural_depth="stage",
        effects=effects,
        upstream_ref=None,
    )


def _parsed(node_effects: dict[str, list[str]]) -> SimpleNamespace:
    """A minimal stand-in for ``ParsedWiring``: ``audit_run`` only reads ``.node_order`` and
    ``.parts[node_id]``, so a full ``ParsedWiring``/registry round-trip is unnecessary here.
    """
    return SimpleNamespace(
        node_order=tuple(node_effects),
        parts={node_id: _part(node_id, effects) for node_id, effects in node_effects.items()},
    )


def test_declared_handles_maps_client_effects_and_store_effects_separately():
    handles = storage_audit._declared_handles(["calls_llm", "reads_kv", "writes_vector"])
    assert handles == frozenset({("client", "llm"), ("store", "kv"), ("store", "vector")})


def test_matched_when_every_declared_handle_was_touched():
    parsed = _parsed({"n1": ["reads_kv"]})
    rows, violations = storage_audit.audit_run(parsed, [("n1", "store", "kv")])

    assert violations == []
    assert len(rows) == 1
    assert rows[0].state == "matched"
    assert rows[0].unused_effects == ()


def test_no_touch_when_a_node_with_declared_effects_touched_nothing():
    parsed = _parsed({"n1": ["calls_rerank"]})
    rows, violations = storage_audit.audit_run(parsed, [])

    assert violations == []
    assert rows[0].state == "no-touch"
    assert rows[0].touched == ()
    assert rows[0].unused_effects == ()


def test_over_declared_when_some_but_not_all_declared_handles_were_touched():
    parsed = _parsed({"n1": ["reads_kv", "reads_vector"]})
    rows, violations = storage_audit.audit_run(parsed, [("n1", "store", "kv")])

    assert violations == []
    assert rows[0].state == "over-declared"
    assert rows[0].unused_effects == ("store:vector",)


def test_matched_vacuously_when_a_node_declares_no_store_or_client_effect_at_all():
    """A pure-transform node (a join/truncator, effects=[]) has nothing to own — the
    storage-ownership question is vacuous, not a suspicious absence (which is what "no-touch"
    exists to flag for a node that DID declare a handle it could have reached).
    """
    parsed = _parsed({"join": []})
    rows, violations = storage_audit.audit_run(parsed, [])

    assert violations == []
    assert rows[0].state == "matched"
    assert rows[0].touched == ()


def test_no_touch_and_over_declared_and_matched_are_counted_separately_in_one_run():
    parsed = _parsed(
        {
            "matched-node": ["reads_kv"],
            "no-touch-node": ["calls_rerank"],
            "over-declared-node": ["reads_kv", "reads_vector"],
        }
    )
    touches = [
        ("matched-node", "store", "kv"),
        ("over-declared-node", "store", "kv"),
    ]
    rows, violations = storage_audit.audit_run(parsed, touches)

    assert violations == []
    states = {row.node_id: row.state for row in rows}
    assert states == {
        "matched-node": "matched",
        "no-touch-node": "no-touch",
        "over-declared-node": "over-declared",
    }


def test_a_touch_outside_the_declared_handles_is_reported_as_a_violation_not_silently_dropped():
    """Structurally impossible through the real scheduler path (see the recorder-threading group
    below) but checked for defensively — the audit's own bookkeeping must never let an anomaly
    disappear into a report row that reads as clean.
    """
    parsed = _parsed({"n1": ["reads_kv"]})
    rows, violations = storage_audit.audit_run(parsed, [("n1", "store", "vector")])

    assert len(violations) == 1
    assert violations[0].node_id == "n1"
    assert violations[0].reference == "store:vector"


# --------------------------------------------------------------------------------------------- #
# Group 2: recorder threading at the scheduler level, and the undeclared-touch refusal proof
# --------------------------------------------------------------------------------------------- #


def _minimal_parsed(nodes: dict, parts: dict, deps: dict) -> ParsedWiring:
    return ParsedWiring(
        nodes=nodes, parts=parts, deps=deps, node_order=tuple(sorted(nodes)), report=ValidationReport()
    )


async def test_recorder_receives_node_id_kind_and_key_on_every_successful_resolution():
    async def body(ctx: NodeContext):
        return {"kv": ctx.stores["kv"], "llm": ctx.clients["llm"]}

    part = Part(
        name_at_version="test/toucher@1.0.0",
        kind="retriever",
        structural_depth="stage",
        effects=["reads_kv", "calls_llm"],
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component="test/toucher@1.0.0", kind="retriever", effects=["reads_kv", "calls_llm"], deps=[])
    parsed = _minimal_parsed({"n1": node}, {"n1": part}, {"n1": ()})

    touches: list[tuple[str, str, str]] = []
    result = await scheduler.run_wiring(
        parsed,
        PartRegistry(),
        {"kv": object()},
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
        clients={"llm": object()},
        recorder=lambda node_id, kind, key: touches.append((node_id, kind, key)),
    )

    assert result["partial"] is False
    assert set(touches) == {("n1", "store", "kv"), ("n1", "client", "llm")}


async def test_no_recorder_passed_behaves_exactly_as_before():
    """``recorder`` defaults to ``None`` and every existing call site passes none — this asserts
    the default path still runs a node clean with no recorder-related change in outcome.
    """
    async def body(ctx: NodeContext):
        return {"kv": ctx.stores["kv"]}

    part = Part(
        name_at_version="test/no-recorder@1.0.0",
        kind="retriever",
        structural_depth="stage",
        effects=["reads_kv"],
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component="test/no-recorder@1.0.0", kind="retriever", effects=["reads_kv"], deps=[])
    parsed = _minimal_parsed({"n1": node}, {"n1": part}, {"n1": ()})

    result = await scheduler.run_wiring(
        parsed,
        PartRegistry(),
        {"kv": "the-kv-store"},
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )

    assert result["partial"] is False
    assert result["results"]["n1"]["kv"] == "the-kv-store"


async def test_an_undeclared_store_reach_fails_the_run_rather_than_appearing_in_the_audit():
    """The audit's own "no undeclared touch can appear" claim rests on
    ``CapabilityScopedStores.require`` raising before ever returning a handle — proven here
    directly rather than merely restated in the audit's docstring.
    """

    async def body(ctx: NodeContext):
        return {"vector": ctx.stores["vector"]}  # reaches for an effect this part never declared

    part = Part(
        name_at_version="test/reaches-undeclared@1.0.0",
        kind="retriever",
        structural_depth="stage",
        effects=["reads_kv"],  # declares only reads_kv
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component="test/reaches-undeclared@1.0.0", kind="retriever", effects=["reads_kv"], deps=[])
    parsed = _minimal_parsed({"n1": node}, {"n1": part}, {"n1": ()})

    touches: list[tuple[str, str, str]] = []
    result = await scheduler.run_wiring(
        parsed,
        PartRegistry(),
        {"kv": object(), "vector": object()},
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
        recorder=lambda node_id, kind, key: touches.append((node_id, kind, key)),
    )

    assert result["partial"] is True
    trace = next(n for n in result["nodes"] if n.node_id == "n1")
    assert "undeclared effect" in trace.cross_process_failure_cause
    # The refused reach never got far enough to notify the recorder — nothing appears in the
    # audit's own input, which is the mechanism this test exists to prove.
    assert touches == []


def test_undeclared_effect_error_is_the_real_refusal_capability_scoped_stores_raises():
    """A direct, non-scheduler confirmation that the refusal class the trace above names is the
    real one this codebase's deny-by-default enforcement raises."""
    from databasise.parts_core import CapabilityScopedStores

    scoped = CapabilityScopedStores({"kv": object()}, ["reads_kv"])
    with pytest.raises(UndeclaredEffectError):
        scoped.require("reads_vector")


# --------------------------------------------------------------------------------------------- #
# Group 3: the naive arm, end to end, against a synthetic store with stub clients
# --------------------------------------------------------------------------------------------- #


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
            text="stub completion for the storage audit's own naive-arm test.",
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


@pytest.fixture
async def synthetic_naive_store(store_root):
    """The same minimal synthetic imported-store shape ``test_naive_arm_end_to_end.py``'s own
    ``synthetic_naive_store`` fixture builds — one chunk, one query-matching direction, enough for
    a full seven-node dispatch, built directly through the v2 stores' own public write paths.
    """
    workspace = "storage-audit-naive-test"
    query_vector = [1.0, 0.0, 0.0]

    vector_store = FaissVectorStore(namespace="chunks", workspace=workspace, store_root=store_root)
    await vector_store.upsert(
        ids=["chunk-1"],
        embeddings=np.array([query_vector]),
        metadatas=[{"content": "Ed Wood directed several low-budget films."}],
    )
    await vector_store.index_done_callback()

    kv_store = SqliteKVStore(namespace="text_chunks", workspace=workspace, store_root=store_root)
    await kv_store.upsert(
        {"chunk-1": {"content": "Ed Wood directed several low-budget films.", "file_path": "ed_wood.txt"}}
    )
    await kv_store.index_done_callback()

    return {"store_root": store_root, "workspace": workspace, "query_vector": query_vector}


async def test_naive_arm_audit_runs_clean_with_the_three_states_counted_separately(
    synthetic_naive_store,
):
    embedding_client = _StubEmbeddingClient(vector=synthetic_naive_store["query_vector"])
    llm_client = _StubLLMClient()

    result = await storage_audit.run_audit(
        "naive",
        "Which films did Ed Wood direct?",
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients={"embedding": embedding_client, "llm": llm_client},
    )

    assert result["partial"] is False
    assert result["violations"] == []

    rows = result["rows"]
    node_ids = {row.node_id for row in rows}
    assert node_ids == {
        "embedder-query",
        "chunk-vector",
        "heading-backfill",
        "rerank",
        "assemble",
        "generate",
        "embedder-index",
    }

    by_id = {row.node_id: row for row in rows}
    # Nodes whose declared effect(s) were fully exercised by this run.
    assert by_id["embedder-query"].state == "matched"
    assert by_id["chunk-vector"].state == "matched"
    assert by_id["heading-backfill"].state == "matched"
    assert by_id["generate"].state == "matched"
    # assemble declares no store/client effect at all (pure transform) — vacuously matched.
    assert by_id["assemble"].state == "matched"
    # rerank declares calls_rerank but the naive arm's own committed config never sets
    # live_rerank, so its body never reaches ctx.clients["rerank"] at all.
    assert by_id["rerank"].state == "no-touch"
    # embedder-index declares calls_embedding/writes_artifact but this run configures no
    # config["sample"] (the driver only injects query text onto embedder-query/generate — see
    # embedder_index.py's own docstring), so its body returns an empty artifact without ever
    # reaching ctx.clients["embedding"] at all: genuinely no-touch on this real run, not an
    # over-declared node with a live-but-partial embedding call. The over-declared state itself
    # (chunk-sel-kg's reads_vector on a WEIGHT-only config, per §19.9) is proven directly against
    # a synthetic Part in the isolated audit_run cases above — this arm never dispatches
    # chunk-sel-kg (naive removes the graph-half nodes entirely).
    assert by_id["embedder-index"].state == "no-touch"

    states = [row.state for row in rows]
    assert states.count("matched") == 5
    assert states.count("no-touch") == 2
    assert states.count("over-declared") == 0


async def test_naive_arm_audit_report_matches_the_summary_line(synthetic_naive_store):
    embedding_client = _StubEmbeddingClient(vector=synthetic_naive_store["query_vector"])
    llm_client = _StubLLMClient()

    result = await storage_audit.run_audit(
        "naive",
        "Which films did Ed Wood direct?",
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients={"embedding": embedding_client, "llm": llm_client},
    )

    summary = storage_audit._render_summary(result["rows"])
    assert "matched=5" in summary
    assert "no-touch=2" in summary
    assert "over-declared=0" in summary


# --------------------------------------------------------------------------------------------- #
# CLI presentation (main()) — isolated from any real run via monkeypatched run_audit
# --------------------------------------------------------------------------------------------- #


def test_main_prints_one_row_per_node_and_a_three_way_summary_line(monkeypatch, capsys):
    fake_rows = [
        storage_audit.AuditRow(
            node_id="a", component="x@0.1.0", declared_effects=("reads_kv",),
            touched=("store:kv",), state="matched", unused_effects=(),
        ),
        storage_audit.AuditRow(
            node_id="b", component="y@0.1.0", declared_effects=("calls_rerank",),
            touched=(), state="no-touch", unused_effects=(),
        ),
        storage_audit.AuditRow(
            node_id="c", component="z@0.1.0", declared_effects=("reads_kv", "reads_vector"),
            touched=("store:kv",), state="over-declared", unused_effects=("store:vector",),
        ),
    ]

    async def fake_run_audit(arm_name, query, **kwargs):
        return {"rows": fake_rows, "violations": [], "partial": False}

    monkeypatch.setattr(storage_audit, "run_audit", fake_run_audit)

    status = storage_audit.main(["--arm", "naive"])
    captured = capsys.readouterr()

    assert status == 0
    assert captured.out.count("state=matched") == 1
    assert captured.out.count("state=no-touch") == 1
    assert captured.out.count("state=over-declared") == 1
    assert "matched=1" in captured.out
    assert "no-touch=1" in captured.out
    assert "over-declared=1" in captured.out


def test_main_exits_1_and_prints_every_violation_when_any_exist(monkeypatch, capsys):
    async def fake_run_audit(arm_name, query, **kwargs):
        return {
            "rows": [],
            "violations": [storage_audit.Violation(node_id="x", reference="store:mystery")],
            "partial": False,
        }

    monkeypatch.setattr(storage_audit, "run_audit", fake_run_audit)

    status = storage_audit.main(["--arm", "naive"])
    captured = capsys.readouterr()

    assert status == 1
    assert "VIOLATION: x: store:mystery" in captured.out

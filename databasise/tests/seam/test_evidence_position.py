"""WIRE-02 row tests: the KG arms return the chunks they put into the context as evidence.

LightRAG ``assemble`` emits ``items`` (v1's truncated chunk reference list) and the local, global
and hybrid arms point ``evidence_position`` at it; bypass declares none. This file is new because
the neighbouring seam tests are ledger-protected. Every test imports only names that exist at the
phase base and captures exceptions, so a failure at the base is a plain ``AssertionError``
(Phase 13 fail-first rule). The real-driver test drives one ingest through the hermetic loopback
harness and is skipped only when ``v1/.venv/bin/python`` is absent.
"""

from __future__ import annotations

from typing import Any

import pytest
from databasise.clients.builder import build_clients
from databasise.parity.run_comparison import _inject_pinned_keywords
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.assemble import LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.tests.fixtures.v1_stub_server import (  # noqa: F401 - fixture
    real_v1,
    requires_v1,
)
from databasise.wirings.resolve import resolve_arm

_TEXT = "UNIQalpha Corp builds bridges in UNIQalpha City."
_QUERY = "What does UNIQalpha Corp build in UNIQalpha City?"
_KEYWORDS = {"hl_keywords": ["bridge building"], "ll_keywords": ["UNIQalpha Corp", "UNIQalpha City"]}
_ASSEMBLE_AS_EVIDENCE = {"node": "assemble", "namespace": "chunks"}


async def test_assemble_emits_the_chunks_it_put_into_the_context():
    # The second chunk is far over v1's token budget, so only the first is admitted.
    candidates = [
        {"id": "c1", "chunk_id": "c1", "content": "chunk one", "file_path": "a.txt", "score": 0.5},
        {"id": "c2", "chunk_id": "c2", "content": "x" * 400_000, "file_path": "b.txt", "score": 0.4},
    ]
    ctx = NodeContext(node_id="assemble", config={}, inputs={"rerank": {"items": candidates}}, stores={}, clients={})

    result = await LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.body(ctx)

    assert result["chunk_count"] == 1
    assert result.get("items") == [{"id": "c1", "score": 0.5}]


async def test_assemble_items_follow_the_context_order_and_carry_no_invented_score():
    candidates = [{"id": "z", "content": "z"}, {"id": "a", "content": "a"}, {"id": "m", "content": "m"}]
    ctx = NodeContext(node_id="assemble", config={}, inputs={"rerank": {"items": candidates}}, stores={}, clients={})

    result = await LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.body(ctx)

    assert result.get("items") == [{"id": "z", "score": None}, {"id": "a", "score": None}, {"id": "m", "score": None}]


@requires_v1
async def test_a_local_arm_query_returns_non_empty_evidence_that_resolves(real_v1):  # noqa: F811
    engine = Databasise(store_root=real_v1.store_root, workspace="wire02-local", clients=build_clients(real_v1.client_env))
    job = await engine.ingest(IngestDocument(document_id="evdoc1", text=_TEXT))
    assert job.enqueued == 1
    resolved = _inject_pinned_keywords(resolve_arm("local"), **_KEYWORDS)

    envelope = await engine._execute_resolved(QueryObject(text=_QUERY), resolved)

    assert len(envelope.evidence) > 0
    for ref in envelope.evidence:
        record = await engine.resolve_evidence(ref)
        assert record, ref

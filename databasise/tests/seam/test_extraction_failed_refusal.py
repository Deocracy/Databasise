"""Phase 12 HIPP-10 (D-08): an OpenIE extraction failure refuses the whole HippoRAG ingest as a
``ForeignEngineRefusalError`` of failure class ``ExtractionFailed`` (REST 502), carrying only a failed
chunk count and closed reason codes, never provider text, and commits nothing."""

from __future__ import annotations

import re

import pytest

from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.stores.vector import FaissVectorStore
from seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _HIPPORAG_CAPABILITY,
    _WORKSPACE,
    _StubEmbeddingClient,
    _StubIngestQueryLLMClient,
)

_REASON_GRAMMAR = re.compile(r"unparseable_response|llm_call_failed:[A-Za-z_][A-Za-z0-9_]{0,63}")


class _MalformedNerLLM(_StubIngestQueryLLMClient):
    """Answers every NER prompt with text that is not JSON; every other prompt as the base stub."""

    async def chat(self, messages, **kwargs):
        if "---Recognised Entities---" not in messages[0]["content"] and "---Candidate Facts---" not in messages[0]["content"]:
            result = await super().chat(messages, **kwargs)
            return type(result)(
                text="not json",
                tokens=result.tokens,
                resolved_model_identity=result.resolved_model_identity,
            )
        return await super().chat(messages, **kwargs)


async def test_a_malformed_openie_response_is_a_502_extraction_failed_refusal_and_commits_nothing(store_root):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from databasise.seam.rest import create_app

    app = create_app(
        store_root=store_root,
        workspace=_WORKSPACE,
        clients={"embedding": _StubEmbeddingClient(), "llm": _MalformedNerLLM()},
    )
    response = TestClient(app).post(
        "/documents",
        json={
            "document": {"document_id": "doc-malformed", "text": _DOCUMENT_TEXT},
            "selector": {"capability": _HIPPORAG_CAPABILITY},
        },
    )

    assert response.status_code == 502, response.text
    body = response.json()
    assert body["refusal_type"] == "ForeignEngineRefusalError"
    assert body["failure_class"] == "ExtractionFailed"
    assert body["failed_chunks"] == 1
    assert body["failure_reasons"] == ["unparseable_response"]
    assert len(response.content) < 1024
    assert "not json" not in response.text

    chunks = FaissVectorStore("hipporag-chunks", _WORKSPACE, store_root)
    try:
        assert list(chunks.iter_vectors()) == []
    finally:
        await chunks.finalize()


class ExtractionFailedError(Exception):
    """Stands in for ``parts_core.hipporag.openie.ExtractionFailedError``: the refusal keys on the type name."""

    def __init__(self, failed_chunks: int, failure_reasons: list[str]) -> None:
        self.failed_chunks = failed_chunks
        self.failure_reasons = failure_reasons
        super().__init__("OpenIE extraction failed")


def test_the_refusal_caps_failure_reasons_at_ten_and_drops_codes_outside_the_grammar():
    reasons = ["raw text with spaces", "x" * 80] + [f"llm_call_failed:Err{i}" for i in range(18)]
    reasons += ["llm_call_failed:" + "E" * 65, 12345]

    refusal = ForeignEngineRefusalError(
        operation="ingest", cause=ExtractionFailedError(len(reasons), reasons)
    )

    assert refusal.failure_class == "ExtractionFailed"
    assert refusal.failed_chunks == len(reasons)
    assert len(refusal.failure_reasons) == 10
    assert all(_REASON_GRAMMAR.fullmatch(code) for code in refusal.failure_reasons)
    assert refusal.failure_reasons[0] == "llm_call_failed:Err0"

"""11 REVIEW A-WR-05: D-11 keeps v1's stderr tail in the server log, so key-shaped tokens in it
(``sk-...``, ``Bearer ...``, ``api_key=...``) are redacted before it can be logged."""

from __future__ import annotations

import pytest
from databasise.foreign import CorpusOpSubprocessError
from databasise.foreign.v1_corpus_adapter import redact_secrets
from databasise.parts_core.lightrag import full_ingest
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.refusals import ForeignEngineRefusalError

_SECRETS = ("sk-proj-abc123XYZ", "abc***xyz", "tok-live-999", "hunter2secret", "s3cr3t-value")
_STDERR = (
    "openai.AuthenticationError: Incorrect API key provided: sk-proj-abc123XYZ\n"
    "provider echoed sk-abc***xyz\n"
    "headers: {'Authorization': 'Bearer tok-live-999'}\n"
    "LLM_BINDING_API_KEY=hunter2secret base_url=http://127.0.0.1:9/v1\n"
    'body: {"api_key": "s3cr3t-value"}\n'
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("key sk-proj-abc123XYZ end", "key sk-[REDACTED] end"),
        ("Authorization: Bearer tok-live-999", "Authorization: Bearer [REDACTED]"),
        ("api_key=hunter2secret&x=1", "api_key=[REDACTED]&x=1"),
        ('"api-key": "s3cr3t"', '"api-key": "[REDACTED]"'),
        ("task-runner and risk-free stay", "task-runner and risk-free stay"),
        ("url?key=AIzaSECRET&x=1", "url?key=[REDACTED]&x=1"),
        ("monkey=1 turnkey=2", "monkey=1 turnkey=2"),
    ],
)
def test_redact_secrets_masks_key_shaped_tokens_only(text, expected):
    assert redact_secrets(text) == expected


def test_the_subprocess_error_never_carries_a_key_shaped_token():
    error = CorpusOpSubprocessError(1, _STDERR)

    for secret in _SECRETS:
        assert secret not in str(error) and secret not in error.stderr
    assert "base_url=http://127.0.0.1:9/v1" in str(error)  # the tail is otherwise kept (D-11)


async def test_the_server_log_of_a_driver_fault_holds_no_key(tmp_path, monkeypatch, caplog):
    def _fails(*_args, **_kwargs):
        raise CorpusOpSubprocessError(1, _STDERR)

    monkeypatch.setattr(full_ingest, "run_corpus_op", _fails)
    engine = Databasise(store_root=tmp_path, workspace="ws")

    with caplog.at_level("WARNING"), pytest.raises(ForeignEngineRefusalError):
        await engine.ingest(IngestDocument(document_id="d", text="t"))

    assert "AuthenticationError" in caplog.text
    for secret in _SECRETS:
        assert secret not in caplog.text


_PROVIDER_ERROR = (
    "provider 401: invalid api_key=sk-SECRET123 at https://api.example.com/v1?key=AIzaSECRET"
)
_LEAKS = ("sk-SECRET123", "AIzaSECRET", "api.example.com")


class _RaisingEmbeddingClient:
    async def embed(self, texts, **kwargs):
        raise RuntimeError(_PROVIDER_ERROR)


async def test_an_in_process_provider_error_is_logged_without_its_key_or_url(tmp_path, caplog):
    """A-WR-05 (D-11): the server log of an in-process provider fault names the exception type and a
    redacted traceback, never the key or the provider URL; ``refusal.cause`` keeps the original."""
    from seam.test_hipporag_write_path import _DOCUMENT_TEXT, _HIPPORAG_CAPABILITY, _StubIngestQueryLLMClient

    from databasise.seam.selectors import Selector

    engine = Databasise(
        store_root=tmp_path,
        workspace="redact-ws",
        clients={"embedding": _RaisingEmbeddingClient(), "llm": _StubIngestQueryLLMClient()},
    )
    caught = None
    with caplog.at_level("ERROR", logger="databasise.seam.engine"):
        try:
            await engine.ingest(
                IngestDocument(document_id="redact-doc", text=_DOCUMENT_TEXT),
                selector=Selector(capability=_HIPPORAG_CAPABILITY),
            )
        except Exception as exc:  # noqa: BLE001 - asserted below
            caught = exc

    assert type(caught).__name__ == "ForeignEngineRefusalError"
    assert "sk-SECRET123" in str(caught.cause)  # the in-process cause stays whole
    assert "RuntimeError" in caplog.text
    for leak in _LEAKS:
        assert leak not in caplog.text
    assert all(not record.exc_info for record in caplog.records)


async def test_a_failed_query_nodes_debug_cause_is_redacted(tmp_path):
    """D-11: ``cross_process_failure_cause`` reaches ``resolve_trace(debug=True)``; it carries the
    exception type and no key-shaped token."""
    from seam.test_hipporag_write_path import (
        _DOCUMENT_TEXT,
        _HIPPORAG_CAPABILITY,
        _StubEmbeddingClient,
        _StubIngestQueryLLMClient,
    )

    from databasise.seam.query import QueryObject
    from databasise.seam.selectors import Selector

    selector = Selector(capability=_HIPPORAG_CAPABILITY)
    good = Databasise(
        store_root=tmp_path,
        workspace="redact-query-ws",
        clients={"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()},
    )
    await good.ingest(IngestDocument(document_id="redact-q-doc", text=_DOCUMENT_TEXT), selector=selector)

    broken = Databasise(
        store_root=tmp_path,
        workspace="redact-query-ws",
        clients={"embedding": _RaisingEmbeddingClient(), "llm": _StubIngestQueryLLMClient()},
    )
    outcome = None
    try:
        outcome = await broken.query(QueryObject(text="What did Ed Wood direct?"), selector)
    except Exception as exc:  # noqa: BLE001 - reported below
        outcome = exc
    trace_token = getattr(outcome, "trace_token", None)
    assert trace_token, f"the failed query produced no trace: {outcome!r}"

    trace = await broken.resolve_trace(trace_token, debug=True)
    causes = [n["cross_process_failure_cause"] for n in trace["nodes"] if n.get("cross_process_failure_cause")]
    assert causes
    assert any(cause.startswith("NodeExecutionError: ") for cause in causes)
    for cause in causes:
        assert "sk-SECRET123" not in cause
        assert "AIzaSECRET" not in cause

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

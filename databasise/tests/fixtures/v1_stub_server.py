"""Hermetic real-driver harness (11-01-PLAN.md Task 1, 11-RESEARCH.md "Hermetic Real-Driver Harness").

The real v1 corpus driver runs under v1's own interpreter against a loopback OpenAI-compatible
stub server, so a test exercises v1's real enqueue/pipeline/storage code with no network and no
real key. Stdlib only.

- :class:`StubModelServer`: ``POST /v1/chat/completions`` answers extraction prompts in v1's
  delimiter format (one ``<tok> Corp`` and one ``<tok> City`` entity plus one relation for every
  distinct ``UNIQ...`` token in the prompt) and anything else with ``"stub answer"``;
  ``POST /v1/embeddings`` returns a deterministic 8-dim vector per input.
- :func:`write_env_overlay`: the temp env file the adapter applies over ``os.environ``. Values are
  stub-local strings, never real keys.
- ``requires_v1``: skip marker when ``v1/.venv/bin/python`` is absent.
- ``real_v1``: fixture that starts the server, writes the overlay and points
  ``v1_corpus_adapter.DEFAULT_V1_ENV_PARITY`` at it, so no test ever reads the real parity env.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import struct
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from databasise.foreign import v1_corpus_adapter
from databasise.foreign.v1_corpus_adapter import DEFAULT_V1_INTERPRETER

EMBEDDING_DIM = 8
_TOKEN = re.compile(r"UNIQ[A-Za-z0-9]+")
_WORD = re.compile(r"\w+")

requires_v1 = pytest.mark.skipif(
    not DEFAULT_V1_INTERPRETER.exists(), reason="v1/.venv/bin/python is absent"
)


def stub_vector(text: str) -> list[float]:
    """Hashed bag of words, L2-normalised, never all-zero."""
    vec = [0.0] * EMBEDDING_DIM
    for word in _WORD.findall(str(text).lower()):
        vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIM] += 1.0
    if not any(vec):
        vec[0] = 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec]


def _extraction_rows(text: str) -> str:
    rows: list[str] = []
    for tok in dict.fromkeys(_TOKEN.findall(text)):  # distinct, first-seen order
        rows.append(f"entity<|#|>{tok} Corp<|#|>Organization<|#|>{tok} Corp is an organization.")
        rows.append(f"entity<|#|>{tok} City<|#|>Location<|#|>{tok} City is a place.")
        rows.append(f"relation<|#|>{tok} Corp<|#|>{tok} City<|#|>located in<|#|>{tok} Corp is in {tok} City.")
    rows.append("<|COMPLETE|>")
    return "\n".join(rows)


class StubModelServer:
    """A loopback OpenAI-compatible server on a daemon thread. Tests may set ``omit_usage`` and
    ``delay_for`` (token -> seconds to sleep before answering a chat request containing it)."""

    def __init__(self) -> None:
        self.chat_calls: list[str] = []
        self.omit_usage = False
        self.delay_for: dict[str, float] = {}
        server_ref = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:  # keep test output quiet
                pass

            def _send(self, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:  # noqa: N802 - http.server naming
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path.endswith("/chat/completions"):
                    self._send(server_ref._chat(request))
                elif self.path.endswith("/embeddings"):
                    self._send(server_ref._embed(request))
                else:
                    self.send_error(404)

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._httpd.daemon_threads = True
        self.url = f"http://127.0.0.1:{self._httpd.server_address[1]}/v1"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def _chat(self, request: dict[str, Any]) -> dict[str, Any]:
        text = "\n".join(str(m.get("content")) for m in request.get("messages", []))
        self.chat_calls.append(text)
        for token, seconds in self.delay_for.items():
            if token in text:
                time.sleep(seconds)
        content = _extraction_rows(text) if "entities and relationships" in text else "stub answer"
        out: dict[str, Any] = {
            "id": "stub-chat",
            "object": "chat.completion",
            "created": 0,
            "model": "stub-llm",
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
            ],
        }
        if not self.omit_usage:
            out["usage"] = {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}
        return out

    def _embed(self, request: dict[str, Any]) -> dict[str, Any]:
        inputs = request["input"] if isinstance(request["input"], list) else [request["input"]]
        as_base64 = request.get("encoding_format") == "base64"
        data = []
        for i, text in enumerate(inputs):
            vec = stub_vector(text)
            embedding: Any = (
                base64.b64encode(struct.pack(f"<{len(vec)}f", *vec)).decode() if as_base64 else vec
            )
            data.append({"object": "embedding", "index": i, "embedding": embedding})
        out: dict[str, Any] = {"object": "list", "model": "stub-embed", "data": data}
        if not self.omit_usage:
            out["usage"] = {"prompt_tokens": 3 * len(inputs), "total_tokens": 3 * len(inputs)}
        return out

    def __enter__(self) -> StubModelServer:
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


_OVERLAY_KEYS = (
    "LLM_MODEL",
    "LLM_BINDING_API_KEY",
    "LLM_BINDING_HOST",
    "EMBEDDING_MODEL",
    "EMBEDDING_BINDING_HOST",
    "EMBEDDING_BINDING_API_KEY",
    "EMBEDDING_DIM",
    "EMBEDDING_USE_BASE64",
    "LIGHTRAG_KV_STORAGE",
    "LIGHTRAG_GRAPH_STORAGE",
    "LIGHTRAG_VECTOR_STORAGE",
    "LIGHTRAG_DOC_STATUS_STORAGE",
)


def _overlay_values(url: str) -> dict[str, str]:
    return {
        "LLM_MODEL": "stub-llm",
        "LLM_BINDING_API_KEY": "stub-local-key",
        "LLM_BINDING_HOST": url,
        "EMBEDDING_MODEL": "stub-embed",
        "EMBEDDING_BINDING_HOST": url,
        "EMBEDDING_BINDING_API_KEY": "stub-local-key",
        "EMBEDDING_DIM": str(EMBEDDING_DIM),
        "EMBEDDING_USE_BASE64": "false",
        "LIGHTRAG_KV_STORAGE": "JsonKVStorage",
        "LIGHTRAG_GRAPH_STORAGE": "CozoGraphStorage",
        "LIGHTRAG_VECTOR_STORAGE": "FaissVectorDBStorage",
        "LIGHTRAG_DOC_STATUS_STORAGE": "JsonDocStatusStorage",
    }


def write_env_overlay(
    path: Path, url: str, *, omit: tuple[str, ...] = (), blank: tuple[str, ...] = ()
) -> Path:
    """Write the stub env overlay. ``blank`` keys are written as ``KEY=`` (how a test makes a key
    missing: v1 loads ``v1/.env`` with ``override=False``, so an omitted key could still arrive
    from that file, while an empty process-env value is never overridden)."""
    values = _overlay_values(url)
    lines = []
    for key in _OVERLAY_KEYS:
        if key in omit:
            continue
        lines.append(f"{key}=" if key in blank else f"{key}={values[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def real_v1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    with StubModelServer() as server:
        overlay = write_env_overlay(tmp_path / "stub-v1.env", server.url)
        monkeypatch.setattr(v1_corpus_adapter, "DEFAULT_V1_ENV_PARITY", overlay)
        client_env = {
            key: value
            for key, value in _overlay_values(server.url).items()
            if key.startswith(("LLM_", "EMBEDDING_")) and key not in ("EMBEDDING_DIM", "EMBEDDING_USE_BASE64")
        }
        yield SimpleNamespace(store_root=tmp_path / "store", server=server, client_env=client_env, env_path=overlay)


__all__ = [
    "EMBEDDING_DIM",
    "StubModelServer",
    "real_v1",
    "requires_v1",
    "stub_vector",
    "write_env_overlay",
]

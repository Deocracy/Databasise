"""Shared probes for the Phase 9 seam tests (09-06-PLAN.md; 09-07 reuses them): counting stub
clients, the trace-row count and the corpus-inbox listing. A helper module, not collected by pytest.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise


class CountingEmbeddingClient:
    """Returns ``vector`` for every text and counts how often it was called."""

    def __init__(self, vector: list[float]):
        self.vector = vector
        self.calls = 0

    async def embed(self, texts, **kwargs):
        self.calls += 1
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class CountingLLMClient:
    """Returns a fixed completion and counts how often it was called."""

    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, messages, **kwargs):
        self.calls += 1
        return ChatResult(
            text="stub completion",
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


def counting_clients(vector: list[float]) -> dict[str, object]:
    return {"llm": CountingLLMClient(), "embedding": CountingEmbeddingClient(vector=vector)}


def trace_row_count(store_root: str | Path) -> int:
    """Number of rows in ``store_root/trace.db``'s ``traces`` table."""
    conn = sqlite3.connect(Path(store_root) / "trace.db")
    try:
        return conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
    finally:
        conn.close()


def inbox_files(store_root: str | Path) -> list[Path]:
    """Every file under ``store_root/corpus-inbox``; empty when the directory does not exist."""
    inbox = Path(store_root) / "corpus-inbox"
    return sorted(inbox.rglob("*")) if inbox.exists() else []


async def promote_alias(store_root: str | Path, alias: str, arm_name: str = "naive") -> None:
    """Promote ``alias`` to ``arm_name``'s wiring: seed a trace naming that arm, then promote
    through ``Databasise.promote`` (the call the REST and MCP routes make)."""
    # Imported here: test_rest_transport imports fastapi, which the rest of this module must not need.
    from databasise.tests.seam.test_rest_transport import _seed_trace

    token = _seed_trace(store_root, arm_name)
    await Databasise(store_root=store_root, workspace="probe-promote").promote(
        alias, [token], "human_edit"
    )

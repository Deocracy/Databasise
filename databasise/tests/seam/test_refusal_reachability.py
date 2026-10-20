"""WIRE-17 (13-07, D-11): where each partly reachable refusal occurs.

``MutableStoreComparisonExcludedError`` fires on ``compare`` for one selector as well as for two or
more (CONTRACT.md section 14.4 point 3: the mutates_store check runs before any node does), so a
single selector resolving a ``mutates_store`` wiring is refused instead of run. D-11's exception
clause: the refusal stays defined although no shipped wiring reaches it, so the ``cbm_reachable``
fixture below adds the committed ``codebase-memory-mcp`` wiring to the capability candidates for one
test only (a local copy of the fixture in ``test_mutable_store_exclusion.py``).

Every outcome is captured with ``try/except Exception`` and asserted by name, so a pre-fix run fails
by ``AssertionError`` rather than by an unrelated exception.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise, QueryObject
from databasise.seam import selectors as selectors_module
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.selectors import Selector

_CBM_WIRING_PATH = Path(__file__).resolve().parent.parent.parent / "wirings" / "codebase-memory-mcp.json"
_MUTATES_STORE_CAPABILITY = ["mutates_store"]
_LIGHTRAG_CAPABILITY = ["reads_vector"]
_HIPPORAG_CAPABILITY = ["reads_graph", "reads_kv"]


@pytest.fixture
def cbm_reachable(monkeypatch):
    """Adds the committed codebase-memory-mcp wiring to the capability selector's candidates."""
    cbm_resolved = json.loads(_CBM_WIRING_PATH.read_text(encoding="utf-8"))
    original_candidates = selectors_module._capability_candidates

    def _with_cbm() -> list[tuple[str, dict]]:
        return [*original_candidates(), ("codebase-memory-mcp", cbm_resolved)]

    monkeypatch.setattr(selectors_module, "_capability_candidates", _with_cbm)


def _trace_rows(store_root) -> int:
    """Rows in trace.db, 0 when no run ever created it."""
    db = Path(store_root) / "trace.db"
    if not db.exists():
        return 0
    conn = sqlite3.connect(db)
    try:
        return conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


async def _outcome(awaitable):
    """``(result, exception)`` of awaiting ``awaitable``; never raises."""
    try:
        return await awaitable, None
    except Exception as exc:  # noqa: BLE001 - the assertions name what was caught
        return None, exc


class _StubEmbeddingClient:
    def __init__(self, counted_by: str = "stub-embed"):
        self.counted_by = counted_by

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[[1.0, 0.0, 0.0] for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by=self.counted_by),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    def __init__(self, counted_by: str = "stub-llm"):
        self.counted_by = counted_by

    async def chat(self, messages, **kwargs):
        content = messages[0]["content"]
        if "---Candidate Facts---" in content:
            text = json.dumps({"keep_ids": []})
        elif "---Recognised Entities---" in content:
            text = json.dumps({"triples": [["Ed Wood", "directed", "films"]]})
        else:
            text = json.dumps({"entities": ["Ed Wood", "films"]})
        return ChatResult(
            text=text,
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by=self.counted_by),
            resolved_model_identity="stub-llm-model",
        )


def _engine(store_root, workspace: str, embedding=None, llm=None) -> Databasise:
    return Databasise(
        store_root=store_root,
        workspace=workspace,
        clients={"embedding": embedding or _StubEmbeddingClient(), "llm": llm or _StubLLMClient()},
    )


# --------------------------------------------------------------------------------------------- #
# compare with one selector (WIRE-17, D-11)
# --------------------------------------------------------------------------------------------- #


async def test_compare_with_one_mutating_selector_is_refused(cbm_reachable, store_root):
    engine = _engine(store_root, "reach-one-mutating")
    rows_before = _trace_rows(store_root)

    result, caught = await _outcome(
        engine.compare(QueryObject(text="x"), [Selector(capability=_MUTATES_STORE_CAPABILITY)])
    )

    assert type(caught).__name__ == "MutableStoreComparisonExcludedError", (type(caught), result)
    assert _trace_rows(store_root) == rows_before


async def test_compare_with_one_plain_selector_returns_a_bare_envelope(synthetic_naive_store):
    engine = _engine(synthetic_naive_store["store_root"], synthetic_naive_store["workspace"])

    result, caught = await _outcome(
        engine.compare(QueryObject(text="Which films?"), [Selector(capability=_LIGHTRAG_CAPABILITY)])
    )

    assert caught is None, caught
    assert isinstance(result, ResponseEnvelope)


async def test_compare_with_no_selector_is_still_refused(store_root):
    engine = _engine(store_root, "reach-empty")

    _result, caught = await _outcome(engine.compare(QueryObject(text="x"), []))

    assert type(caught).__name__ == "EmptyComparisonRequestError", caught

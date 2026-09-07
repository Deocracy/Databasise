"""04-05-PLAN.md Task 1 (+ Task 2): the optional REST transport (D-15/D-16/D-17, EMBED-02,
API-04, API-10, D-10). Task 1's tracer: an HTTP client posts a query object and receives the same
closed envelope an in-process caller receives, from a transport that holds no logic of its own —
proven behaviorally (the response's own answer/evidence fields carry real values written into the
test's own store fixture, never shape alone) and structurally (an AST walk over
`databasise/seam/rest.py`'s own source finds no call to the selector-resolution, redaction, or
envelope-assembly functions; a second AST walk over `databasise/__init__.py`/
`databasise/seam/__init__.py` finds no module-scope import reaching this optional module).

Task 2 extends this module with SSE streaming/non-streaming content equality, the four §18
operations' REST/in-process parity, the parametrized refusal-mapping proof (enumerated from
`SeamRefusalError`'s own subclass set, never a hand-maintained list), and the two-tier leak gate
run over a real REST response body.
"""

from __future__ import annotations

import ast
import inspect
import json

import pytest
from fastapi.testclient import TestClient

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import redact as redact_module
from databasise.seam import rest as rest_module
from databasise.seam import selectors as selectors_module
from databasise.seam.rest import create_app

_STUB_COMPLETION = "This is a stub completion for the REST transport's tracer test."


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


@pytest.fixture
def rest_app(synthetic_naive_store):
    return create_app(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=_stub_clients(synthetic_naive_store),
    )


@pytest.fixture
def client(rest_app):
    return TestClient(rest_app)


# --------------------------------------------------------------------------------------------- #
# Task 1: the tracer, and the two structural proofs (import guard, no-logic-in-the-transport).
# --------------------------------------------------------------------------------------------- #


def test_an_http_client_posts_a_query_and_receives_the_same_closed_envelope(client):
    response = client.post("/query", json={"query": {"text": "Which films did Ed Wood direct?"}})

    assert response.status_code == 200
    body = response.json()
    # Real values, never shape alone: the stub client's own configured completion text, and the
    # evidence reference id the test's own store fixture wrote in (databasise/tests/seam/conftest.py).
    assert body["answer"] == _STUB_COMPLETION
    assert [item["ref"] for item in body["evidence"]] == ["chunk-1"]


def test_databasise_and_databasise_seam_are_importable_with_no_web_framework_present():
    """AST walk over the source, not `sys.modules` manipulation (per the plan's own instruction)
    — the assertion is about what the module declares, not a fragile runtime state. Neither module
    may import the optional REST module at module scope, or a consumer without the `rest` extra
    installed gets a raw `ImportError` traceback the moment they `import databasise`."""
    import databasise
    import databasise.seam

    for module in (databasise, databasise.seam):
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "rest" not in alias.name.split("."), (
                        f"{module.__name__} imports {alias.name!r} at module scope"
                    )
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                assert "rest" not in module_name.split("."), (
                    f"{module.__name__} imports from {module_name!r} at module scope"
                )


def _called_names(source: str) -> set[str]:
    """Every function/method name a module's own source directly *calls* — never names merely
    referenced as a type annotation or imported for re-export (annotations/imports produce no
    `ast.Call` node)."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def test_rest_module_calls_no_selector_resolution_redaction_or_envelope_assembly_function():
    """D-17's structural half: `rest.py` may hold `Selector`/`ResponseEnvelope` as type
    annotations (it must, to deserialize/serialize) but must never itself *call* the functions
    that resolve a selector, redact a run record, or assemble an envelope — those calls happen
    exactly once, inside `databasise.seam.engine`. The forbidden name set is read off the
    producing modules' own `__all__`, never a hand-restated list, so a rename there cannot make
    this test silently stop checking anything."""
    called = _called_names(inspect.getsource(rest_module))

    forbidden = {"ResponseEnvelope"}
    forbidden.update(name for name in selectors_module.__all__ if name != "Selector")
    forbidden.update(redact_module.__all__)

    overlap = called & forbidden
    assert not overlap, f"databasise/seam/rest.py calls forbidden seam-logic function(s): {overlap}"

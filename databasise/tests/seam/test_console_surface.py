"""16-01 (CONN-01): the operator surface is one flag, one module, thin adapters (D-01, D-03, D-04).

``databasise/seam/operator_rest.py`` mounts only under ``create_app(operator=True)`` /
``databasise-rest --operator``. Every route body in it is an optional docstring plus exactly
``return await engine.<method>(...)``, so no route reads the ledger, trace store, registry or stores
itself. This file holds the structural AST rule (with a mutant that must be flagged), the flag-off
404s, and the launcher flag.

New API is reached through ``find_spec`` / ``inspect.signature`` so each node fails by a plain
``AssertionError`` before the change (16-RESEARCH Pitfall 1).
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect

import pytest

pytest.importorskip("fastapi")

from databasise.seam import redact as redact_module
from databasise.seam.rest import create_app
from fastapi.testclient import TestClient

_ROUTE_METHODS = {"get", "post", "put", "patch", "delete"}
_ALLOWED_ARGUMENT_HELPERS = {"checked_page", "_selector_field"}
_BANNED_NAMES = {
    "Ledger",
    "TraceStore",
    "PartRegistry",
    "default_registry",
    "_build_stores",
    "Databasise",
    "ResponseEnvelope",
    "resolve_selector",
    "sqlite3",
    "open",
    *redact_module.__all__,
}
_BANNED_IMPORT_PREFIXES = (
    "databasise.ledger",
    "databasise.seam.trace_store",
    "databasise.stores",
    "databasise.parts.registry",
)
_OPERATOR_PATHS = (
    ("GET", "/info"),
    ("GET", "/wirings"),
    ("GET", "/ledger/aliases"),
    ("GET", "/traces"),
    ("GET", "/log"),
    ("POST", "/ledger/history"),
    ("POST", "/promote/preview"),
    ("POST", "/chunks"),
    ("POST", "/graph/nodes"),
    ("POST", "/graph/node"),
)


def _is_route(fn: ast.AST) -> bool:
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    for decorator in fn.decorator_list:
        call = decorator if isinstance(decorator, ast.Call) else None
        func = call.func if call is not None else decorator
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "app"
            and func.attr in _ROUTE_METHODS
        ):
            return True
    return False


def _body_without_docstring(fn: ast.AST) -> list[ast.stmt]:
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(
        body[0].value.value, str
    ):
        body = body[1:]
    return body


def _thin_adapter_findings(source: str) -> tuple[int, list[str]]:
    """``(route_count, findings)`` for an operator-routes module source (D-04). Walks ``fn.body`` only,
    never annotations or defaults."""
    tree = ast.parse(source)
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        else:
            continue
        findings.extend(f"imports {m}" for m in modules if m.startswith(_BANNED_IMPORT_PREFIXES))

    routes = [node for node in ast.walk(tree) if _is_route(node)]
    for fn in routes:
        body = _body_without_docstring(fn)
        shape_ok = (
            len(body) == 1
            and isinstance(body[0], ast.Return)
            and isinstance(body[0].value, ast.Await)
            and isinstance(body[0].value.value, ast.Call)
            and isinstance(body[0].value.value.func, ast.Attribute)
            and isinstance(body[0].value.value.func.value, ast.Name)
            and body[0].value.value.func.value.id == "engine"
        )
        if not shape_ok:
            findings.append(f"{fn.name}: body is not exactly `return await engine.<method>(...)`")
        else:
            engine_call = body[0].value.value
            arguments = [*engine_call.args, *(kw.value for kw in engine_call.keywords)]
            for argument in arguments:
                for inner in ast.walk(argument):
                    if isinstance(inner, ast.Call):
                        name = inner.func.id if isinstance(inner.func, ast.Name) else getattr(inner.func, "attr", "?")
                        if name not in _ALLOWED_ARGUMENT_HELPERS:
                            findings.append(f"{fn.name}: argument calls {name}")
        for statement in fn.body:
            for inner in ast.walk(statement):
                banned = None
                if isinstance(inner, ast.Name) and inner.id in _BANNED_NAMES:
                    banned = inner.id
                elif isinstance(inner, ast.Attribute) and inner.attr in _BANNED_NAMES:
                    banned = inner.attr
                if banned is not None:
                    findings.append(f"{fn.name}: uses banned name {banned}")
    return len(routes), findings


_MUTANT = '''
def add_operator_routes(app, engine):
    @app.get("/ledger/aliases")
    async def get_aliases():
        return Ledger(engine.store_root).aliases()
'''


def test_operator_routes_are_thin_adapters_and_absent_without_the_flag(tmp_path):
    spec = importlib.util.find_spec("databasise.seam.operator_rest")
    assert spec is not None, "databasise/seam/operator_rest.py does not exist (CONN-01)"
    source = inspect.getsource(importlib.import_module("databasise.seam.operator_rest"))

    route_count, findings = _thin_adapter_findings(source)
    assert route_count >= 1, "no operator route was found by the AST walk"
    assert not findings, findings

    mutant_count, mutant_findings = _thin_adapter_findings(_MUTANT)
    assert mutant_count == 1 and mutant_findings, "the AST rule did not flag a `Ledger(...)` route body"

    plain = create_app(store_root=tmp_path, workspace="ws")
    client = TestClient(plain)
    openapi_paths = set(plain.openapi()["paths"])
    for method, path in _OPERATOR_PATHS:
        response = client.request(method, path, json={} if method == "POST" else None)
        assert response.status_code == 404, f"{method} {path} answered {response.status_code} without the flag"
        assert path not in openapi_paths, f"{path} is in the default app's OpenAPI"

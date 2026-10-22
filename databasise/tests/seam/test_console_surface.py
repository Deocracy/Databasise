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
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from databasise.launcher.serve_rest import build_app, build_parser, main
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


def _launcher_args(tmp_path, *extra):
    return build_parser().parse_args(["--no-clients", "--store-root", str(tmp_path), "--workspace", "ws", *extra])


def test_the_launcher_operator_flag_mounts_the_routes_only_when_given(tmp_path):
    assert "--operator" in build_parser().format_help(), "databasise-rest has no --operator flag (CONN-01)"
    with_flag = build_app(_launcher_args(tmp_path / "on", "--operator"), None)
    assert TestClient(with_flag, base_url="http://127.0.0.1").get("/info").status_code == 200
    without_flag = build_app(_launcher_args(tmp_path / "off"), None)
    assert TestClient(without_flag, base_url="http://127.0.0.1").get("/info").status_code == 404


_COVERAGE_MD = Path(__file__).resolve().parents[2] / "evidence" / "COVERAGE.md"
_ABSENT_HEADER = "| operation | decision | reason |"


def _absent_rows() -> list[list[str]]:
    """Rows of COVERAGE.md's 'Operations deliberately absent' table, parsed like the growth test does."""
    lines = _COVERAGE_MD.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().startswith(_ABSENT_HEADER))
    rows: list[list[str]] = []
    for line in lines[start + 2 :]:
        if not line.strip().startswith("|"):
            break
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


def test_every_operator_operation_has_a_rest_only_absent_row():
    from databasise.mcp.tools import TOOL_NAMES

    rows = _absent_rows()
    for method, path in _OPERATOR_PATHS:
        route = f"`{method} {path}`"
        matches = [row for row in rows if route in row[0]]
        assert len(matches) == 1, f"{route}: {len(matches)} absent-table rows, expected exactly one (D-03)"
        assert matches[0][1] == "REST-ONLY", f"{route}: decision is {matches[0][1]!r}, expected 'REST-ONLY'"
    assert len(TOOL_NAMES) == 10, f"the MCP tool set grew to {len(TOOL_NAMES)} names (D-03)"


def _route_pairs(app) -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in app.routes
        for method in (getattr(route, "methods", None) or ())
        if method not in {"HEAD", "OPTIONS"}
    }


def _operator_app(tmp_path, name: str, **extra):
    """An app built with ``operator=True`` under its own store root. The 'log_path' assert keeps a base
    without the parameter on AssertionError rather than TypeError."""
    if extra:
        assert "log_path" in inspect.signature(create_app).parameters, "create_app has no log_path (CONN-14)"
    return create_app(store_root=tmp_path / name, workspace="ws", operator=True, **extra)


def test_the_operator_app_mounts_exactly_the_operator_routes(tmp_path):
    default = _route_pairs(create_app(store_root=tmp_path / "default", workspace="ws"))
    assert not default & set(_OPERATOR_PATHS), "the default app mounts an operator route"

    ten = {(m, p) for m, p in _OPERATOR_PATHS}
    with_log = _route_pairs(_operator_app(tmp_path, "with_log", log_path=tmp_path / "server.log"))
    assert with_log - default == ten, sorted(with_log - default)

    without_log = _route_pairs(_operator_app(tmp_path, "without_log"))
    assert without_log - default == ten - {("GET", "/log")}, sorted(without_log - default)


def test_operator_with_a_remote_host_is_refused_before_the_store_lock(tmp_path, capsys):
    assert "--operator" in build_parser().format_help(), "databasise-rest has no --operator flag (CONN-01)"
    root = tmp_path / "root"
    caught: BaseException | None = None
    try:
        main([
            "--operator", "--host", "192.168.1.5", "--allow-remote-unauthenticated", "--no-clients",
            "--store-root", str(root),
        ])
    except BaseException as exc:  # SystemExit from parser.error
        caught = exc
    stderr = capsys.readouterr().err
    assert isinstance(caught, SystemExit) and caught.code == 2, caught
    assert "--operator" in stderr and "loopback" in stderr, stderr
    assert "unrecognized arguments" not in stderr, stderr
    assert not (root / ".engine.lock").exists(), "the store lock was taken before the refusal"

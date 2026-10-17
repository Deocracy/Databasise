"""08-08 security addendum: the unauthenticated seam refuses a non-loopback bind and rejects foreign
Host headers (DNS rebinding). Seam authentication itself stays an open owner decision.

No test binds a socket: refusal is checked through argument parsing, the REST app through
``TestClient``, and the MCP settings through the SDK's own request validator.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

_REMOTE_HOSTS = ["0.0.0.0", "192.168.1.5", "example.com", "::"]
_LOOPBACK_HOSTS = ["127.0.0.1", "127.5.5.5", "::1", "[::1]", "localhost"]


def _never_start(monkeypatch, module) -> None:
    """A refused launch must stop at argument validation: if it gets as far as opening the engine
    (lock, clients, socket), fail the test instead of binding anything."""

    def _opened(args):
        raise AssertionError("the launcher got past argument validation and opened the engine")

    monkeypatch.setattr(module, "open_engine", _opened)


def _argv(store_root, *flags: str) -> list[str]:
    return ["--store-root", str(store_root), "--workspace", "w", "--no-clients", *flags]


@pytest.mark.parametrize("host", _REMOTE_HOSTS)
def test_rest_refuses_a_non_loopback_host_with_exit_2(store_root, capsys, monkeypatch, host):
    from databasise.launcher import serve_rest

    _never_start(monkeypatch, serve_rest)
    with pytest.raises(SystemExit) as excinfo:
        serve_rest.main(_argv(store_root, "--host", host))

    err = capsys.readouterr().err
    assert excinfo.value.code == 2
    assert "no authentication" in err and "--allow-remote-unauthenticated" in err
    assert not (store_root / ".engine.lock").exists()


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "[::]", "0", "0.0", "", "::ffff:0.0.0.0"])
@pytest.mark.parametrize("launcher", ["serve_rest", "serve_mcp"])
def test_a_wildcard_bind_is_refused_even_with_the_flag(store_root, capsys, monkeypatch, launcher, host):
    import importlib

    module = importlib.import_module(f"databasise.launcher.{launcher}")
    _never_start(monkeypatch, module)
    extra = ["--transport", "sse"] if launcher == "serve_mcp" else []
    with pytest.raises(SystemExit) as excinfo:
        module.main(_argv(store_root, *extra, "--host", host, "--allow-remote-unauthenticated"))

    assert excinfo.value.code == 2
    assert "wildcard" in capsys.readouterr().err
    assert not (store_root / ".engine.lock").exists()


@pytest.mark.parametrize("transport", ["sse", "streamable-http"])
def test_mcp_http_transports_refuse_a_non_loopback_host_with_exit_2(
    store_root, capsys, monkeypatch, transport
):
    from databasise.launcher import serve_mcp

    _never_start(monkeypatch, serve_mcp)
    with pytest.raises(SystemExit) as excinfo:
        serve_mcp.main(_argv(store_root, "--transport", transport, "--host", "0.0.0.0"))

    assert excinfo.value.code == 2
    assert "no authentication" in capsys.readouterr().err
    assert not (store_root / ".engine.lock").exists()


def test_mcp_stdio_opens_no_port_so_any_host_value_passes_validation(store_root):
    from databasise.launcher import check_engine_arguments, serve_mcp

    parser = serve_mcp.build_parser()
    args = parser.parse_args(_argv(store_root, "--transport", "stdio", "--host", "0.0.0.0"))

    check_engine_arguments(parser, args)


@pytest.mark.parametrize("host", _LOOPBACK_HOSTS)
def test_loopback_hosts_pass_validation(store_root, host):
    from databasise.launcher import check_engine_arguments, serve_rest

    parser = serve_rest.build_parser()

    check_engine_arguments(parser, parser.parse_args(_argv(store_root, "--host", host)))


@pytest.mark.parametrize("host", ["192.168.1.5", "example.com"])
def test_the_flag_lets_a_non_loopback_host_pass_validation(store_root, host):
    from databasise.launcher import check_engine_arguments, serve_rest

    parser = serve_rest.build_parser()
    args = parser.parse_args(_argv(store_root, "--host", host, "--allow-remote-unauthenticated"))

    check_engine_arguments(parser, args)


def _rest_client(store_root, monkeypatch, *flags: str) -> TestClient:
    from databasise.launcher import serve_rest
    from databasise.tests.seam.test_rest_cors import _patch_health

    _patch_health(monkeypatch)
    args = serve_rest.build_parser().parse_args(_argv(store_root, *flags))
    return TestClient(serve_rest.build_app(args, None))


def test_the_launcher_built_rest_app_rejects_a_foreign_host_header(store_root, monkeypatch):
    client = _rest_client(store_root, monkeypatch)

    response = client.get("/health", headers={"Host": "evil.example"})

    assert response.status_code == 400


@pytest.mark.parametrize("host_header", ["127.0.0.1:8000", "localhost:8000", "[::1]:8000", "127.0.0.1"])
def test_the_launcher_built_rest_app_accepts_loopback_host_headers(store_root, monkeypatch, host_header):
    client = _rest_client(store_root, monkeypatch)

    response = client.get("/health", headers={"Host": host_header})

    assert response.status_code == 200


def test_the_bound_remote_host_is_allowed_and_a_foreign_one_is_not(store_root, monkeypatch):
    client = _rest_client(
        store_root, monkeypatch, "--host", "192.168.1.5", "--allow-remote-unauthenticated"
    )

    assert client.get("/health", headers={"Host": "192.168.1.5:8000"}).status_code == 200
    assert client.get("/health", headers={"Host": "evil.example"}).status_code == 400


def _upload(client, origin: str | None):
    headers = {"Host": "127.0.0.1:8000", **({"Origin": origin} if origin else {})}
    return client.post(
        "/documents/upload",
        files={"file": ("report.pdf", b"raw pdf bytes", "application/pdf")},
        headers=headers,
    )


def test_a_cross_site_write_is_refused_whether_or_not_cors_is_configured(store_root, monkeypatch):
    for flags in ((), ("--cors-origin", "http://localhost:5173")):
        client = _rest_client(store_root, monkeypatch, *flags)

        response = _upload(client, "http://evil.example")

        assert response.status_code == 403
        assert response.json() == {"detail": "origin not allowed"}
        assert client.get("/jobs/x", headers={"Origin": "http://evil.example"}).status_code != 403


def test_writes_with_no_origin_a_loopback_origin_or_a_listed_origin_pass_the_guard(store_root, monkeypatch):
    client = _rest_client(store_root, monkeypatch, "--cors-origin", "http://localhost:5173")

    for origin in (None, "http://127.0.0.1:8000", "http://localhost:8000", "http://localhost:5173"):
        assert _upload(client, origin).status_code != 403
    assert _upload(client, "http://127.0.0.1:9999").status_code == 403


def test_create_app_itself_keeps_accepting_any_host(store_root, monkeypatch):
    from databasise.seam.rest import create_app
    from databasise.tests.seam.test_rest_cors import _patch_health

    _patch_health(monkeypatch)

    response = TestClient(create_app(store_root=store_root, workspace="w")).get("/health")

    assert response.status_code == 200


def _mcp_validate(settings, *, host: str, origin: str | None = None) -> int | None:
    import anyio
    from databasise.foreign._mcp_sdk_guard import import_real_mcp
    from starlette.requests import Request

    security = import_real_mcp("mcp.server.transport_security").TransportSecurityMiddleware(settings)
    headers = [(b"host", host.encode())]
    if origin is not None:
        headers.append((b"origin", origin.encode()))
    request = Request({"type": "http", "method": "GET", "headers": headers})
    response = anyio.run(security.validate_request, request)
    return None if response is None else response.status_code


def test_mcp_transport_security_enables_dns_rebinding_protection_for_loopback(store_root):
    from databasise.launcher import serve_mcp

    args = serve_mcp.build_parser().parse_args(_argv(store_root, "--transport", "streamable-http"))
    settings = serve_mcp.build_transport_security(args)

    assert settings.enable_dns_rebinding_protection is True
    for host in ("127.0.0.1:8001", "localhost:8001", "[::1]:8001"):
        assert _mcp_validate(settings, host=host) is None
    assert _mcp_validate(settings, host="evil.example") == 421
    assert _mcp_validate(settings, host="evil.example:8001") == 421
    assert _mcp_validate(settings, host="127.0.0.1:8001", origin="http://localhost:5173") is None
    assert _mcp_validate(settings, host="127.0.0.1:8001", origin="http://evil.example") == 403


def test_mcp_transport_security_allows_the_bound_remote_host(store_root):
    from databasise.launcher import serve_mcp

    args = serve_mcp.build_parser().parse_args(
        _argv(
            store_root,
            "--transport", "sse",
            "--host", "192.168.1.5",
            "--allow-remote-unauthenticated",
        )  # fmt: skip
    )
    settings = serve_mcp.build_transport_security(args)

    assert _mcp_validate(settings, host="192.168.1.5:8001") is None
    assert _mcp_validate(settings, host="evil.example") == 421

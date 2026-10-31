"""LIVE-01 (D-01, D-02, D-03): the launcher serves the built console same-origin at GET /console.

The row test is the page fetch: a POST /query from the console page returns 200 with no CORS or
Access-Control console message. The remaining tests check the server side: the security headers and
their sha256 hash sources, the route absent without ``--console``, an unchanged ``/openapi.json``, the
loopback-host and fixed-port refusals, ``--console`` not implying ``--operator``, an injected inline
script that Chromium does not run, and the wheel contents. Uses the in-process harness in
``conftest.py``; no test here uses the live marker.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.resources
import re

import pytest
from fastapi.testclient import TestClient

from databasise.launcher import serve_rest
from databasise.tests.gui_live.conftest import open_live_ui
from databasise.tests.test_packaging import _before_build, _dist_info_text, built_wheel  # noqa: F401

QUERY_WORD = "Wood"  # a word of the seeded HippoRAG document text

_FETCH_QUERY = """async (body) => {
  const res = await fetch("/query", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  return res.status;
}"""


def _packaged_page() -> bytes:
    return importlib.resources.files("databasise.console").joinpath("operator-console.html").read_bytes()


def _hash_source(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode() + "'"


def _directives(policy: str) -> dict[str, str]:
    return {d.split(None, 1)[0]: d.split(None, 1)[1] for d in (p.strip() for p in policy.split(";")) if " " in d}


def _client(tmp_path, name: str, *flags: str) -> TestClient:
    argv = ["--store-root", str(tmp_path / name), "--workspace", "ws", "--no-clients", *flags]
    app = serve_rest.build_app(serve_rest.build_parser().parse_args(argv), None)
    return TestClient(app, base_url="http://127.0.0.1:8000")  # TrustedHost rejects the default "testserver"


def test_page_fetch_post_query_returns_200_without_cors_errors(seeded, live_ui):
    body = {"query": {"text": QUERY_WORD}, "selector": {"capability": ["reads_graph", "reads_kv"]}}
    status = live_ui.page.evaluate(_FETCH_QUERY, body)
    assert status == 200
    assert live_ui.cors_messages() == []


def test_console_route_serves_the_packaged_file_with_security_headers(live_app):
    response = live_app.http.get("/console")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.content == _packaged_page()
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    directives = _directives(response.headers["content-security-policy"])
    assert directives["default-src"] == "'none'"
    assert directives["img-src"] == "'self' data:"
    assert directives["connect-src"] == "'self'"
    assert directives["base-uri"] == "'none'"
    assert directives["form-action"] == "'none'"
    assert directives["frame-ancestors"] == "'none'"


def test_console_route_is_absent_without_the_flag(tmp_path):
    assert _client(tmp_path, "plain").get("/console").status_code == 404


def test_openapi_is_identical_with_and_without_the_flag(tmp_path):
    plain = _client(tmp_path, "plain", "--operator").get("/openapi.json")
    console = _client(tmp_path, "console", "--operator", "--console").get("/openapi.json")
    assert plain.status_code == console.status_code == 200
    assert plain.json() == console.json()
    assert "/console" not in console.json()["paths"]


def test_console_does_not_imply_operator(tmp_path):
    client = _client(tmp_path, "console", "--console")
    assert client.get("/console").status_code == 200
    assert client.get("/info").status_code == 404


def test_console_needs_a_loopback_host(tmp_path, capsys):
    with pytest.raises(SystemExit) as caught:
        serve_rest.main([
            "--console", "--host", "192.168.1.5", "--allow-remote-unauthenticated", "--no-clients",
            "--store-root", str(tmp_path),
        ])
    stderr = capsys.readouterr().err
    assert caught.value.code == 2
    assert "--console" in stderr and "loopback" in stderr, stderr
    assert not (tmp_path / ".engine.lock").exists(), "the store lock was taken before the refusal"


def test_console_needs_a_fixed_port(tmp_path, capsys):
    with pytest.raises(SystemExit) as caught:
        serve_rest.main(["--console", "--port", "0", "--no-clients", "--store-root", str(tmp_path)])
    stderr = capsys.readouterr().err
    assert caught.value.code == 2
    assert "fixed --port" in stderr, stderr
    assert not (tmp_path / ".engine.lock").exists(), "the store lock was taken before the refusal"


def test_csp_hashes_match_the_served_blocks(live_app):
    response = live_app.http.get("/console")
    body = response.text
    scripts = [
        text for attrs, text in re.findall(r"<script([^>]*)>(.*?)</script>", body, re.S) if "type=" not in attrs
    ]
    styles = re.findall(r"<style[^>]*>(.*?)</style>", body, re.S)
    assert len(scripts) == 1 and len(styles) == 1
    policy = response.headers["content-security-policy"]
    directives = _directives(policy)
    assert directives["script-src"] == _hash_source(scripts[0])
    assert directives["style-src"] == _hash_source(styles[0])
    assert "'unsafe-inline'" not in policy


def test_an_injected_inline_script_is_blocked(live_app, browser):
    def inject(page):
        def handler(route):
            response = route.fetch()
            head, tail = response.text().rsplit("</body>", 1)
            route.fulfill(response=response, body=head + "<script>window.__injected = 1</script></body>" + tail)

        page.route("**/console", handler)

    ui = open_live_ui(browser, live_app, before_goto=inject)
    try:
        assert ui.page.evaluate("typeof window.__injected") == "undefined"
        assert ui.page.evaluate("typeof window.Console") == "object"
        for _ in range(100):  # the violation message can arrive after load
            if any("Content Security Policy" in message for message in ui.console):
                break
            ui.page.wait_for_timeout(50)
        assert any("Content Security Policy" in message for message in ui.console), ui.console
    finally:
        ui.close()


def test_console_csp_refuses_a_page_with_two_scripts():
    two_scripts = b"<style>a{}</style><script>1</script><script>2</script>"
    no_style = b"<script>1</script>"
    with pytest.raises(RuntimeError):
        serve_rest.console_csp(two_scripts)
    with pytest.raises(RuntimeError):
        serve_rest.console_csp(no_style)
    data_block = b'<style>a{}</style><script type="application/json" id="d">{}</script><script>1</script>'
    assert "script-src" in serve_rest.console_csp(data_block)


def test_the_wheel_ships_the_built_console(built_wheel):
    recorded = {line.split(",", 1)[0] for line in _dist_info_text(built_wheel, "RECORD").splitlines()}
    assert "databasise/console/operator-console.html" in recorded
    assert [name for name in recorded if name.startswith("databasise/console/src/")] == []

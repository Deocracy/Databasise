"""Sweep fix (phase 08): ``--port`` outside 0..65535 is refused at parse time (exit 2), before the
store lock is taken; uvicorn would otherwise raise OverflowError after the engine is up.
"""

from __future__ import annotations

import importlib

import pytest


def _never_start(monkeypatch, module) -> None:
    def _opened(args):
        raise AssertionError("the launcher got past argument validation and opened the engine")

    monkeypatch.setattr(module, "open_engine", _opened)


def _argv(store_root, *flags: str) -> list[str]:
    return ["--store-root", str(store_root), "--workspace", "w", "--no-clients", *flags]


@pytest.mark.parametrize("port", ["70000", "-1", "65536"])
@pytest.mark.parametrize("launcher", ["serve_rest", "serve_mcp"])
def test_an_out_of_range_port_exits_2_before_the_lock(store_root, capsys, monkeypatch, launcher, port):
    module = importlib.import_module(f"databasise.launcher.{launcher}")
    _never_start(monkeypatch, module)
    extra = ["--transport", "sse"] if launcher == "serve_mcp" else []
    with pytest.raises(SystemExit) as excinfo:
        module.main(_argv(store_root, *extra, "--port", port))

    assert excinfo.value.code == 2
    assert "--port" in capsys.readouterr().err
    assert not (store_root / ".engine.lock").exists()


@pytest.mark.parametrize("port", ["8000", "0"])
def test_ports_in_range_parse(store_root, port):
    from databasise.launcher import serve_rest

    args = serve_rest.build_parser().parse_args(_argv(store_root, "--port", port))

    assert args.port == int(port)

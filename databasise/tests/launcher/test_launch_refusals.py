"""WR-02 (08 review): configuration errors are clean one-line refusals, not tracebacks.

Everything runs in-process through ``main()``; every refusal happens before a socket is bound.
"""

from __future__ import annotations

import pytest

_ENV = (
    "LLM_BINDING_HOST=http://llm.invalid\nLLM_MODEL=m\nLLM_BINDING_API_KEY=k1\n"
    "EMBEDDING_BINDING_HOST=http://emb.invalid\nEMBEDDING_MODEL=e\nEMBEDDING_BINDING_API_KEY=k2\n"
)
_RERANK = "RERANK_BINDING_HOST=http://rr.invalid\nRERANK_MODEL=r\nRERANK_BINDING_API_KEY=k3\n"


def _launch(module, store_root, env_file) -> int:
    return module.main(["--store-root", str(store_root), "--workspace", "w", "--env-file", str(env_file)])


@pytest.mark.parametrize("module_name", ["serve_rest", "serve_mcp"])
def test_an_unsupported_rerank_binding_is_a_clean_refusal(module_name, store_root, tmp_path, capsys):
    import importlib

    module = importlib.import_module(f"databasise.launcher.{module_name}")
    env_file = tmp_path / "env"
    env_file.write_text(_ENV + _RERANK + "RERANK_BINDING=bogus-marker\n", encoding="utf-8")

    assert _launch(module, store_root, env_file) == 1

    err = capsys.readouterr().err
    assert err.startswith("databasise: ") and "RERANK_BINDING" in err and "bogus-marker" not in err


def test_an_unreadable_env_file_is_a_clean_refusal(store_root, tmp_path, capsys):
    from databasise.launcher import serve_rest

    assert _launch(serve_rest, store_root, tmp_path) == 1  # a directory: IsADirectoryError
    assert capsys.readouterr().err.startswith("databasise: ")


def test_a_non_utf8_env_file_is_refused_without_quoting_its_bytes(store_root, tmp_path, capsys):
    from databasise.launcher import serve_rest

    env_file = tmp_path / "env"
    env_file.write_bytes(b"LLM_MODEL=\xff\xfe\n")

    assert _launch(serve_rest, store_root, env_file) == 1

    err = capsys.readouterr().err
    assert "UTF-8" in err and "0xff" not in err


def test_the_rerank_binding_match_is_case_insensitive():
    from databasise.clients.builder import build_clients

    env = {
        **dict(line.split("=", 1) for line in (_ENV + _RERANK).splitlines()),
        "RERANK_BINDING": " Cohere ",
    }

    assert "rerank" in build_clients(env)


@pytest.mark.parametrize("module_name", ["run_arm", "storage_audit"])
def test_parity_clis_refuse_a_bad_rerank_config_instead_of_raising(
    module_name, tmp_path, monkeypatch, capsys
):
    import importlib

    from databasise.clients.builder import (
        MissingParityEnvKeyError,
        UnsupportedRerankBindingError,
    )
    from databasise.parity import import_index

    module = importlib.import_module(f"databasise.parity.{module_name}")
    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", tmp_path / "store")
    argv = ["--arm", "naive", "--query", "q"] if module_name == "run_arm" else ["--arm", "naive"]

    for error in (UnsupportedRerankBindingError("RERANK_BINDING"), MissingParityEnvKeyError(["RERANK_MODEL"])):

        def _raise(*_args, _error=error, **_kwargs):
            raise _error

        monkeypatch.setattr(module, "run_arm" if module_name == "run_arm" else "run_audit", _raise)

        assert module.main(argv) == 1
        assert "RERANK" in capsys.readouterr().err

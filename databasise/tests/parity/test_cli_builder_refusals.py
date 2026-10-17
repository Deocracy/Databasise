"""WR-02 (08 review, iteration 2): every CLI that builds clients turns a builder refusal into a named,
non-zero exit instead of a traceback. The env file is a stub in ``tmp_path``; no real env file is read."""

from __future__ import annotations

import importlib

import pytest

from databasise.parity import import_index, run_arm

_ENV = (
    "LLM_BINDING_HOST=http://llm.invalid\nLLM_MODEL=m\nLLM_BINDING_API_KEY=k1\n"
    "EMBEDDING_BINDING_HOST=http://emb.invalid\nEMBEDDING_MODEL=e\nEMBEDDING_BINDING_API_KEY=k2\n"
    "RERANK_BINDING_HOST=http://rr.invalid\nRERANK_MODEL=r\nRERANK_BINDING_API_KEY=k3\n"
    "RERANK_BINDING=bogus-marker\n"
)

_CASES = [
    ("databasise.parity.run_arm", ["--arm", "naive", "--query", "q"], {}),
    ("databasise.parity.storage_audit", ["--arm", "naive"], {}),
    (
        "databasise.parity.run_cross_modality",
        [],
        {"preflight": lambda *a, **k: None},
    ),
    ("databasise.parity.build_hipporag_index", [], {}),
    ("databasise.eval.aa_run", ["--spend"], {}),
    ("databasise.eval.corpus_ingest", ["--limit", "1", "--spend"], {}),
    ("databasise.eval.remint", [], {}),
]


@pytest.mark.parametrize(("module_name", "argv", "patches"), _CASES, ids=[c[0].rsplit(".", 1)[1] for c in _CASES])
def test_a_bad_rerank_binding_is_a_named_refusal_not_a_traceback(
    module_name, argv, patches, tmp_path, monkeypatch, capsys
):
    module = importlib.import_module(module_name)
    env_file = tmp_path / "env"
    env_file.write_text(_ENV, encoding="utf-8")
    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", tmp_path / "store")
    monkeypatch.setattr(run_arm, "DEFAULT_V1_ENV_PARITY", env_file)  # storage_audit reads it off run_arm
    # run_arm and storage_audit open the real store (a RocksDB lock) before building clients; stub it.
    monkeypatch.setattr(run_arm, "_build_stores", lambda *a, **k: {})
    if hasattr(module, "DEFAULT_V1_ENV_PARITY"):
        monkeypatch.setattr(module, "DEFAULT_V1_ENV_PARITY", env_file)
    for name, stub in patches.items():
        monkeypatch.setattr(module, name, stub)

    assert module.main(argv) != 0

    err = capsys.readouterr().err
    assert "RERANK_BINDING" in err and "bogus-marker" not in err and "Traceback" not in err

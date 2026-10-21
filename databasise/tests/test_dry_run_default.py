"""TOOL-05 (D-04): every offline CLI that can spend is estimate-only unless it is given ``--spend``.

A bare call returns 0, prints ``mode: estimate-only``, builds no client, takes no lock, launches nothing
and writes nothing. The TOOL-05 row text names ``build_hipporag_index`` and ``remint``; D-04 reads it as
covering every spending CLI, so the table below lists all nine.

The HippoRAG build cases from the same row sit at the bottom: ``--spend`` on an empty store root builds,
and a build whose chunk embedder writes nothing raises the named post-build error.

Fail-first (D-22): the file imports only stdlib and pytest at module level and resolves everything else
inside the tests; every outcome (argparse's SystemExit included) is captured and asserted on. No test
reads a real env file (D-24): an autouse fixture points every module's ``DEFAULT_V1_ENV_PARITY`` at an
absent temp path, and each ``--spend`` case stubs the loader and the clients.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import subprocess

import pytest

_ENV_MODULES = (
    "databasise.parity.run_arm",
    "databasise.parity.build_hipporag_index",
    "databasise.parity.storage_audit",
    "databasise.parity.run_comparison",
    "databasise.parity.run_cross_modality",
    "databasise.parity.v1_arm",
    "databasise.foreign.v1_corpus_adapter",
    "databasise.eval.remint",
    "databasise.eval.corpus_ingest",
    "databasise.eval.aa_run",
)

# (module, argv without --spend)
_CLIS = [
    pytest.param("databasise.parity.build_hipporag_index", [], id="build_hipporag_index"),
    pytest.param("databasise.eval.remint", [], id="remint"),
    pytest.param("databasise.parity.run_arm", ["--arm", "naive", "--query", "q"], id="run_arm"),
    pytest.param("databasise.parity.storage_audit", ["--arm", "naive"], id="storage_audit"),
    pytest.param("databasise.parity.run_comparison", ["--arm", "naive"], id="run_comparison"),
    pytest.param("databasise.parity.run_cross_modality", [], id="run_cross_modality"),
    pytest.param("databasise.parity.v1_arm", ["--mode", "naive", "--query", "q"], id="v1_arm"),
    pytest.param("databasise.eval.corpus_ingest", ["--limit", "1"], id="corpus_ingest"),
    pytest.param("databasise.eval.aa_run", ["--split", "dev"], id="aa_run"),
]

# Everything a spending path calls: env loaders, client builders, locks, the work functions, engines.
_FORBIDDEN = (
    "store_lock",
    "acquire_store_lock",
    "_load_env_file",
    "load_env_file",
    "_build_clients",
    "build_clients",
    "build_index",
    "remint",
    "resolve_judge_identity",
    "run_arm",
    "run_audit",
    "_run_cli",
    "compare_arm_on_query",
    "run_cross_modality",
    "run_v1_arm",
    "ingest_documents",
    "calibrate_family",
    "Databasise",
    "MultiNamespaceVectorStore",
)


@pytest.fixture(autouse=True)
def _no_real_env_file(tmp_path, monkeypatch):
    """D-24: no case here can open the real ``v1/.env.parity``."""
    absent = tmp_path / "absent.env.parity"
    for name in _ENV_MODULES:
        module = importlib.import_module(name)
        if hasattr(module, "DEFAULT_V1_ENV_PARITY"):
            monkeypatch.setattr(module, "DEFAULT_V1_ENV_PARITY", absent)
    return absent


def _tree(path):
    return sorted(str(p.relative_to(path)) for p in path.rglob("*"))


@pytest.mark.parametrize(("module_name", "argv"), _CLIS)
def test_a_call_without_spend_is_estimate_only(module_name, argv, tmp_path, monkeypatch, capsys):
    module = importlib.import_module(module_name)
    import_index = importlib.import_module("databasise.parity.import_index")
    store_lock_module = importlib.import_module("databasise.store_lock")

    calls: list[str] = []

    def _counting_fake(label):
        def _fake(*_args, **_kwargs):
            calls.append(label)
            raise AssertionError(f"{label} was reached without --spend")

        return _fake

    # Every store root and results directory points into tmp_path; none of them is created here.
    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", tmp_path / "store")
    for owner in (module, importlib.import_module("databasise.eval.corpus_ingest")):
        for attr in ("DEFAULT_STORE_ROOT", "_EVAL_INGEST_STORE_ROOT"):
            if hasattr(owner, attr):
                monkeypatch.setattr(owner, attr, tmp_path / "store")
    if hasattr(module, "_RESULTS_DIR"):
        monkeypatch.setattr(module, "_RESULTS_DIR", tmp_path / "results")

    for owner in (module, store_lock_module):
        for name in _FORBIDDEN:
            if hasattr(owner, name) and not inspect.ismodule(getattr(owner, name)):
                monkeypatch.setattr(owner, name, _counting_fake(f"{owner.__name__.rsplit('.', 1)[1]}.{name}"))
    monkeypatch.setattr(subprocess, "run", _counting_fake("subprocess.run"))

    before = _tree(tmp_path)
    caught = None
    returncode = None
    try:
        returncode = module.main(list(argv))
    except BaseException as exc:  # noqa: BLE001 - argparse raises SystemExit; a forbidden fake raises AssertionError
        caught = exc

    captured = capsys.readouterr()
    assert caught is None, f"{module_name}.main({argv}) raised {caught!r}; stderr: {captured.err!r}"
    assert returncode == 0, (returncode, captured.err)
    assert "mode: estimate-only" in captured.out.splitlines(), captured.out
    assert calls == [], calls
    assert _tree(tmp_path) == before


# --------------------------------------------------------------------------------------------- #
# build_hipporag_index: --spend builds on an empty store root; a short chunk namespace is refused.
# --------------------------------------------------------------------------------------------- #


def _synthetic_snapshot():
    from databasise.parity.corpus import CorpusDocument, CorpusSnapshot

    texts = (
        "Ed Wood directed several low-budget films in the 1950s.",
        "Bela Lugosi starred in many of Ed Wood's films.",
        "Plan 9 from Outer Space is one of Ed Wood's best-known films.",
    )
    documents = tuple(
        CorpusDocument(id=f"synth-doc-{i}", title=f"Synthetic Doc {i}", text=text, sha256=f"synthetic-sha-{i}")
        for i, text in enumerate(texts, start=1)
    )
    return CorpusSnapshot(
        documents=documents,
        queries=(),
        corpus_hash="synthetic-corpus-hash",
        queries_hash="synthetic-queries-hash",
        source={"kind": "15-18 synthetic test fixture"},
    )


def _stub_clients():
    from databasise.clients.base import ChatResult, EmbeddingResult
    from databasise.runner.trace import TokenAccounting

    class _Embedding:
        async def embed(self, texts, **kwargs):
            assert texts and all(str(text).strip() for text in texts), texts
            return EmbeddingResult(
                vectors=[[1.0, 0.0, 0.0, 0.0] for _ in texts],
                tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed@1"),
                resolved_model_identity="stub-embed@1",
            )

    class _OpenIE:
        async def chat(self, messages, **kwargs):
            if "---Recognised Entities---" in messages[0]["content"]:
                text = json.dumps({"triples": [["Ed Wood", "directed", "films"]]})
            else:
                text = json.dumps({"entities": ["Ed Wood", "films"]})
            return ChatResult(
                text=text,
                tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm@1"),
                resolved_model_identity="stub-llm@1",
            )

    return {"embedding": _Embedding(), "llm": _OpenIE()}


def test_build_hipporag_index_spend_builds_on_an_empty_store_root(tmp_path, monkeypatch, capsys):
    build = importlib.import_module("databasise.parity.build_hipporag_index")
    import_index = importlib.import_module("databasise.parity.import_index")
    store_root = tmp_path / "store"
    store_root.mkdir()
    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", store_root)
    monkeypatch.setattr(build, "load_snapshot", _synthetic_snapshot)
    monkeypatch.setattr(import_index, "load_snapshot", _synthetic_snapshot)
    clients = _stub_clients()
    monkeypatch.setattr(build, "_load_env_file", lambda path: {})
    monkeypatch.setattr(build, "_build_clients", lambda env: clients)

    caught = None
    returncode = None
    try:
        returncode = build.main(["--spend"])
    except BaseException as exc:  # noqa: BLE001
        caught = exc

    captured = capsys.readouterr()
    assert caught is None, f"main(['--spend']) raised {caught!r}"
    assert returncode == 0, captured.err
    assert (store_root / import_index._import_workspace()).is_dir()


def test_build_hipporag_index_refuses_an_empty_chunk_namespace_by_name(tmp_path, monkeypatch):
    build = importlib.import_module("databasise.parity.build_hipporag_index")
    registry_module = importlib.import_module("databasise.parts.registry")
    chunk_embed = importlib.import_module("databasise.parts_core.hipporag.chunk_embed")

    monkeypatch.setattr(build, "load_snapshot", _synthetic_snapshot)

    async def _chunk_embed_that_writes_nothing(ctx):
        records = [
            {
                "chunk_id": f"{doc['document_id']}:{ordinal}",
                "document_id": doc["document_id"],
                "ordinal": ordinal,
                "text": piece,
            }
            for doc in ctx.config.get("documents") or []
            for ordinal, piece in enumerate(chunk_embed._split_into_chunks(doc["text"], 1200, 100))
        ]
        return {"chunks": records}

    registry = registry_module.default_registry()
    # The Part objects are shared module-level singletons: monkeypatch restores the real body.
    monkeypatch.setattr(registry.get("hipporag/chunker-embedder@0.1.0"), "body", _chunk_embed_that_writes_nothing)

    caught = None
    try:
        asyncio.run(build.build_index(registry=registry, clients=_stub_clients(), store_root=tmp_path, workspace="w"))
    except BaseException as exc:  # noqa: BLE001
        caught = exc

    assert caught is not None, "a build with no chunk vectors was reported as built"
    assert type(caught).__name__ == "ChunkCountMismatchError", repr(caught)
    assert (getattr(caught, "found", None), getattr(caught, "expected", None)) == (0, 3)

"""Phase 15 review-fix checks for the eval CLIs (15-REVIEW.md, lane A findings)."""

from __future__ import annotations

import asyncio

import pytest

from databasise import cli
from databasise.clients.openai_compat import (
    EmbeddingBatchMismatchError,
    EmptyChoicesError,
    MissingCompletionContentError,
    ModelIdentityMissingError,
)
from databasise.clients.rerank import RerankResponseError
from databasise.eval import corpus_ingest, remint
from databasise.parity.corpus import load_snapshot
from databasise.stores.vector import VectorStoreCorruptedError


def test_offline_refusals_cover_client_and_vector_store_refusals():
    """A-WR-01 (with B-WR-05): the shared D-03 tuple names the client and store refusals."""
    refusals = cli.offline_refusals()
    for cls in (
        ModelIdentityMissingError,
        EmptyChoicesError,
        MissingCompletionContentError,
        EmbeddingBatchMismatchError,
        RerankResponseError,
        VectorStoreCorruptedError,
    ):
        assert cls in refusals


class _ChatRaises:
    def __init__(self, exc):
        self._exc = exc

    async def chat(self, messages):
        raise self._exc


def test_resolve_judge_identity_maps_a_model_less_response_to_its_own_refusal():
    """A-WR-01: UnresolvedJudgeIdentityError is reachable with the real client's refusal."""
    with pytest.raises(remint.UnresolvedJudgeIdentityError):
        asyncio.run(remint.resolve_judge_identity(_ChatRaises(ModelIdentityMissingError("m"))))


def test_remint_spend_client_refusal_is_one_line_and_exit_1(monkeypatch, capsys):
    """A-WR-01: a client refusal on the probe call is the D-03 single line, not a traceback."""
    monkeypatch.setattr(remint, "_load_env_file", lambda path: {})
    monkeypatch.setattr(
        remint, "_build_clients", lambda env: {"llm": _ChatRaises(MissingCompletionContentError("m", "length"))}
    )
    assert remint.main(["--spend"]) == 1
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert err_lines[0].startswith("MissingCompletionContentError: ")


@pytest.mark.parametrize("module_name", ["corpus_ingest", "aa_run"])
def test_eval_spend_paths_take_the_store_lock(module_name, tmp_path, monkeypatch, capsys):
    """A-WR-07: a --spend run on a held eval store root refuses with StoreLockedError and writes nothing."""
    from databasise.eval import aa_run
    from databasise.store_lock import store_lock

    module = {"corpus_ingest": corpus_ingest, "aa_run": aa_run}[module_name]
    root = tmp_path / "eval-store"
    monkeypatch.setattr(module, "_EVAL_INGEST_STORE_ROOT", root)
    monkeypatch.setattr(module, "_load_env_file", lambda path: {})
    monkeypatch.setattr(module, "_build_clients", lambda env: {})
    argv = ["--limit", "1", "--spend"] if module_name == "corpus_ingest" else ["--family", "gold_passage", "--spend"]
    with store_lock(root):
        assert module.main(argv) == 1
    assert capsys.readouterr().err.strip().startswith("StoreLockedError: ")
    assert sorted(p.name for p in root.iterdir()) == [".engine.lock"]


@pytest.mark.parametrize("limit", ["-5", "0"])
def test_corpus_ingest_limit_below_one_exits_2(limit, capsys):
    """A-CR-01: a negative --limit would slice to all but |limit| documents; argparse refuses it."""
    with pytest.raises(SystemExit) as exc_info:
        corpus_ingest.main(["--limit", limit])
    assert exc_info.value.code == 2
    assert "documents" not in capsys.readouterr().out


@pytest.mark.parametrize("limit", [-5, 0])
def test_corpus_ingest_estimate_refuses_limit_below_one(limit):
    """A-CR-01: the library entry point refuses by name instead of slicing."""
    snapshot = load_snapshot(corpus_ingest.CORPUS_DIR)
    with pytest.raises(corpus_ingest.NonPositiveLimitError):
        corpus_ingest.estimate(snapshot, limit=limit, arm="lightrag")

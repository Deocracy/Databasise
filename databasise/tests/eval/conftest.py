"""Fixtures for the eval-bundle tests (06-04-PLAN.md Task 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from databasise.parity.corpus import CorpusSnapshot, load_snapshot

_EVAL_CORPUS_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "eval-corpus"


@pytest.fixture
def bundle_root(tmp_path: Path) -> Path:
    """A fresh, empty bundle root per test — never the committed evidence bundle root."""
    return tmp_path / "eval-bundles"


@pytest.fixture(scope="session")
def eval_snapshot() -> CorpusSnapshot:
    """The Task 1 eval-corpus snapshot (30 questions), hash-verified on load. Not
    environment-dependent — the fixture files are committed to the repo, so this never skips.
    """
    return load_snapshot(_EVAL_CORPUS_DIR)

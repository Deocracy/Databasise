"""Fixtures every Phase 3 parity test depends on (03-02-PLAN.md Task 3).

The ``store_root`` fixture every store adapter writes under is inherited from
``databasise/tests/conftest.py`` (that fixture already applies to every test under
``databasise/tests/``, including this directory — it is not redefined here).

Environment-dependent fixtures skip cleanly when their prerequisite is absent, so the verifier's
own logic (including the corrupted-chunk ``inconclusive`` path) can still run against a synthetic
v1-shaped index on every machine with no ``v1/`` venv and no network — only the fixtures below are
skip-guarded, never the tests that use a synthetic fixture instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from databasise.parity.corpus import CorpusSnapshot, load_snapshot

_REPO_ROOT = Path(__file__).resolve().parents[3]
_V1_VENV_PYTHON = _REPO_ROOT / "v1" / ".venv" / "bin" / "python"
_V1_WORKING_DIR = _REPO_ROOT / "v1" / ".parity_working_dir"


@pytest.fixture(scope="session")
def v1_venv_python() -> Path:
    """Path to the v1 venv's interpreter. Skips cleanly if the venv (03-02-PLAN.md Task 1) has
    not been set up on this machine.
    """
    if not _V1_VENV_PYTHON.exists():
        pytest.skip(
            f"v1/ venv not found at {_V1_VENV_PYTHON} — run v1 environment setup first "
            "(03-02-PLAN.md Task 1)"
        )
    return _V1_VENV_PYTHON


@pytest.fixture(scope="session")
def v1_index_dir() -> Path:
    """Path to the v1-built index working directory. Skips cleanly if the ingest run
    (03-02-PLAN.md Task 2, ``v1/scripts/run_parity_ingest.py``) has not been performed on this
    machine.
    """
    if not _V1_WORKING_DIR.exists():
        pytest.skip(
            f"v1-built index not found at {_V1_WORKING_DIR} — run "
            "v1/scripts/run_parity_ingest.py first (03-02-PLAN.md Task 2)"
        )
    return _V1_WORKING_DIR


@pytest.fixture(scope="session")
def corpus_snapshot() -> CorpusSnapshot:
    """The Task 2 corpus snapshot, hash-verified on load. Not environment-dependent — the fixture
    files are committed to the repo, so this never skips.
    """
    return load_snapshot()

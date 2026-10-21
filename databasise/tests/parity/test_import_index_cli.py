"""TOOL-02 row test (15-09, D-05): ``python -m databasise.parity.import_index`` parses its arguments
before it takes the store lock, so ``--help`` and a typo never import, verify or write anything.

Every node patches ``import_v1_index`` and ``verify_import`` with recorders and ``DEFAULT_STORE_ROOT`` to
a temp directory first (15-RESEARCH Pitfall 12: before the fix ``main(["--help"])`` runs a real import).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from databasise.parity import import_index


def _outcome(argv: list[str]) -> tuple[str, object]:
    """Run ``main(argv)`` and report ``(type name, value)`` of what it returned or raised."""
    try:
        return "returned", import_index.main(argv)
    except BaseException as caught:  # SystemExit from argparse is the case under test
        return type(caught).__name__, getattr(caught, "code", None)


@pytest.fixture
def recorders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    store = tmp_path / "store"
    calls: dict = {"import": [], "verify": [], "store": store}

    async def fake_import(*args, **kwargs):
        calls["import"].append((args, kwargs))
        return "ws-from-import"

    async def fake_verify(*args, **kwargs):
        calls["verify"].append((args, kwargs))
        return import_index.VerificationResult(status="verified")

    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", store)
    monkeypatch.setattr(import_index, "import_v1_index", fake_import)
    monkeypatch.setattr(import_index, "verify_import", fake_verify)
    return calls


def test_help_exits_zero_and_touches_nothing(recorders):
    kind, code = _outcome(["--help"])

    assert (kind, code) == ("SystemExit", 0), f"--help gave {kind} {code!r}, expected SystemExit 0"
    assert recorders["import"] == [] and recorders["verify"] == []
    assert not recorders["store"].exists(), "--help took the store lock or wrote the store root"


def test_a_misspelt_flag_exits_two_and_touches_nothing(recorders):
    kind, code = _outcome(["--verfiy"])

    assert (kind, code) == ("SystemExit", 2), f"--verfiy gave {kind} {code!r}, expected SystemExit 2"
    assert recorders["import"] == [] and recorders["verify"] == []
    assert not recorders["store"].exists(), "a bad flag took the store lock or wrote the store root"

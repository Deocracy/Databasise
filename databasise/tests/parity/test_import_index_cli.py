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
    except BaseException as caught:  # noqa: BLE001 - SystemExit from argparse is the case under test
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


def test_paths_pass_through_and_the_workspace_prints(recorders, tmp_path, capsys):
    a, b = tmp_path / "v1dir", tmp_path / "other_store"

    code = _outcome(["--v1-working-dir", str(a), "--store-root", str(b), "--verify"])
    out = capsys.readouterr().out

    workspace = import_index._import_workspace()
    assert code == ("returned", 0), f"expected a clean return of 0, got {code!r}"
    assert recorders["import"] == [], "--verify must not import"
    assert len(recorders["verify"]) == 1, "verify_import was not called exactly once"
    seen = [str(x) for x in recorders["verify"][0][0]]
    assert seen == [str(a), str(b), workspace], f"verify_import saw {seen!r}"
    assert workspace in out and "derived from parity corpus snapshot" in out, out


def test_an_explicit_workspace_is_used_and_labelled(recorders, tmp_path, capsys):
    code = _outcome(["--workspace", "w1", "--store-root", str(tmp_path / "s"), "--verify"])
    out = capsys.readouterr().out

    assert code == ("returned", 0), f"expected a clean return of 0, got {code!r}"
    assert len(recorders["verify"]) == 1
    assert "w1" in [str(x) for x in recorders["verify"][0][0]]
    assert "w1 (--workspace)" in out, out


def test_a_full_run_passes_the_workspace_to_the_importer_too(recorders, tmp_path):
    code = _outcome(["--workspace", "w2", "--store-root", str(tmp_path / "s")])

    assert code == ("returned", 0), f"expected a clean return of 0, got {code!r}"
    assert len(recorders["import"]) == 1
    args, kwargs = recorders["import"][0]
    assert "w2" in [str(x) for x in args] + [str(v) for v in kwargs.values()]


def test_the_launcher_workspace_equals_the_derived_workspace():
    from databasise import launcher

    assert launcher.DEFAULT_WORKSPACE == import_index._import_workspace()


def test_a_missing_v1_index_is_one_stderr_line(recorders, tmp_path, monkeypatch, capsys):
    async def refusing_import(*args, **kwargs):
        raise import_index.MissingV1IndexError(tmp_path / "nowhere")

    monkeypatch.setattr(import_index, "import_v1_index", refusing_import)

    code = _outcome(["--v1-working-dir", str(tmp_path / "nowhere"), "--store-root", str(tmp_path / "s")])
    captured = capsys.readouterr()

    assert code == ("returned", 1), f"expected a return of 1, got {code!r}"
    lines = captured.err.strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("MissingV1IndexError:"), captured.err

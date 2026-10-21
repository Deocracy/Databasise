"""TOOL-15 row tests: the Falsifier 2 and F-07 records state only what their renderers computed.

Falsifier 2's verdict paragraph and ``main()``'s exit status derive from the probe results; the
F-07 module has a ``main`` that writes the computed record; both records state one MODAL-05 value.
New names this phase adds are resolved with ``getattr`` and every call is captured, so the file
collects and fails by assertion on the phase base.
"""

from __future__ import annotations

from pathlib import Path

from databasise.evidence import f07_report, falsifier2

_COMMITTED_F2 = falsifier2.EVIDENCE_PATH.read_text(encoding="utf-8")
_EVIDENCE_DIR = Path(falsifier2.__file__).resolve().parent


def _capture(fn, *args):
    """``(result, None)`` or ``(None, exception)``; argparse raises ``SystemExit``."""
    try:
        return fn(*args), None
    except BaseException as caught:  # noqa: BLE001 - the capture is the point
        return None, caught


def test_a_probe_that_does_not_fire_renders_fired_and_exits_one(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(falsifier2, "EVIDENCE_PATH", tmp_path / "f2.md")
    real = falsifier2.evaluate_probe

    def silent_a(probe):
        return frozenset() if probe.probe_id == "a-effects-exceed-part" else real(probe)

    monkeypatch.setattr(falsifier2, "evaluate_probe", silent_a)

    text, err = _capture(falsifier2.render_markdown)
    assert err is None, f"render_markdown raised {type(err).__name__}: {err}"
    assert "Falsifier 2 did not fire" not in text, "verdict is fixed text, not computed"
    assert "Falsifier 2 fired" in text

    code, err = _capture(falsifier2.main, [])
    capsys.readouterr()
    assert err is None, f"main([]) raised {type(err).__name__}: {err}"
    assert code == 1, f"main() returned {code!r}, expected 1"


def test_the_unpatched_run_renders_did_not_fire_and_exits_zero(monkeypatch, tmp_path, capsys):
    out = tmp_path / "f2.md"
    monkeypatch.setattr(falsifier2, "EVIDENCE_PATH", out)

    code, err = _capture(falsifier2.main, [])
    capsys.readouterr()
    assert err is None, f"main([]) raised {type(err).__name__}: {err}"
    assert code == 0, f"main() returned {code!r}, expected 0"
    assert out.read_text(encoding="utf-8") == _COMMITTED_F2

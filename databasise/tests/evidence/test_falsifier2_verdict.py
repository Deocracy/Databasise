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


# --- F-07 record and the shared MODAL-05 statement (Task 2) -------------------------------------


def _verdict_section(text: str) -> str:
    start = text.index("\n## Verdict")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def _status_section(text: str) -> str:
    start = text.index("\n## Status")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def test_f07_main_exists_and_regenerates_the_committed_record(monkeypatch, tmp_path, capsys):
    main = getattr(f07_report, "main", None)
    assert callable(main), "f07_report has no main()"
    out = tmp_path / "f07.md"
    monkeypatch.setattr(f07_report, "EVIDENCE_PATH", out, raising=False)

    code, err = _capture(main, [])
    capsys.readouterr()
    assert err is None, f"main([]) raised {type(err).__name__}: {err}"
    assert code == 0, f"main() returned {code!r}, expected 0"
    committed = (_EVIDENCE_DIR / "F-07-MUTABLE-STORE-DISPOSITION.md").read_text(encoding="utf-8")
    assert out.read_text(encoding="utf-8") == committed


def test_a_third_mutates_store_part_appears_in_the_verdict(monkeypatch):
    from databasise.parts.registry import default_registry
    from databasise.parts.schema import Part

    fake = Part(
        name_at_version="probe/third-mutator@0.1.0",
        kind="extractor",
        structural_depth="stage",
        effects=["mutates_store"],
        upstream_ref=None,
        body=None,
    )
    monkeypatch.setitem(f07_report._KNOWN_REASONS, fake.name_at_version, "A third mutator.")
    registry = default_registry()
    registry.register(fake)

    text, err = _capture(f07_report.render_f07_record, registry)
    assert err is None, f"render raised {type(err).__name__}: {err}"
    assert fake.name_at_version in _verdict_section(text)


def test_the_f07_verdict_claims_no_enforced_comparison_path():
    from databasise.parts.registry import default_registry

    verdict = _verdict_section(f07_report.render_f07_record(default_registry()))
    assert "enforced as an explicit refusal" not in verdict


def test_both_records_state_one_modal05_value():
    from databasise.parts.registry import default_registry

    statement = getattr(f07_report, "MODAL_05_STATEMENT", None)
    assert isinstance(statement, str) and statement, "f07_report has no MODAL_05_STATEMENT"
    assert statement in f07_report.render_f07_record(default_registry())

    cross = (_EVIDENCE_DIR / "CROSS-MODALITY-EVIDENCE.md").read_text(encoding="utf-8")
    flat = " ".join(cross.split())
    assert statement in cross.splitlines()[0], "title line does not carry the statement"
    assert statement in " ".join(_status_section(cross).split()), "Status lacks the statement"
    assert flat.count(statement) >= 3, "the statement is not in the body as well"

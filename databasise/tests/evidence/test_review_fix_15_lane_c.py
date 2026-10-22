"""Phase 15 review fixes, lane C: the evidence renderers (falsifier2, parity_report, f07_report)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from databasise.evidence import falsifier2


@pytest.fixture
def wirings_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A temp copy of the named wirings, with WIRINGS_DIR and EVIDENCE_PATH retargeted to it."""
    wirings = tmp_path / "wirings"
    shutil.copytree(falsifier2.WIRINGS_DIR, wirings)
    monkeypatch.setattr(falsifier2, "WIRINGS_DIR", wirings)
    monkeypatch.setattr(falsifier2, "EVIDENCE_PATH", tmp_path / "FALSIFIER-2-EVIDENCE.md")
    return wirings


def _edit_w2(wirings: Path, edit) -> None:
    path = wirings / "w2-codebase-memory-mcp.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    edit(doc["nodes"]["cbm"])
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_a_named_wiring_violation_fires_falsifier_2(wirings_copy: Path, capsys) -> None:
    _edit_w2(wirings_copy, lambda node: node["effects"].append("writes_artifact"))

    assert falsifier2.failing_wirings() == ("w2-codebase-memory-mcp",)
    assert falsifier2.main([]) == 1
    text = falsifier2.EVIDENCE_PATH.read_text(encoding="utf-8")
    assert "**Result: Falsifier 2 fired.**" in text
    assert "did not fire" not in text
    assert "`effects-exceed-part` at `/nodes/cbm/effects`" in text


def test_a_self_declared_depth_on_a_named_wiring_fires_instead_of_crashing(
    wirings_copy: Path, capsys
) -> None:
    _edit_w2(wirings_copy, lambda node: node.__setitem__("effective_depth", "stage"))

    evidence = falsifier2.evaluate_wiring("w2-codebase-memory-mcp")
    assert evidence.rows == ()
    assert "self-declared-derivation" in {v.code for v in evidence.violations}
    assert falsifier2.main([]) == 1
    text = falsifier2.EVIDENCE_PATH.read_text(encoding="utf-8")
    assert "**Result: Falsifier 2 fired.**" in text
    assert "`self-declared-derivation`" in text


def test_the_committed_wirings_render_no_violation(wirings_copy: Path, capsys) -> None:
    assert falsifier2.failing_wirings() == ()
    assert falsifier2.main([]) == 0
    text = falsifier2.EVIDENCE_PATH.read_text(encoding="utf-8")
    assert text.count("**Validator violations:** none.") == len(falsifier2.NAMED_WIRINGS)

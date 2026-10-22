"""Phase 15 review fixes, lane C: the evidence renderers (falsifier2, parity_report, f07_report)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from databasise.evidence import falsifier2, parity_report


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


# --------------------------------------------------------------------------------------------- #
# parity_report (C-WR-01)
# --------------------------------------------------------------------------------------------- #


@pytest.fixture
def parity_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Temp copies of parity_results/ and human_findings.json; both output documents retargeted."""
    results = tmp_path / "parity_results"
    shutil.copytree(parity_report.RESULTS_DIR, results)
    findings = tmp_path / "human_findings.json"
    shutil.copy(parity_report.HUMAN_FINDINGS_PATH, findings)
    monkeypatch.setattr(parity_report, "RESULTS_DIR", results)
    monkeypatch.setattr(parity_report, "HUMAN_FINDINGS_PATH", findings)
    monkeypatch.setattr(parity_report, "EVIDENCE_PATH", tmp_path / "PARITY-EVIDENCE.md")
    monkeypatch.setattr(parity_report, "DEVIATIONS_PATH", tmp_path / "DECLARED-DEVIATIONS.md")
    return tmp_path


def _rewrite(path: Path, edit) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def _spotcheck(**overrides):
    entry = {"query_id": "q1", "arm": "naive", "judgment": "match", "notes": "same answer",
             "recorded_by": "test", "recorded_at": "2026-10-21"}
    entry.update(overrides)
    return entry


_PARITY_BREAKS = {
    "record-missing-status": lambda root: _rewrite(
        root / "parity_results" / "naive-comparison.json", lambda recs: recs[0].pop("status")
    ),
    "missing-comparison-file": lambda root: (
        root / "parity_results" / "naive-comparison.json"
    ).unlink(),
    "orphan-declared-cause": lambda root: _rewrite(
        root / "human_findings.json",
        lambda d: d["declared_causes"].append({**d["declared_causes"][0], "query_id": "nope"}),
    ),
    "invalid-judgment": lambda root: _rewrite(
        root / "human_findings.json",
        lambda d: d["answer_spotchecks"].append(_spotcheck(judgment="looks fine")),
    ),
}


@pytest.mark.parametrize("case", sorted(_PARITY_BREAKS))
def test_parity_report_refuses_by_name_and_writes_neither_document(
    parity_copy: Path, case: str, capsys
) -> None:
    _PARITY_BREAKS[case](parity_copy)

    assert parity_report.main([]) == 1
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1
    assert err[0].split(":", 1)[0] in {
        "ParityRecordFormatError",
        "OrphanDeviationCauseError",
        "InvalidJudgmentError",
    }
    assert not parity_report.EVIDENCE_PATH.exists()
    assert not parity_report.DEVIATIONS_PATH.exists()


def test_parity_report_renders_a_spotcheck_with_null_notes(parity_copy: Path, capsys) -> None:
    _rewrite(
        parity_copy / "human_findings.json",
        lambda d: d["answer_spotchecks"].append(_spotcheck(notes=None)),
    )

    assert parity_report.main([]) == 0
    assert "**Judgment: `match`** (arm `naive`" in parity_report.EVIDENCE_PATH.read_text(
        encoding="utf-8"
    )


# --------------------------------------------------------------------------------------------- #
# parity_report (C-WR-02): inconclusive prose names the causes it reads
# --------------------------------------------------------------------------------------------- #

_DEGRADED_REASON = "degraded: NodeExecutionError at entity-lookup"
_AUDIT_REASON = "partial: the audit run stopped at entity-lookup"


def _make_d07_inconclusive(root: Path, arm: str) -> None:
    """Rewrite one arm the way 15 D-07's run_comparison writes a degraded decomposed run."""

    def edit(records):
        for record in records:
            record.update(
                status="inconclusive",
                inconclusive_reason=_DEGRADED_REASON,
                chunk_diff=None,
                entity_diff=None,
                relation_diff=None,
                keyword_variance_band=None,
                decomposed_run_record={
                    **(record.get("decomposed_run_record") or {}),
                    "degraded": True,
                    "degradation_reason": "NodeExecutionError at entity-lookup",
                },
            )

    _rewrite(root / "parity_results" / f"{arm}-comparison.json", edit)
    _rewrite(
        root / "parity_results" / f"{arm}-storage-audit.json",
        lambda audit: audit.update(status="inconclusive", reason=_AUDIT_REASON),
    )


_FALSE_CAUSES = (
    "are all absent",
    "MissingParityEnvError",
    "reports an environment-precondition refusal",
    "stopped at a precondition",
    "failed against",
)


def test_an_all_inconclusive_render_names_the_recorded_causes(parity_copy: Path, capsys) -> None:
    for arm in parity_report.ARMS:
        _make_d07_inconclusive(parity_copy, arm)
    # No completed excursion is left, so the committed causes would be orphans.
    _rewrite(parity_copy / "human_findings.json", lambda d: d.update(declared_causes=[]))

    assert parity_report._run_state() == "inconclusive"
    assert parity_report._arm_degraded("hybrid") == (True, "NodeExecutionError at entity-lookup")
    assert parity_report.main([]) == 0
    text = parity_report.EVIDENCE_PATH.read_text(encoding="utf-8")
    assert f"`hybrid`/`q1`: {_DEGRADED_REASON}" in text
    assert f"`hybrid` storage audit: {_AUDIT_REASON}" in text
    for phrase in _FALSE_CAUSES:
        assert phrase not in text, phrase
    deviations = parity_report.DEVIATIONS_PATH.read_text(encoding="utf-8")
    assert "v1/.env.parity" not in deviations


def test_a_mixed_render_names_the_inconclusive_arm_causes(parity_copy: Path) -> None:
    _make_d07_inconclusive(parity_copy, "hybrid")

    assert parity_report._run_state() == "mixed"
    text = parity_report.render_markdown()
    assert f"`hybrid`/`q2`: {_DEGRADED_REASON}" in text
    assert f"`hybrid` storage audit: {_AUDIT_REASON}" in text
    for phrase in _FALSE_CAUSES:
        assert phrase not in text, phrase

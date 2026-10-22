"""Phase 15 review fixes, lane C: the evidence renderers (falsifier2, parity_report, f07_report)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from databasise import cli
from databasise.evidence import f07_report, falsifier2, parity_report


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
    # C-ITER2-CR-01: an inconclusive record's degradation is a recorded cause, not a degraded arm.
    assert parity_report._arm_degraded("hybrid") == (False, "")
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


def test_a_degraded_inconclusive_record_does_not_rewrite_the_arm_s_completed_excursion(
    parity_copy: Path,
) -> None:
    """C-ITER2-CR-01: hybrid's q1 completed with a real excursion; only q2 degraded (D-07)."""

    def degrade_q2(records):
        record = next(r for r in records if r["query_id"] == "q2")
        record.update(
            status="inconclusive",
            inconclusive_reason=_DEGRADED_REASON,
            original_arm_result=None,
            chunk_diff=None,
            entity_diff=None,
            relation_diff=None,
            decomposed_run_record={"degraded": True, "degradation_reason": "NodeExecutionError"},
        )

    _rewrite(parity_copy / "parity_results" / "hybrid-comparison.json", degrade_q2)

    assert parity_report._arm_degraded("hybrid") == (False, "")
    verdict = parity_report._arm_verdict_line("hybrid")
    assert "the two disagree: `q1`: chunk_diff=2" in verdict
    assert "symmetric_difference=[]" not in verdict
    deviation = parity_report._render_known_design_deviation()
    assert "degraded before completing a real retrieval" not in deviation
    assert "surfaces as a measured excursion" in deviation
    guidance = parity_report._render_spotcheck_arm_guidance()
    assert "original_arm_result.answer" not in guidance
    assert guidance.count("`hybrid`") == 1
    assert f"`hybrid`/`q2`: {_DEGRADED_REASON}" in parity_report.render_markdown()


def test_a_mixed_arm_s_verdict_line_speaks_only_for_its_completed_records(parity_copy: Path) -> None:
    """ITER3-C-WR-01 (D-16): q1 clean, q2 a D-07 degraded inconclusive record; the line must not
    say the arm completed, nor claim an arm-wide exact agreement."""

    def clean_q1_degrade_q2(records):
        for record in records:
            if record["query_id"] == "q1":
                for name in ("chunk_diff", "entity_diff", "relation_diff"):
                    record[name] = {**(record.get(name) or {}), "symmetric_difference": []}
            else:
                record.update(
                    status="inconclusive",
                    inconclusive_reason=_DEGRADED_REASON,
                    chunk_diff=None,
                    entity_diff=None,
                    relation_diff=None,
                    decomposed_run_record={"degraded": True, "degradation_reason": "NodeExecutionError"},
                )

    _rewrite(parity_copy / "parity_results" / "hybrid-comparison.json", clean_q1_degrade_q2)

    assert parity_report._arm_state("hybrid") == "mixed"
    verdict = parity_report._arm_verdict_line("hybrid")
    assert "a validated exact retrieval-level agreement" not in verdict
    assert "`hybrid` completed" not in verdict
    assert "`hybrid`'s completed record(s) measured" in verdict
    assert f"did not complete: `hybrid`/`q2`: {_DEGRADED_REASON}" in verdict
    text = parity_report._render_verdict()
    assert "an outcome only for each arm's completed records" in text
    assert "an outcome only for the arms that completed" not in text


# --------------------------------------------------------------------------------------------- #
# C-WR-03 (no write into an installed package) and C-WR-04 (named refusals, D-03)
# --------------------------------------------------------------------------------------------- #


def _one_refusal_line(capsys, name: str) -> None:
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1 and err[0].startswith(f"{name}: "), err


def test_write_committed_documents_refuses_an_installed_package_and_writes_nothing(
    tmp_path: Path,
) -> None:
    source = tmp_path / "checkout" / "A.md"
    installed = tmp_path / "lib" / "site-packages" / "databasise" / "evidence" / "B.md"
    source.parent.mkdir(parents=True)
    installed.parent.mkdir(parents=True)

    with pytest.raises(cli.InstalledPackageWriteError):
        cli.write_committed_documents((source, "a"), (installed, "b"))
    assert not source.exists() and not installed.exists()

    cli.write_committed_documents((source, "a"))
    assert source.read_text(encoding="utf-8") == "a"


@pytest.fixture
def installed_dir(tmp_path: Path) -> Path:
    path = tmp_path / "lib" / "site-packages" / "databasise" / "evidence"
    path.mkdir(parents=True)
    return path


def test_f07_report_refuses_to_write_into_an_installed_package(
    installed_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    target = installed_dir / "F-07-MUTABLE-STORE-DISPOSITION.md"
    monkeypatch.setattr(f07_report, "EVIDENCE_PATH", target)

    assert f07_report.main([]) == 1
    _one_refusal_line(capsys, "InstalledPackageWriteError")
    assert not target.exists()


def test_f07_report_maps_an_os_write_error_to_one_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr(f07_report, "EVIDENCE_PATH", tmp_path / "missing-dir" / "F-07.md")

    assert f07_report.main([]) == 1
    _one_refusal_line(capsys, "FileNotFoundError")


def test_f07_report_refuses_an_unreasoned_mutates_store_part_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    target = tmp_path / "F-07.md"
    monkeypatch.setattr(f07_report, "EVIDENCE_PATH", target)
    # D-16: rendering from probe_registry() raises (its codebase-memory-mcp part has no reason).
    monkeypatch.setattr(f07_report, "default_registry", falsifier2.probe_registry)

    with pytest.raises(ValueError):  # still a ValueError for library callers
        f07_report.render_f07_record(falsifier2.probe_registry())
    assert f07_report.main([]) == 1
    _one_refusal_line(capsys, "UnreasonedMutableStoreError")
    assert not target.exists()


def test_falsifier2_refuses_a_malformed_boundary_knob_by_name(wirings_copy: Path, capsys) -> None:
    path = wirings_copy / "w2-codebase-memory-mcp.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["boundary_knobs"][0].pop("rationale")
    path.write_text(json.dumps(doc), encoding="utf-8")

    assert falsifier2.main([]) == 1
    _one_refusal_line(capsys, "MalformedBoundaryKnobError")
    assert not falsifier2.EVIDENCE_PATH.exists()


@pytest.mark.parametrize("stem", ["w1-lightrag-query-side", "w2-codebase-memory-mcp"])
def test_falsifier2_refuses_a_named_wiring_that_is_not_json_by_name(
    wirings_copy: Path, stem: str, capsys
) -> None:
    """C-ITER2-WR-01 (D-03): one stderr line and exit 1, not a JSONDecodeError traceback."""
    (wirings_copy / f"{stem}.json").write_text("{not json", encoding="utf-8")

    assert falsifier2.main([]) == 1
    _one_refusal_line(capsys, "MalformedWiringDocumentError")
    assert not falsifier2.EVIDENCE_PATH.exists()


@pytest.mark.parametrize("stem", ["w1-lightrag-query-side", "w2-codebase-memory-mcp"])
@pytest.mark.parametrize("content", [b"[]", b'"x"', b"\xff\xfe{}"], ids=["list", "string", "not-utf8"])
def test_falsifier2_refuses_a_named_wiring_that_is_not_a_json_object_by_name(
    wirings_copy: Path, stem: str, content: bytes, capsys
) -> None:
    """ITER3-C-WR-02 (D-03): valid JSON that is not an object, or bytes that are not UTF-8, is one
    stderr line and exit 1, not an AttributeError or UnicodeDecodeError traceback."""
    (wirings_copy / f"{stem}.json").write_bytes(content)

    assert falsifier2.main([]) == 1
    _one_refusal_line(capsys, "MalformedWiringDocumentError")
    assert not falsifier2.EVIDENCE_PATH.exists()


def test_falsifier2_refuses_boundary_knobs_that_are_not_a_list_by_name(wirings_copy: Path, capsys) -> None:
    """ITER3-C-WR-02 (D-03): ``boundary_knobs: 5`` is MalformedBoundaryKnobError, not a TypeError."""
    path = wirings_copy / "w2-codebase-memory-mcp.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["boundary_knobs"] = 5
    path.write_text(json.dumps(doc), encoding="utf-8")

    assert falsifier2.main([]) == 1
    _one_refusal_line(capsys, "MalformedBoundaryKnobError")
    assert not falsifier2.EVIDENCE_PATH.exists()


def test_falsifier2_refuses_to_write_into_an_installed_package(
    installed_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    target = installed_dir / "FALSIFIER-2-EVIDENCE.md"
    monkeypatch.setattr(falsifier2, "EVIDENCE_PATH", target)

    assert falsifier2.main([]) == 1
    _one_refusal_line(capsys, "InstalledPackageWriteError")
    assert not target.exists()


def test_parity_report_refuses_to_write_into_an_installed_package(
    parity_copy: Path, installed_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    target = installed_dir / "PARITY-EVIDENCE.md"
    monkeypatch.setattr(parity_report, "EVIDENCE_PATH", target)

    assert parity_report.main([]) == 1
    _one_refusal_line(capsys, "InstalledPackageWriteError")
    assert not target.exists()
    assert not parity_report.DEVIATIONS_PATH.exists()

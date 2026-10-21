"""Structural assertions over ``databasise/evidence/CROSS-MODALITY-EVIDENCE.md``.

06-08-PLAN.md wrote the record as BLOCKED (the owner's ``defer-and-record-blocked`` decision); the
2026-09-10 runs then discharged MODAL-05. 15-17 (TOOL-15, D-16) pins the record's present shape: the
title line and Status section carry the one MODAL-05 statement, the single Findings row is marked
superseded by the "Real run — 2026-09-10" section, and each BLOCKED section is kept as marked
history. Parses the actual document structure (title line, blocker table, named sections), never a
whole-file grep — mirrors ``tests/evidence/test_falsifier5_record.py``'s own
parse-the-actual-structure discipline.
"""

from __future__ import annotations

import re
from pathlib import Path


def _evidence_dir() -> Path:
    # databasise/tests/evidence/test_cross_modality_record.py -> databasise/evidence/
    return Path(__file__).resolve().parent.parent.parent / "evidence"


def _text() -> str:
    return (_evidence_dir() / "CROSS-MODALITY-EVIDENCE.md").read_text(encoding="utf-8")


def _section(text: str, heading_pattern: str) -> str:
    """Return the body of the first ``##``-level section whose heading matches
    ``heading_pattern``, up to (not including) the next ``## `` heading or EOF."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and re.search(heading_pattern, line, re.IGNORECASE):
            start = i
            break
    assert start is not None, f"no section heading matching {heading_pattern!r} found"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end])


def _collapsed(text: str) -> str:
    """Collapses markdown line-wrapping whitespace so a substring assertion is not tripped up by
    where a prose sentence happens to hard-wrap."""
    return re.sub(r"\s+", " ", text)


def _parse_markdown_table(section_text: str) -> list[list[str]]:
    table_lines = [line for line in section_text.splitlines() if line.strip().startswith("|")]
    assert len(table_lines) >= 3, f"expected a header + separator + rows, found {table_lines!r}"

    def _is_separator(line: str) -> bool:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        return all(re.fullmatch(r"-+", c) for c in cells)

    header, *rest = table_lines
    assert _is_separator(rest[0]), f"second table line is not a separator row: {rest[0]!r}"
    return [[c.strip() for c in line.strip().strip("|").split("|")] for line in rest[1:]]


def test_document_exists_and_is_non_empty():
    path = _evidence_dir() / "CROSS-MODALITY-EVIDENCE.md"
    assert path.exists(), f"{path} does not exist"
    assert path.stat().st_size > 0, f"{path} is empty"


def test_modal05_claim_quoted_verbatim():
    text = _collapsed(re.sub(r"(?m)^>\s?", "", _text()))
    # Verbatim substrings from .planning/REQUIREMENTS.md's MODAL-05 row (the quote hard-wraps).
    assert "the milestone proof point" in text
    assert "F-14's outcome" in text
    assert "§18.3 seam-invariance falsifier" in text


def _modal05_statement() -> str:
    from databasise.evidence import f07_report

    return f07_report.MODAL_05_STATEMENT


def test_title_and_status_state_the_one_modal05_value():
    text = _text()
    statement = _modal05_statement()
    assert statement in text.splitlines()[0]
    status = _collapsed(_section(text, r"^## Status"))
    assert statement in status
    assert "BLOCKED" in status  # the history is named as history
    assert "superseded history" in status


def test_deferral_sections_are_marked_superseded_history():
    text = _text()
    for heading in (
        r"^## Findings",
        r"^## Owner decision",
        r"^## What was built instead",
        r"^## Method and limits",
        r"^## Entry criterion",
        r"^## Next Phase Readiness",
        r"^## Real run attempted",
    ):
        body = _section(text, heading).splitlines()
        assert body[2].startswith("*Superseded"), f"{heading}: first line is {body[2]!r}"
    assert _modal05_statement() in _collapsed(_section(text, r"^## Real run — 2026-09-10"))


def test_document_never_reports_a_real_run_result():
    text = _text()
    limits = _section(text, r"^## Method and limits")
    assert "No counts, spend, duration, or comparison result is reported" in limits
    # Never a numeric "graph_node_count: N" / "duration_seconds: N"-shaped claim anywhere in the
    # body — those are IndexBuildResult's/CrossModalityRecord's own field names, and their
    # presence with a number would mean a real result was pasted in.
    fabricated_result_pattern = re.compile(
        r"(?:graph_node_count|graph_edge_count|chunk_vector_count|entity_vector_count|"
        r"fact_vector_count|duration_seconds|token_spend)\s*[:=]\s*\d",
        re.IGNORECASE,
    )
    assert not fabricated_result_pattern.search(text), (
        "document appears to report a real build/comparison result field with a numeric value — "
        "no run occurred and no such value exists to report"
    )


def test_findings_table_has_exactly_one_row_marked_superseded():
    text = _text()
    findings = _section(text, r"^## Findings")
    rows = _parse_markdown_table(findings)
    assert len(rows) == 1, f"expected exactly 1 row, found {len(rows)}: {rows}"
    assert "Superseded by the" in rows[0][1]
    assert "Real run — 2026-09-10" in rows[0][1]


def test_blocker_names_the_unauthorized_real_invocation():
    text = _text()
    findings = _section(text, r"^## Findings")
    assert "build_hipporag_index" in findings
    assert "v1/.env.parity" in findings
    assert "qwen" in findings.lower()
    assert "20-document" in findings or "Phase 3 parity corpus" in findings


def test_owner_decision_defer_and_record_blocked_recorded():
    text = _text()
    decision = _collapsed(_section(text, r"^## Owner decision"))
    assert "defer-and-record-blocked" in decision
    assert "No real invocation runs" in decision
    assert "No LLM call, no embedding call, no ingestion, no spend" in decision


def test_entry_criterion_named():
    text = _text()
    criterion = _collapsed(_section(text, r"^## Entry criterion"))
    assert "owner authorization" in criterion.lower()
    assert "build_hipporag_index" in criterion
    assert "run_cross_modality" in criterion


def test_the_superseded_limits_and_readiness_sections_keep_their_history_only():
    text = _text()
    limits = _section(text, r"^## Method and limits")
    assert "MODAL-05 stays Pending" in limits  # history, under the superseded marker
    readiness = _section(text, r"^## Next Phase Readiness")
    assert "deferred" in readiness.lower()
    assert "no longer open" in readiness


def test_f14_evidence_is_cited_not_restated():
    text = _text()
    status = _section(text, r"^## Status")
    assert "F-14-SEAM-INVARIANCE.md" in status

"""06-08-PLAN.md Task 3 (owner-authorized deviation — see 06-08-SUMMARY.md ## Deviations from
Plan): structural assertions over ``databasise/evidence/CROSS-MODALITY-EVIDENCE.md``, adapted to
the blocked reality the owner's ``defer-and-record-blocked`` checkpoint decision produced. The
plan's original Task 3 asked for a *passing-shape* record (a per-arm, per-query table of real
observed counts, a structural-comparability finding drawn from a real run). No cross-modality run
occurred — Task 1's index build and Task 2's comparison were both deliberately not invoked — so
this test instead pins the *BLOCKED* shape: the record names the one blocker, names the entry
criterion for a future run, and never claims a count/spend/duration/comparison result it does not
have. Parses the actual document structure (front matter heading, blocker table, named sections),
never a whole-file grep — mirrors ``tests/evidence/test_falsifier5_record.py``'s own
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
    text = _text()
    # Verbatim substrings from .planning/REQUIREMENTS.md's MODAL-05 row.
    assert "the milestone proof point" in text
    assert "F-14's outcome" in text
    assert "§18.3 seam-invariance falsifier" in text


def test_status_section_states_blocked_not_discharged():
    text = _text()
    status = _section(text, r"^## Status")
    assert "BLOCKED" in status
    assert "NOT discharged" in status or "not discharged" in status.lower()
    assert "No real cross-modality run" in status


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


def test_findings_table_has_exactly_one_blocker_row():
    text = _text()
    findings = _section(text, r"^## Findings")
    rows = _parse_markdown_table(findings)
    assert len(rows) == 1, f"expected exactly 1 blocker row, found {len(rows)}: {rows}"


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


def test_modal05_stays_pending_in_limits():
    text = _text()
    limits = _section(text, r"^## Method and limits")
    assert "MODAL-05 stays Pending" in limits


def test_next_phase_readiness_names_the_deferred_run_and_the_entry_criterion():
    text = _text()
    readiness = _section(text, r"^## Next Phase Readiness")
    assert "deferred" in readiness.lower()
    assert "MODAL-05, this phase's core-value requirement, remains unproven" in readiness


def test_f14_evidence_is_cited_not_restated():
    text = _text()
    status = _section(text, r"^## Status")
    assert "F-14-SEAM-INVARIANCE.md" in status

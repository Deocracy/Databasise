"""06-06-PLAN.md Task 3 (owner-authorized deviation — see 06-06-SUMMARY.md ## Deviations from
Plan): structural assertions over ``databasise/evidence/FALSIFIER-5-EVIDENCE.md``, adapted to the
blocked reality the owner's ``defer-run`` checkpoint decision produced. The plan's original Task 3
asked for a *passing-shape* record (a findings table of two committed calibration results, a
pre-registered threshold, a verdict). No calibration ran — Task 2 was deliberately not executed —
so this test instead pins the *BLOCKED* shape: the record names both blockers, names both
preconditions for a future run, and never claims a floor value it does not have. Parses the actual
document structure (front matter heading, blocker table, precondition list), never a whole-file
grep — mirrors ``tests/evidence/test_falsifier4_evidence.py``'s own parse-the-actual-structure
discipline.
"""

from __future__ import annotations

import re
from pathlib import Path


def _evidence_dir() -> Path:
    # databasise/tests/evidence/test_falsifier5_record.py -> databasise/evidence/
    return Path(__file__).resolve().parent.parent.parent / "evidence"


def _text() -> str:
    return (_evidence_dir() / "FALSIFIER-5-EVIDENCE.md").read_text(encoding="utf-8")


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
    where a prose sentence happens to hard-wrap — the wrap point is a rendering choice, not part
    of the claim being asserted."""
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
    path = _evidence_dir() / "FALSIFIER-5-EVIDENCE.md"
    assert path.exists(), f"{path} does not exist"
    assert path.stat().st_size > 0, f"{path} is empty"


def test_mach03_pass_criterion_quoted_verbatim():
    text = _text()
    # Verbatim substring from .planning/REQUIREMENTS.md's MACH-03 row, stripped of markdown bold
    # decoration so the assertion survives incidental re-wrapping.
    assert "per-tier null width at T1 materially narrower than T0" in text
    assert "SELECTION Falsifier" in text
    assert "5" in text


def test_status_section_states_blocked_not_discharged():
    text = _text()
    status = _section(text, r"^## Status")
    assert "BLOCKED" in status
    assert "NOT discharged" in status or "not discharged" in status.lower()
    assert "MACH-03 is not met" in status


def test_document_never_reports_a_floor_value():
    text = _text()
    # The document must say explicitly that no floor is reported...
    assert "No floor value is reported anywhere in this document" in text
    # ...and must not smuggle one in as a bare "p95 = <number>" / "floor: <number>" pattern
    # anywhere in the body (case-insensitive; tolerates markdown emphasis around the label).
    # A "<=" is excluded from the "=" branch (but not the ":" branch): it is the comparison
    # operator in a *threshold formula* ("floor <= 0.5 x ... floor", 06-17's pre-registered
    # threshold), never an assignment of a measured value — the pre-registration states a
    # relationship between two not-yet-computed floors, not a number read from a run.
    floor_value_pattern = re.compile(
        r"(?:p95|floor)[^a-zA-Z0-9\n]{0,10}(?:(?<!<)=|:)[^a-zA-Z0-9\n]{0,5}\d", re.IGNORECASE
    )
    assert not floor_value_pattern.search(text), (
        "document appears to report a numeric floor/p95 value — Falsifier 5 has not run and no "
        "floor exists to report"
    )


def test_findings_table_has_one_row_per_named_blocker():
    text = _text()
    findings = _section(text, r"^## Findings")
    rows = _parse_markdown_table(findings)
    assert len(rows) == 2, f"expected exactly 2 blocker rows, found {len(rows)}: {rows}"

    target_families = {row[1].strip("`") for row in rows}
    assert target_families == {"answer_level", "gold_passage"}, target_families

    tiers = {row[2].strip("`") for row in rows}
    assert tiers == {"T0", "T1"}, tiers


def test_blocker_1_names_the_unresolved_judge_identity():
    text = _text()
    findings = _section(text, r"^## Findings")
    assert "judge_instance" in findings
    assert '"unresolved"' in findings
    assert "EVAL-BUNDLE-V1.md" in findings


def test_blocker_2_names_the_unbudgetable_ingest_cost():
    text = _text()
    findings = _section(text, r"^## Findings")
    assert "291-document" in findings or "291" in findings
    assert "unbudgetable" in findings
    assert "full_ingest.py" in findings


def test_two_preconditions_named():
    text = _text()
    preconditions = _section(text, r"^## Two preconditions")
    assert "resolved judge identity" in preconditions.lower()
    assert "cost-bounded indexing" in preconditions.lower() or "cost-bounded" in preconditions.lower()


def test_owner_decision_defer_run_recorded():
    text = _text()
    decision = _collapsed(_section(text, r"^## Owner decision"))
    assert "defer-run" in decision
    assert "No corpus is ingested, no LLM calls are made, no spend is incurred" in decision


def test_mach03_stays_pending_stated_in_limits():
    text = _text()
    limits = _section(text, r"^## Method and limits")
    assert "MACH-03 stays Pending" in limits


def test_next_phase_readiness_names_phase_7_and_the_two_preconditions():
    text = _text()
    readiness = _section(text, r"^## Next Phase Readiness")
    assert "deferred to a later plan" in readiness
    assert "Phase 7" in readiness
    assert "resolved judge identity" in readiness
    assert "cost-bounded indexing" in readiness

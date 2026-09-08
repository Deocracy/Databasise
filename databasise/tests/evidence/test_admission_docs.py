"""Structural assertions over Phase 5 plan 05-02's two evidence documents
(``databasise/evidence/INJECTED-LLM-ENDPOINT-SURVEY.md`` and
``databasise/evidence/DR-04-DECISION.md``), so a later edit that silently hollows out a row, a
front-matter field, or the provenance disclosure fails a test rather than passing unnoticed.

Every assertion parses the specific structure it checks (the findings table, the YAML-shaped
front matter block) rather than grepping the whole file for a substring — a doc-wide grep would
pass on an accidental mention anywhere in the prose, not on the field actually being present in
the position that gives it meaning.
"""

from __future__ import annotations

import re
from pathlib import Path


def _evidence_dir() -> Path:
    # databasise/tests/evidence/test_admission_docs.py -> databasise/evidence/
    return Path(__file__).resolve().parent.parent.parent / "evidence"


def _survey_text() -> str:
    return (_evidence_dir() / "INJECTED-LLM-ENDPOINT-SURVEY.md").read_text(encoding="utf-8")


def _section(text: str, heading_pattern: str) -> str:
    """Return the body of the first ``##``-level section whose heading matches
    ``heading_pattern`` (case-insensitive), up to (not including) the next ``## `` heading or EOF.
    """
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


def _parse_markdown_table(section_text: str) -> list[list[str]]:
    """Parse the first pipe-table inside ``section_text`` into a list of data rows (each a list
    of cell strings), skipping the header row and the ``---`` separator row.
    """
    table_lines = [
        line for line in section_text.splitlines() if line.strip().startswith("|")
    ]
    assert len(table_lines) >= 3, f"expected a header + separator + rows, found {table_lines!r}"

    def _is_separator(line: str) -> bool:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        return all(re.fullmatch(r"-+", c) for c in cells)

    header, *rest = table_lines
    assert _is_separator(rest[0]), f"second table line is not a separator row: {rest[0]!r}"
    data_rows = rest[1:]

    return [
        [c.strip() for c in line.strip().strip("|").split("|")]
        for line in data_rows
    ]


# ---------------------------------------------------------------------------
# Survey document (MACH-04 / Falsifier 8)
# ---------------------------------------------------------------------------


def test_survey_names_five_engines():
    text = _survey_text()
    findings = _section(text, r"^## Findings")
    rows = _parse_markdown_table(findings)

    assert len(rows) == 5, f"expected exactly five engine rows, found {len(rows)}: {rows}"

    engine_cells = [row[0] for row in rows]
    for expected in (
        "codebase-memory-mcp",
        "postgres-mcp",
        "supabase-mcp",
        "code-graph-rag",
        "LightRAG server",
    ):
        assert any(expected in cell for cell in engine_cells), (
            f"{expected!r} not found in any findings-table engine cell: {engine_cells}"
        )

    for expected_id in ("CA-1", "CA-2", "MC-1", "MC-2"):
        assert expected_id in text, f"{expected_id!r} not found anywhere in the survey document"


def test_survey_findings_table_each_row_carries_an_evidence_class_tag():
    text = _survey_text()
    findings = _section(text, r"^## Findings")
    rows = _parse_markdown_table(findings)

    evidence_tags = ("[code-verified]", "[docs-verified]", "[inference]")
    for row in rows:
        # Evidence class and source is the fifth column (index 4) per the header order this
        # document declares: Engine, Hosting shape, Accepts injected endpoint, Injection
        # mechanism, Evidence class and source, §8 condition 3 consequence.
        evidence_cell = row[4]
        assert any(tag in evidence_cell for tag in evidence_tags), (
            f"row {row[0]!r} evidence cell carries none of {evidence_tags}: {evidence_cell!r}"
        )

    seen_tags = {tag for row in rows for tag in evidence_tags if tag in row[4]}
    assert seen_tags == set(evidence_tags), (
        f"expected all three evidence-class tags to appear at least once, found: {seen_tags}"
    )


def test_survey_states_list_provenance():
    text = _survey_text()
    provenance_section = _section(text, r"provenance")
    assert "A2" in provenance_section, (
        "the list-provenance section must name Assumption A2 as the inference's origin"
    )


def test_survey_states_the_claim_under_test_verbatim():
    text = _survey_text()
    assert "Engines refuse the injected endpoint in the common case" in text
    assert "Engines accept an injected LLM endpoint in the common case" in text


def test_survey_document_exists_and_is_non_empty():
    path = _evidence_dir() / "INJECTED-LLM-ENDPOINT-SURVEY.md"
    assert path.exists(), f"{path} does not exist"
    assert path.stat().st_size > 0, f"{path} is empty"

"""06-03-PLAN.md Task 3: structural assertions over ``databasise/evidence/F-14-SEAM-INVARIANCE.md``
— the F-14 claim is quoted verbatim from ``docs/system-model/MODEL-RED-TEAM.md``, the findings
table carries exactly one row per ``ResponseEnvelope`` field (derived live from
``ResponseEnvelope.model_fields``, never a hand-written list, so a field added to the envelope
later fails this test as an unrecorded widening rather than passing silently by omission), the
document distinguishes a field-content difference from a field-set difference for ``answer`` and
``depth_label``, and a verdict section states the outcome.

Mirrors ``tests/evidence/test_admission_docs.py``/``test_falsifier4_evidence.py``'s own
parse-the-actual-structure discipline — every assertion below parses the specific section/table it
checks, never a whole-file grep.
"""

from __future__ import annotations

import re
from pathlib import Path

from databasise.seam.envelope import ResponseEnvelope


def _evidence_dir() -> Path:
    # databasise/tests/evidence/test_f14_record.py -> databasise/evidence/
    return Path(__file__).resolve().parent.parent.parent / "evidence"


def _text() -> str:
    return (_evidence_dir() / "F-14-SEAM-INVARIANCE.md").read_text(encoding="utf-8")


def _collapsed(text: str) -> str:
    """Collapses markdown line-wrapping whitespace (and strips leading ``> `` blockquote markers)
    so a substring assertion is not tripped up by where a prose paragraph or a quoted block
    happens to wrap — mirrors ``test_falsifier4_evidence.py``'s own helper of the same name."""
    unquoted = re.sub(r"(?m)^>\s?", "", text)
    return re.sub(r"\s+", " ", unquoted)


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


def _parse_markdown_table(section_text: str) -> list[list[str]]:
    table_lines = [line for line in section_text.splitlines() if line.strip().startswith("|")]
    assert len(table_lines) >= 3, f"expected a header + separator + rows, found {table_lines!r}"

    def _is_separator(line: str) -> bool:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        return all(re.fullmatch(r"-+", c) for c in cells)

    header, *rest = table_lines
    assert _is_separator(rest[0]), f"second table line is not a separator row: {rest[0]!r}"
    return [[c.strip() for c in line.strip().strip("|").split("|")] for line in rest[1:]]


def _model_red_team_f14_section() -> str:
    path = Path(__file__).resolve().parents[3] / "docs" / "system-model" / "MODEL-RED-TEAM.md"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith("### F-14")), None
    )
    assert start is not None, "MODEL-RED-TEAM.md carries no '### F-14' heading"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("### "):
            end = j
            break
    return "\n".join(lines[start:end])


def test_document_exists_and_is_non_empty():
    path = _evidence_dir() / "F-14-SEAM-INVARIANCE.md"
    assert path.exists(), f"{path} does not exist"
    assert path.stat().st_size > 0, f"{path} is empty"


def test_document_carries_a_dated_header():
    text = _text()
    header = "\n".join(text.splitlines()[:6])
    assert re.search(r"\*\*Date:\*\*\s*\d{4}-\d{2}-\d{2}", header), (
        f"no dated header found near the top of the document: {header!r}"
    )


def test_the_f14_claim_is_quoted_verbatim_from_model_red_team():
    """Derived live from ``docs/system-model/MODEL-RED-TEAM.md``'s own F-14 section — never a
    hand-copied literal that could silently drift from the source document."""
    f14_source = _model_red_team_f14_section()
    # The refutation-condition sentence §18.3's own invariance rule names — the single sentence
    # both this document and F-14's own "Issue" paragraph must state identically.
    refutation_sentence = (
        "the first Phase 3 stress-modality wiring exercise run against this seam finding a case "
        "a consumer can only interpret correctly by knowing which modality answered — at that "
        "point the envelope's closed field set is incomplete."
    )
    assert refutation_sentence in f14_source, (
        "the expected refutation sentence was not found in MODEL-RED-TEAM.md's own F-14 section "
        "— this test's own source-of-truth assumption is stale"
    )

    doc_text = _collapsed(_text())
    assert refutation_sentence in doc_text, (
        "F-14-SEAM-INVARIANCE.md does not quote the F-14 refutation sentence verbatim"
    )
    assert (
        "the falsifier both clauses name as the actual test has not fired, in either direction, "
        "because nothing has run"
        in doc_text
    )


def test_findings_table_has_exactly_one_row_per_response_envelope_field_each_code_verified():
    expected_fields = set(ResponseEnvelope.model_fields.keys())
    assert expected_fields, "ResponseEnvelope declares no fields — nothing to check against"

    text = _text()
    findings = _section(text, r"^## Findings")
    rows = _parse_markdown_table(findings)

    field_cells = [row[0].strip("`") for row in rows]
    assert set(field_cells) == expected_fields, (
        f"findings table field set {set(field_cells)} does not match "
        f"ResponseEnvelope.model_fields {expected_fields}"
    )
    assert len(field_cells) == len(expected_fields), "a field name appears more than once"

    for row in rows:
        assert any("[code-verified]" in cell for cell in row), (
            f"row for {row[0]!r} carries no [code-verified] tag: {row}"
        )


def test_findings_table_distinguishes_content_difference_from_field_set_difference_for_answer_and_depth_label():
    text = _text()
    findings = _section(text, r"^## Findings")
    rows = _parse_markdown_table(findings)
    by_field = {row[0].strip("`"): row for row in rows}

    for field in ("answer", "depth_label"):
        assert field in by_field, f"no findings-table row for {field!r}"
        disposition = by_field[field][-1]
        assert "content difference" in disposition.lower(), (
            f"{field!r}'s own row must state this is a content difference, not a field-set "
            f"difference: {disposition!r}"
        )
        assert "field-set difference" in disposition.lower() or "not a field-set" in disposition.lower(), (
            f"{field!r}'s own row must explicitly distinguish itself from a field-set difference: "
            f"{disposition!r}"
        )

    # Every other field's own row must NOT claim a content difference this run — the distinction
    # only means something if it is not asserted vacuously for every row.
    for field, row in by_field.items():
        if field in ("answer", "depth_label"):
            continue
        assert "content difference" not in row[-1].lower(), (
            f"{field!r}'s own row unexpectedly claims a content difference: {row[-1]!r}"
        )


def test_verdict_section_states_the_outcome_either_way():
    text = _text()
    verdict = _collapsed(_section(text, r"^## Verdict"))

    no_field_changed = "no consumer-visible envelope field changed" in verdict
    names_a_changed_field = bool(
        re.search(
            r"`(" + "|".join(re.escape(f) for f in ResponseEnvelope.model_fields) + r")`.{0,80}(differ|chang)",
            verdict,
        )
    )
    assert no_field_changed or names_a_changed_field, (
        "verdict section states neither 'no field changed' nor names a specific changed field: "
        f"{verdict!r}"
    )
    assert "F-14" in verdict


def test_method_and_limits_section_names_architecture_comparison_mode_and_the_real_corpus_gap():
    text = _text()
    limits = _collapsed(_section(text, r"^## Method and limits"))
    assert "architecture-comparison mode" in limits
    assert "06-08" in limits
    assert "opaque" in limits.lower()

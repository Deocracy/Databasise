"""06-09-PLAN.md Task 1: structural assertions over
``databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md`` — parses front matter and table
structurally, never a whole-file grep, and proves the record's own enumeration matches the live
``default_registry()`` population plus the two catalogued-not-built roster entries at test time.
Mirrors ``tests/evidence/test_cross_modality_record.py``'s own parse-the-actual-structure
discipline.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from databasise.evidence.f07_report import (
    _ADMISSIBLE_DISPOSITIONS,
    _CATALOGUED_NOT_BUILT,
    render_f07_record,
)
from databasise.parts.registry import PartRegistry, default_registry


def _evidence_dir() -> Path:
    # databasise/tests/evidence/test_f07_record.py -> databasise/evidence/
    return Path(__file__).resolve().parent.parent.parent / "evidence"


def _text() -> str:
    return (_evidence_dir() / "F-07-MUTABLE-STORE-DISPOSITION.md").read_text(encoding="utf-8")


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


def _collapsed(text: str) -> str:
    """Collapses markdown line-wrapping whitespace (and strips blockquote ``> `` markers at the
    start of a line) so a substring assertion is not tripped up by where a prose sentence happens
    to hard-wrap or by a blockquote continuing onto the next line."""
    text = re.sub(r"(?m)^>\s?", "", text)
    return re.sub(r"\s+", " ", text)


def _live_mutates_store_names(registry: PartRegistry) -> set[str]:
    return {
        registry.get(name).name_at_version
        for name in registry.keys()
        if "mutates_store" in registry.get(name).effects
    }


def test_document_exists_and_is_non_empty():
    path = _evidence_dir() / "F-07-MUTABLE-STORE-DISPOSITION.md"
    assert path.exists(), f"{path} does not exist"
    assert path.stat().st_size > 0, f"{path} is empty"


def test_document_re_renders_byte_identically():
    """A second run of the discharge is not a second finding."""
    registry = default_registry()
    rendered = render_f07_record(registry)
    assert rendered == _text()
    assert rendered == render_f07_record(registry)


def test_clause_and_finding_quoted_verbatim():
    text = _collapsed(_text())
    assert "mirroring `§4`'s `unbudgetable`-node exclusion from token comparisons" in text
    assert (
        "unless and until a snapshot/reset protocol is defined and the node is re-verified "
        "against it" in text
    )
    assert "`CA-2`" in text
    assert "`MC-1`" in text
    assert "`CA-7`" in text


def test_population_table_is_non_empty():
    text = _text()
    section = _section(text, r"^## Population and disposition")
    rows = _parse_markdown_table(section)
    assert len(rows) > 0


def test_enumerated_set_equals_live_registry_plus_catalogued_at_test_time():
    text = _text()
    section = _section(text, r"^## Population and disposition")
    rows = _parse_markdown_table(section)
    table_components = {row[0].strip("`") for row in rows}

    registry = default_registry()
    live = _live_mutates_store_names(registry)
    catalogued = {row.component for row in _CATALOGUED_NOT_BUILT}

    assert table_components == live | catalogued


def test_every_row_carries_an_admissible_disposition_and_non_empty_reason():
    text = _text()
    section = _section(text, r"^## Population and disposition")
    rows = _parse_markdown_table(section)
    assert len(rows) > 0
    for component, disposition, reason, tag in rows:
        assert disposition.strip("`") in _ADMISSIBLE_DISPOSITIONS, (
            f"{component!r} carries disposition {disposition!r}, not one of "
            f"{_ADMISSIBLE_DISPOSITIONS!r}"
        )
        assert reason.strip() != "", f"{component!r} carries an empty reason"
        assert tag.strip() != "", f"{component!r} carries an empty tag"


def test_live_component_strings_match_registry_name_at_version_exactly():
    """Component identity is compared as the exact ``name@version`` string the registry holds —
    never a case-folded, normalised, or display form (backstop must-have truth)."""
    text = _text()
    registry = default_registry()
    live = _live_mutates_store_names(registry)
    for name in live:
        assert f"`{name}`" in text, f"{name!r} not present verbatim (backtick-wrapped) in record"
        # A case-folded display variant must never silently stand in for the real string.
        upper_variant = f"`{name.upper()}`"
        assert upper_variant not in text or upper_variant == f"`{name}`", (
            f"a case-folded variant of {name!r} appears in the record"
        )


def test_empty_enumeration_is_refused_not_rendered(monkeypatch):
    """`An F-07 record enumerating zero mutable-store components is refused as incomplete rather
    than accepted as a discharge` (plan must-have truth 2) — proven directly against
    ``render_f07_record`` with both inputs forced empty, not merely observed as "the current
    table happens to be non-empty"."""
    import databasise.evidence.f07_report as f07_report

    monkeypatch.setattr(f07_report, "_CATALOGUED_NOT_BUILT", ())
    empty_registry = PartRegistry(seed_tracer_parts=False)  # no mutates_store parts at all

    with pytest.raises(ValueError, match="zero mutable-store components"):
        f07_report.render_f07_record(empty_registry)


def test_write_quiesce_caveat_recorded_as_not_established():
    text = _text()
    limits = _section(text, r"^## Method and limits")
    assert "not established" in limits.lower()


def test_interrupted_and_concurrent_guarantee_stated():
    """Backstop must-have truth: the recorded disposition states what is guaranteed if a
    comparison run is interrupted part-way through a snapshot or reset, or if two comparison
    runs touch the same mutable store concurrently."""
    text = _text()
    limits = _section(text, r"^## Method and limits")
    assert "interrupted" in limits.lower()
    assert "concurrent" in limits.lower() or "concurrently" in limits.lower()
    assert "guaranteed" in limits.lower()


def test_verdict_names_the_enforcing_refusal_and_the_unqualified_component():
    text = _text()
    verdict = _section(text, r"^## Verdict")
    assert "MutableStoreComparisonExcludedError" in verdict
    assert "lightrag/full-delete@0.1.0" in verdict

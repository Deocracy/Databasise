"""06-07-PLAN.md Task 3: structural assertions over
``databasise/evidence/HIPPORAG-PORT-RECORD.md``, so a future part that quietly gains an effect
fails this test as an unrecorded divergence rather than passing by omission. Mirrors
``tests/evidence/test_admission_docs.py``'s own section/table-parsing helpers (reused verbatim,
not reimplemented) so a doc-wide grep can never pass on an accidental mention.

The divergent-node set is computed at test time — the registry's own ``Part.effects`` compared
against a pinned transcription of ``PARTS.md ## §H``'s node table's own ``effects[] exercised``
column — never read off the record's own prose, so the record's own coverage claim is checked
against ground truth rather than against itself.
"""

from __future__ import annotations

import re
from pathlib import Path

from databasise.parts.registry import default_registry
from databasise.wirings.resolve import load_wiring


def _evidence_dir() -> Path:
    # databasise/tests/evidence/test_hipporag_port_record.py -> databasise/evidence/
    return Path(__file__).resolve().parent.parent.parent / "evidence"


def _record_text() -> str:
    return (_evidence_dir() / "HIPPORAG-PORT-RECORD.md").read_text(encoding="utf-8")


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
    table_lines = [line for line in section_text.splitlines() if line.strip().startswith("|")]
    assert len(table_lines) >= 3, f"expected a header + separator + rows, found {table_lines!r}"

    def _is_separator(line: str) -> bool:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        return all(re.fullmatch(r"-+", c) for c in cells)

    header, *rest = table_lines
    assert _is_separator(rest[0]), f"second table line is not a separator row: {rest[0]!r}"
    data_rows = rest[1:]

    return [[c.strip() for c in line.strip().strip("|").split("|")] for line in data_rows]


# PARTS.md ## §H's own node table, "effects[] exercised" column, pinned by transcription — the
# oracle this test computes the divergent-node set against, never the record's own prose.
_SECTION_H_EFFECTS: dict[str, frozenset[str]] = {
    "chunk-embed": frozenset({"calls_embedding"}),
    "openie": frozenset({"calls_llm"}),
    "entity-fact-embed": frozenset({"calls_embedding"}),
    "fact-edges": frozenset(),
    "passage-edges": frozenset(),
    "synonymy-edges": frozenset({"reads_vector"}),
    "graph-augment-persist": frozenset(),
    "fact-score": frozenset({"reads_vector"}),
    "fact-filter": frozenset({"calls_llm"}),
    "dpr-fallback": frozenset({"calls_embedding", "reads_vector"}),
    "reset-vector-join": frozenset({"reads_vector", "calls_embedding", "reads_kv"}),
    "ppr": frozenset({"reads_graph"}),
    "assemble-result": frozenset({"reads_kv"}),
}


def _computed_divergent_node_ids() -> set[str]:
    registry = default_registry()
    built = load_wiring("hipporag")
    divergent = set()
    for node_id, node in built["nodes"].items():
        part = registry.get(node["component"])
        if frozenset(part.effects) != _SECTION_H_EFFECTS[node_id]:
            divergent.add(node_id)
    return divergent


def test_pinned_transcription_covers_all_thirteen_node_ids():
    built = load_wiring("hipporag")
    assert set(_SECTION_H_EFFECTS) == set(built["nodes"].keys())


def test_reconciliation_table_covers_exactly_the_computed_divergent_node_set():
    text = _record_text()
    section = _section(text, r"^## The declared-effects reconciliation")
    rows = _parse_markdown_table(section)

    table_node_ids = {row[0].strip("`") for row in rows}
    assert table_node_ids == _computed_divergent_node_ids()


def test_reconciliation_table_each_row_carries_a_hash_h_value_a_built_value_and_a_reason():
    text = _record_text()
    section = _section(text, r"^## The declared-effects reconciliation")
    rows = _parse_markdown_table(section)

    for row in rows:
        node_id, section_h_value, built_value, reason = row
        assert section_h_value, f"{node_id}: empty '## §H declared' cell"
        assert built_value, f"{node_id}: empty 'Built declares' cell"
        assert reason.strip(), f"{node_id}: empty reason cell"


def test_findings_table_each_row_carries_an_evidence_class_tag():
    text = _record_text()
    findings = _section(text, r"^## The findings table")
    rows = _parse_markdown_table(findings)

    evidence_tags = ("[code-verified]", "[docs-verified]", "[inference]")
    for row in rows:
        evidence_cell = row[2]
        assert any(tag in evidence_cell for tag in evidence_tags), (
            f"row {row[0]!r} evidence cell carries none of {evidence_tags}: {evidence_cell!r}"
        )


def test_record_states_the_claim_under_test_verbatim():
    text = _record_text()
    assert (
        "HippoRAG 2 fully decomposed — thirteen node positions, no opaque core left behind" in text
    )


def test_record_names_the_guard_placement_row():
    text = _record_text()
    assert "guard-placement" in text.lower()
    assert "config.guards" in text
    assert "config_hash" in text


def test_record_names_the_guard_observability_row():
    text = _record_text()
    assert "guard-observability" in text.lower()
    assert "guards_fired" in text
    assert "degraded" in text.lower()


def test_record_names_the_nearest_signature_typing_row():
    text = _record_text()
    assert "nearest signature" in text.lower()
    assert "fact-score" in text
    assert "graph-augment-persist" in text


def test_limits_section_names_the_unrun_upstream_parity_measurement_and_states_the_deferral():
    text = _record_text()
    limits = _section(text, r"^## Limits")
    assert "hipporag" in limits.lower()
    assert "parity" in limits.lower()
    assert "opaque" in limits.lower()
    assert "06-09" in limits


def test_record_document_exists_and_is_non_empty():
    path = _evidence_dir() / "HIPPORAG-PORT-RECORD.md"
    assert path.exists(), f"{path} does not exist"
    assert path.stat().st_size > 0, f"{path} is empty"

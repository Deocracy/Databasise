"""05-06-PLAN.md Task 3: structural assertions over
``databasise/evidence/FALSIFIER-4-EVIDENCE.md`` (both legs present, the native leg's table carries
one row per ``ChunkRef`` field, the machine-chunks leg carries a disposition value, a verdict
section exists), plus a live re-run of the native leg guarded by a binary-present skip, so the
recorded numbers are reproducible rather than a one-time transcription — mirrors
``tests/evidence/test_admission_docs.py``'s own parse-the-actual-structure discipline, never a
whole-file grep.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from databasise.foreign import codebase_memory_mcp_adapter as adapter
from databasise.foreign._mcp_sdk_guard import mcp_sdk_is_installed

# A live-engine test needs both the binary AND the `mcp` extra (lazily imported by the adapter —
# see that module's own docstring for why importing it never requires the extra, only calling it
# does). Checking only the binary would let this skip fall through to a bare ModuleNotFoundError
# on a `uv run pytest -q` with no extras installed but the binary present on PATH.
# `mcp_sdk_is_installed()` (never a bare `importlib.util.find_spec("mcp")` — 05-07-PLAN.md's own
# fix, Rule 1) is shadow-safe against `databasise/mcp/`, a sibling package added by that same plan
# that shares the SDK's own top-level name.
_MCP_INSTALLED = mcp_sdk_is_installed()


def _evidence_dir() -> Path:
    # databasise/tests/evidence/test_falsifier4_evidence.py -> databasise/evidence/
    return Path(__file__).resolve().parent.parent.parent / "evidence"


def _text() -> str:
    return (_evidence_dir() / "FALSIFIER-4-EVIDENCE.md").read_text(encoding="utf-8")


def _collapsed(text: str) -> str:
    """Collapses markdown line-wrapping whitespace (and strips leading ``> `` blockquote markers)
    so a substring assertion is not tripped up by where a prose paragraph or a quoted block
    happens to wrap — the document's own hard-wrapped line breaks are a rendering choice, not part
    of the claim being asserted."""
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


def test_document_exists_and_is_non_empty():
    path = _evidence_dir() / "FALSIFIER-4-EVIDENCE.md"
    assert path.exists(), f"{path} does not exist"
    assert path.stat().st_size > 0, f"{path} is empty"


def test_falsifier_text_is_quoted_verbatim():
    text = _collapsed(_text())
    assert "run twice on `codebase-memory-mcp`" in text
    assert "`ChunkRef` cannot be constructed from an opaque part's output under any feed strategy" in text


def test_leg_1_native_chunking_section_exists_with_a_real_measured_duration():
    text = _text()
    leg1 = _section(text, r"^## Leg 1")
    assert "Duration" in leg1
    assert re.search(r"\d+\.\d+s", leg1), "leg 1 must record a real, non-placeholder duration"


def test_leg_1_table_carries_one_row_per_chunkref_field():
    text = _text()
    leg1 = _section(text, r"^## Leg 1")
    per_field_heading_idx = leg1.index("Per-field")
    rows = _parse_markdown_table(leg1[per_field_heading_idx:])
    field_names = [row[0].strip("`") for row in rows]
    assert field_names == ["corpus_id", "recipe@version", "ordinal", "content_hash"], field_names

    # Every disposition cell states supplied, derived, or unavailable — never left blank.
    for row in rows:
        disposition_cell = row[-1]
        assert re.search(
            r"[Ss]upplied|[Dd]erived|[Cc]annot be supplied|not supplied", disposition_cell
        ), f"row for {row[0]!r} has no supplied/derived/unavailable disposition: {disposition_cell!r}"


def test_leg_1_records_the_resulting_evidence_tier():
    text = _text()
    leg1 = _section(text, r"^## Leg 1")
    assert "below_T1" in leg1


def test_leg_2_machine_chunks_carries_a_disposition_and_the_section_x5_structural_reason():
    text = _text()
    leg2 = _collapsed(_section(text, r"^## Leg 2"))
    assert "not runnable as worded" in leg2
    assert (
        "the two-leg design may not distinguish two genuinely different code paths at all"
        in leg2
    )
    assert "§X.5" in leg2 or "X.5" in leg2


def test_verdict_section_exists_and_states_what_falsifier_4_calibrates():
    text = _text()
    verdict = _section(text, r"^## Verdict")
    assert "calibrates" in verdict
    assert "not refuted" in verdict
    assert "does not halt the ladder" in verdict


@pytest.mark.skipif(
    adapter.DEFAULT_CBM_BINARY is None or not _MCP_INSTALLED,
    reason=(
        f"codebase-memory-mcp binary not found (DEFAULT_CBM_BINARY={adapter.DEFAULT_CBM_BINARY!r}) "
        f"or the 'mcp' extra is not installed (found={_MCP_INSTALLED})"
    ),
)
def test_the_native_leg_is_reproducible_live_get_code_snippet_still_derives_a_content_hash():
    """Re-runs the concrete claim leg 1's table makes for ``get_code_snippet`` — a real
    call against this repository's own source produces a real, machine-resolvable
    ``file_path``/``line_range`` ref with a derived ``content_hash``, and the item is still
    tier-capped ``below_T1`` (missing ``recipe@version``/``ordinal``) — so the recorded numbers
    are reproducible, not a one-time transcription."""
    project_root = Path(__file__).resolve().parents[3]
    repo_arg = str(project_root / "databasise")

    adapter.call_tool("index_repository", {"repo_path": repo_arg}, timeout=120.0)

    tools = adapter.list_tools(timeout=60.0)
    assert {tool["name"] for tool in tools} >= {"search_graph", "get_code_snippet", "search_code"}

    graph_items = adapter.call_tool(
        "search_graph",
        {"project": _resolved_project_name(project_root), "query": "codebase_memory_mcp_body"},
        timeout=60.0,
    )
    assert graph_items, "search_graph returned no results for a symbol this repo actually defines"
    first = graph_items[0]
    qualified_name = first.get("qn")
    assert qualified_name

    snippet_items = adapter.call_tool(
        "get_code_snippet",
        {"project": _resolved_project_name(project_root), "qualified_name": qualified_name},
        timeout=60.0,
    )
    assert snippet_items
    record = adapter.normalise_to_item_kind(snippet_items[0], "get_code_snippet")
    assert record["kind"] == adapter.ITEM_KIND_CODE_SNIPPET
    assert record["tier"] == "below_T1"
    assert record["ref"] is not None
    assert record["ref"]["chunk_ref"]["content_hash"], "content_hash must be derived from source"
    assert record["ref"]["chunk_ref"]["recipe_at_version"] is None
    assert record["ref"]["chunk_ref"]["ordinal"] is None


def _resolved_project_name(project_root: Path) -> str:
    """codebase-memory-mcp derives its own project name from the indexed repo_path — mirrors the
    convention observed live this session (a slugified absolute path), so this test's ``project``
    argument matches what ``index_repository`` actually registered."""
    parts = [p for p in (project_root / "databasise").parts if p not in ("/",)]
    return "-".join(parts).lstrip("-")

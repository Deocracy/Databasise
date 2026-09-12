"""07-03-PLAN.md Task 3: asserts ``databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md``'s own claims
against the code, following ``tests/evidence/test_f14_record.py``'s parse-the-actual-structure
discipline. Every row of the document's "Criteria" table marked "Holds" must name a pytest node id
that is genuinely collectible — this is what keeps the document from drifting into a claim no test
supports, the exact vacuous-pass failure mode HARD-01 was filed against, applied here to this
phase's own record.

Deliberately checks collectibility via a real ``pytest --collect-only`` subprocess, not an
``importlib``/``getattr`` proxy — the acceptance criterion is stated in terms of what pytest itself
can collect, and the two are not always equivalent (a node id inside a module gated by
``pytest.importorskip`` reports "found no collectors" under ``--collect-only`` when the optional
extra is absent, which a bare "does the function exist" check would miss entirely). The document's
own "Criteria" table cites only extras-free test files for exactly this reason — see the document's
own "Method and limits" section.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def _evidence_dir() -> Path:
    # databasise/tests/evidence/test_promotion_ledger_record.py -> databasise/evidence/
    return Path(__file__).resolve().parent.parent.parent / "evidence"


def _databasise_root() -> Path:
    # databasise/tests/evidence/test_promotion_ledger_record.py -> databasise/
    return Path(__file__).resolve().parent.parent.parent


def _text() -> str:
    return (_evidence_dir() / "PROMOTION-LEDGER-EVIDENCE.md").read_text(encoding="utf-8")


def _section(text: str, heading_pattern: str) -> str:
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


def _extract_node_ids(cell: str) -> list[str]:
    """Every backtick-quoted node id (containing ``::``) in a table cell."""
    return [match for match in re.findall(r"`([^`]+::[^`]+)`", cell)]


def test_document_exists_and_is_non_empty():
    path = _evidence_dir() / "PROMOTION-LEDGER-EVIDENCE.md"
    assert path.exists(), f"{path} does not exist"
    assert path.stat().st_size > 0, f"{path} is empty"


def test_document_carries_a_dated_header():
    text = _text()
    header = "\n".join(text.splitlines()[:6])
    assert re.search(r"\*\*Date:\*\*\s*\d{4}-\d{2}-\d{2}", header), (
        f"no dated header found near the top of the document: {header!r}"
    )


def test_criteria_table_has_one_row_per_roadmap_success_criterion():
    text = _text()
    criteria = _section(text, r"^## Criteria")
    rows = _parse_markdown_table(criteria)
    assert len(rows) == 3, f"expected exactly 3 criteria rows (ROADMAP Phase 7's 1-3), found {rows!r}"
    numbers = [row[0] for row in rows]
    assert numbers == ["1", "2", "3"], f"criteria rows are not numbered 1-3 in order: {numbers!r}"


def test_document_cites_the_gate_amendment_and_states_criteria_4_and_5_are_struck_and_deferred():
    text = _text()
    assert "07-GATE-AMENDMENT.md" in text
    assert "criteria 4 and 5" in text.lower() or "criteria 4-5" in text.lower()
    assert "struck" in text.lower()
    assert "deferred" in text.lower()
    for req_id in ("HARD-04", "HARD-01", "HARD-02"):
        assert req_id in text, f"{req_id} not named in the document's deferral restatement"


def test_document_states_every_promotion_is_operator_asserted_provisional_and_carries_no_verdict():
    text = _text()
    lowered = text.lower()
    assert "operator-asserted" in lowered or "operator_asserted" in lowered
    assert "provisional" in lowered
    assert "no verdict" in lowered or "carries no verdict" in lowered


def test_every_holding_criterion_names_a_pytest_node_id_that_is_actually_collectible():
    """The load-bearing test: parses the "Criteria" table, and for every row marked "Holds",
    asserts every cited node id is collected cleanly by a real `pytest --collect-only` subprocess
    — never merely that the function exists in the module (see this module's own docstring for why
    the two are not equivalent under an extras-gated module)."""
    text = _text()
    criteria = _section(text, r"^## Criteria")
    rows = _parse_markdown_table(criteria)
    assert rows

    holding_rows = [row for row in rows if row[2].strip().lower() == "holds"]
    assert holding_rows, "no row in the Criteria table is marked 'Holds' — nothing to verify"

    all_node_ids: list[str] = []
    for row in holding_rows:
        node_ids = _extract_node_ids(row[3])
        assert node_ids, f"criterion {row[0]!r} is marked 'Holds' but names no pytest node id: {row}"
        all_node_ids.extend(node_ids)

    root = _databasise_root()
    for node_id in all_node_ids:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", node_id],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"{node_id!r} is not collectible (exit {result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "1 test collected" in result.stdout, (
            f"{node_id!r} did not report exactly one collected test:\n{result.stdout}"
        )


def test_verdict_section_names_criteria_1_2_and_3_as_holding():
    text = _text()
    verdict = _section(text, r"^## Verdict")
    assert "1, 2 and 3" in verdict or "1-3" in verdict or "1, 2, 3" in verdict
    assert "hold" in verdict.lower()

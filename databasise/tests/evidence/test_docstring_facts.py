"""TOOL-20 row tests: module and data docstrings state current facts.

One node per lane: the parity modules (fixed by 15-14 and 15-15), the MCP package (15-07), the
evidence package and records, and the registry/refusal docstrings (15-17). Each forbidden phrase is
built from parts so this file never matches its own search. Source and data files are read as text,
so no node needs an optional extra, and every outcome is a plain assertion (the file collects on the
phase base, where the lanes it checks are still stale).
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

_PKG = Path(__file__).resolve().parent.parent.parent
_EVIDENCE = _PKG / "evidence"


def _text(*parts: str) -> str:
    return _PKG.joinpath(*parts).read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(re.sub(r"(?m)^>\s?", "", text).split())


def test_no_parity_module_says_it_was_never_run_for_real():
    phrase = "has not been " + "invoked for real"
    for name in ("build_hipporag_index.py", "run_cross_modality.py"):
        assert phrase not in _flat(_text("parity", name)), f"parity/{name} still says {phrase!r}"


def test_the_never_invoked_findings_row_is_marked_superseded():
    text = _text("evidence", "CROSS-MODALITY-EVIDENCE.md")
    start = text.index("\n## Findings")
    end = text.index("\n## ", start + 1)
    rows = [ln for ln in text[start:end].splitlines() if ln.startswith("| ") and "never invoked" in ln]
    assert len(rows) == 1, f"expected the one never-invoked row, found {len(rows)}"
    assert "uperseded" in rows[0], "the never-invoked row is not marked superseded"
    assert "2026-09-10" in rows[0], "the row does not name the 2026-09-10 section"


def test_the_evidence_package_docstring_names_its_modules():
    import databasise.evidence as evidence

    doc = evidence.__doc__ or ""
    for name in ("falsifier2", "parity_report", "f07_report", "parity_results", "eval-bundles"):
        assert name in doc, f"databasise.evidence.__doc__ does not mention {name}"


def test_no_machine_chunk_leg_is_claimed():
    phrase = "once consuming " + "machine-produced chunks"
    wiring = json.loads(_text("evidence", "wirings", "w2-codebase-memory-mcp.json"))
    rationale = " ".join(knob["rationale"] for knob in wiring["boundary_knobs"])
    assert phrase not in rationale, "the w2 rationale still claims a machine-chunk leg"
    assert "FALSIFIER-4-EVIDENCE.md" in rationale, "the rationale does not cite Falsifier 4"
    assert phrase not in _flat(_text("evidence", "FALSIFIER-2-EVIDENCE.md"))


def test_the_mcp_lane_states_current_facts():
    old = "different declared effect, ``mutates_store`` " + "vs ``writes_artifact``"
    tools = _flat(_text("mcp", "tools.py"))
    assert old not in tools, "mcp/tools.py still contrasts mutates_store with writes_artifact"
    assert "both corpus ports declare ``mutates_store``" in tools
    assert "TOOL_NAMES" in _text("mcp", "__init__.py").split('"""')[1]


def test_the_registry_lane_states_current_facts():
    import databasise.seam.refusals as refusals

    f2 = _text("evidence", "falsifier2.py")
    old = 'getattr(part, "artifact_scope", ' + '"shared")'
    assert old not in f2, "falsifier2.py still describes the getattr default"
    assert 'artifact_scope or "shared"' in f2

    doc = inspect.getdoc(refusals.MutableStoreComparisonExcludedError) or ""
    assert "test_refusal_reachability.py" in doc
    assert "test_mutable_store_exclusion.py" in doc
    assert "unreachable" in doc


def test_the_env_loader_docstrings_do_not_cite_a_deleted_helper():
    deleted = "v1_arm.py``'s own ``" + "_load_env_file"
    for rel in (("clients", "builder.py"), ("foreign", "v1_corpus_adapter.py")):
        assert deleted not in _flat(_text(*rel)), f"{'/'.join(rel)} cites the deleted v1_arm copy"

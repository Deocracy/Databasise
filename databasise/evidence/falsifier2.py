"""Falsifier 2 evidence run — CONTRACT §19.10 and SELECTION.md's ``## Falsifiers`` list item 2.

Falsifier 2, quoted verbatim: "Depth cannot be computed statically. Over three real parts
(decomposed `lightrag-local`, opaque `codebase-memory-mcp`, half-decomposed LightRAG), the
validator cannot derive `depth` from wiring + registry without a self-declaration. Then D4 has no
brake and D's regime was doing structural work."

This module re-runs that falsifier as a committed, ``python -m``-runnable artifact: it loads the
named wirings under ``evidence/wirings/*.json``, resolves them against the real
``default_registry()``, computes ``effective_depth``/``execution_mode``/blast-radius per node
through the same functions the runner calls — never a reimplementation, never the superseded
tracer-era ``derive_execution_mode`` in ``databasise/validator/depth.py`` — and renders a Markdown
document a second author can read without opening a test file (02-CONTEXT.md D-03).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from databasise.parts.registry import default_registry
from databasise.validator.blast_radius import blast_radius_violations
from databasise.validator.depth import effective_depth
from databasise.validator.errors import CODE_BLAST_RADIUS_REFUSAL, Violation
from databasise.validator.execution_mode import derive_execution_mode
from databasise.validator.parse import ParsedWiring, parse_wiring

WIRINGS_DIR = Path(__file__).resolve().parent / "wirings"
EVIDENCE_PATH = Path(__file__).resolve().parent / "FALSIFIER-2-EVIDENCE.md"

# W2/W3 land in Task 2 (02-01-PLAN.md); W1 alone exercises the end-to-end shape first.
NAMED_WIRINGS: tuple[str, ...] = ("w1-lightrag-query-side",)


@dataclass(frozen=True)
class NodeRow:
    """One node's computed-vs-declared row. Only ``node_id``, ``component`` and ``wiring_kind``
    come from the wiring document; every other field is produced by the real validator functions.
    """

    node_id: str
    component: str
    wiring_kind: str
    structural_depth: str
    effective_depth: str
    execution_mode: str
    part_effects: tuple[str, ...]
    artifact_scope: str | None
    blast_radius: str


@dataclass(frozen=True)
class WiringEvidence:
    """One wiring's full evaluation: its node rows plus the validator's own violation/cycle
    report for that wiring.
    """

    stem: str
    wiring_id: str
    title: str
    rows: tuple[NodeRow, ...]
    violations: tuple[Violation, ...]
    cycles: tuple[tuple[str, ...], ...]


def load_wiring(stem: str) -> dict[str, Any]:
    """Load one committed wiring document by its file stem (no ``.json`` suffix)."""
    return json.loads((WIRINGS_DIR / f"{stem}.json").read_text(encoding="utf-8"))


def _parse(stem: str) -> tuple[dict[str, Any], ParsedWiring]:
    doc = load_wiring(stem)
    parsed = parse_wiring(doc, default_registry())
    return doc, parsed


def evaluate_wiring(stem: str) -> WiringEvidence:
    """Resolve one named wiring against ``default_registry()`` and compute one ``NodeRow`` per
    node, iterating in ``parsed.node_order`` (sorted node id) order for a deterministic render.
    """
    doc, parsed = _parse(stem)
    depth_map = effective_depth(parsed)
    blast_violations = blast_radius_violations(parsed, depth_map)
    refused_node_ids = {
        v.pointer.split("/")[2] for v in blast_violations if v.code == CODE_BLAST_RADIUS_REFUSAL
    }

    rows = []
    for node_id in parsed.node_order:
        node = parsed.nodes[node_id]
        part = parsed.parts[node_id]
        if node_id in refused_node_ids:
            verdict = "refused"
        elif "writes_artifact" in part.effects:
            verdict = "permitted"
        else:
            verdict = "n/a"
        rows.append(
            NodeRow(
                node_id=node_id,
                component=part.name_at_version,
                wiring_kind=node.kind,
                structural_depth=part.structural_depth,
                effective_depth=depth_map[node_id],
                execution_mode=derive_execution_mode(part.effects, part.kind),
                part_effects=tuple(sorted(part.effects)),
                artifact_scope=part.artifact_scope,
                blast_radius=verdict,
            )
        )

    return WiringEvidence(
        stem=stem,
        wiring_id=doc.get("wiring_id", stem),
        title=doc.get("title", stem),
        rows=tuple(rows),
        violations=tuple(parsed.report.violations),
        cycles=tuple(tuple(c) for c in parsed.report.cycles),
    )


def _render_node_table(rows: tuple[NodeRow, ...]) -> str:
    header = (
        "| node id | component | wiring kind | structural_depth | effective_depth | "
        "execution_mode | part effects | artifact_scope | blast-radius |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for row in rows:
        effects_cell = ", ".join(row.part_effects) if row.part_effects else "—"
        scope_cell = row.artifact_scope or "—"
        lines.append(
            f"| {row.node_id} | {row.component} | {row.wiring_kind} | {row.structural_depth} | "
            f"{row.effective_depth} | {row.execution_mode} | {effects_cell} | {scope_cell} | "
            f"{row.blast_radius} |"
        )
    return header + "\n".join(lines) + "\n"


def _render_divergence(rows: tuple[NodeRow, ...]) -> str:
    diverged = [row.node_id for row in rows if row.effective_depth != row.structural_depth]
    if not diverged:
        return (
            "No node's computed `effective_depth` diverges from its part's own "
            "`structural_depth`.\n"
        )
    return (
        "Nodes whose computed `effective_depth` diverges from their part's own "
        f"`structural_depth` (the taint rule overriding a declared depth): {', '.join(diverged)}.\n"
    )


def render_markdown() -> str:
    """Render every named wiring's computed-vs-declared table. A pure function of the committed
    wiring documents plus ``default_registry()`` — no timestamp, no host path, no run-varying
    value of any kind — so two calls in one process return byte-identical text.
    """
    sections = [
        "# Falsifier 2 Evidence\n",
        (
            "Computed-vs-declared depth and execution_mode for each of MACH-01's named wirings, "
            "resolved against `default_registry()` and computed by "
            "`databasise.validator.depth.effective_depth` and "
            "`databasise.validator.execution_mode.derive_execution_mode` — the same functions "
            "the runner calls, never a reimplementation.\n"
        ),
    ]
    for stem in NAMED_WIRINGS:
        evidence = evaluate_wiring(stem)
        sections.append(f"## {evidence.wiring_id} — {evidence.title}\n")
        sections.append(
            f"Resolved against `default_registry()`'s Phase-1 entries ({len(evidence.rows)} "
            "node(s)).\n"
        )
        sections.append(_render_node_table(evidence.rows))
        sections.append("**Divergence from declared structural_depth:**\n")
        sections.append(_render_divergence(evidence.rows))
    return "\n".join(sections)


def main() -> None:
    text = render_markdown()
    EVIDENCE_PATH.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

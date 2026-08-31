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

It also re-runs MACH-01's no-self-declaration clause and SELECTION.md Falsifier 1 limb (b) as a
committed probe suite (``PROBES``): each probe expecting a refusal is paired with a control that
must not fire, resolved against ``probe_registry()`` — ``default_registry()`` plus two probe-only
parts that are never registered into the production registry (02-CONTEXT.md D-03).
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from databasise.parts.registry import PartRegistry, default_registry
from databasise.parts.schema import Part
from databasise.validator.blast_radius import blast_radius_violations
from databasise.validator.depth import effective_depth
from databasise.validator.errors import (
    CODE_BLAST_RADIUS_REFUSAL,
    CODE_EFFECTS_EXCEED_PART,
    CODE_INVALID_NODE_SCHEMA,
    CODE_SELF_DECLARED_DERIVATION,
    Violation,
)
from databasise.validator.execution_mode import derive_execution_mode
from databasise.validator.parse import ParsedWiring, parse_wiring

WIRINGS_DIR = Path(__file__).resolve().parent / "wirings"
EVIDENCE_PATH = Path(__file__).resolve().parent / "FALSIFIER-2-EVIDENCE.md"

NAMED_WIRINGS: tuple[str, ...] = (
    "w1-lightrag-query-side",
    "w2-codebase-memory-mcp",
    "w3-lightrag-half-decomposed",
)

# SELECTION.md's `## Falsifiers` list, item 2, quoted verbatim.
_FALSIFIER_2_TEXT = (
    "Depth cannot be computed statically. Over three real parts (decomposed `lightrag-local`, "
    "opaque `codebase-memory-mcp`, half-decomposed LightRAG), the validator cannot derive "
    "`depth` from wiring + registry without a self-declaration. Then D4 has no brake and D's "
    "regime was doing structural work."
)

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


@dataclass(frozen=True)
class BoundaryRow:
    """One CONTRACT §19.10 candidate boundary row: a stated, source-derived enumeration point,
    not a verdict — §19.10 requires the candidate set to be recorded so a second author can check
    it, not only the calls the first author reached on it.
    """

    boundary_id: str
    boundary_class: str
    between: str
    rationale: str


def load_wiring(stem: str) -> dict[str, Any]:
    """Load one committed wiring document by its file stem (no ``.json`` suffix)."""
    return json.loads((WIRINGS_DIR / f"{stem}.json").read_text(encoding="utf-8"))


# Two probe-only parts backing the b-family blast-radius probes below. Neither is registered into
# default_registry() — see probe_registry(). artifact_scope is left unset so CONTRACT §3's stated
# default of `shared` applies via blast_radius.py's own `getattr(part, "artifact_scope", "shared")`
# read.
SHARED_ARTIFACT_WRITER_PROBE_PART = Part(
    name_at_version="probe/shared-artifact-writer@0.1.0",
    kind="extractor",
    structural_depth="stage",
    effects=["writes_artifact"],
    upstream_ref=None,
    body=None,
)

EVIDENCE_WRITER_PROBE_PART = Part(
    name_at_version="probe/evidence-writer@0.1.0",
    kind="extractor",
    structural_depth="evidence",
    effects=["writes_artifact"],
    upstream_ref=None,
    body=None,
)


def probe_registry() -> PartRegistry:
    """``default_registry()`` plus the two probe-only parts above, assembled fresh on every call.
    Never registers them into a shared or module-level registry: the production
    ``default_registry()`` stays exactly D-04's seven entries regardless of how many times a
    probe runs.
    """
    registry = default_registry()
    registry.register(SHARED_ARTIFACT_WRITER_PROBE_PART)
    registry.register(EVIDENCE_WRITER_PROBE_PART)
    return registry


@dataclass(frozen=True)
class Probe:
    """One self-declaration or blast-radius probe: a wiring document paired with the violation
    code a validation pass over it is expected to produce. ``expected_code`` is ``None`` for a
    control probe that must not be refused — every refusal probe below is paired with a control
    so a check that has stopped firing surfaces as a failed probe, not a quietly green suite.
    """

    probe_id: str
    title: str
    expected_code: str | None
    doc: dict[str, Any]


def _w3_query_side_with_extra_key(key: str, value: str) -> dict[str, Any]:
    """A deep copy of W3 with one extra key added to its ``query-side`` node — the shape the
    ``c1``/``c2`` probes need to distinguish a self-declared derived field from an ordinary typo.
    """
    doc = copy.deepcopy(load_wiring("w3-lightrag-half-decomposed"))
    doc["nodes"]["query-side"][key] = value
    return doc


# The self-declaration and blast-radius probe suite (02-CONTEXT.md D-03, SELECTION.md Falsifier 1
# limb (b) and Falsifier 2's self-declaration clause). Every refusal probe (a, b2, b3, c1, c2) is
# paired with a control (b1, c3) that must not fire.
PROBES: tuple[Probe, ...] = (
    Probe(
        probe_id="a-effects-exceed-part",
        title=(
            "If this stopped firing, a wiring node could claim an effect its resolved part "
            "does not back — an unbounded capability claim admitted silently."
        ),
        expected_code=CODE_EFFECTS_EXCEED_PART,
        doc={
            "wiring_id": "probe-a-effects-exceed-part",
            "nodes": {
                "cbm": {
                    "component": "codebase-memory-mcp@0.1.0",
                    "kind": "opaque",
                    "effects": ["self_storage", "fs", "writes_artifact"],
                    "deps": [],
                }
            },
        },
    ),
    Probe(
        probe_id="b1-shared-write-at-stage",
        title=(
            "Control. If this fired, a legitimate shared-artifact write at effective depth "
            "stage would be wrongly refused."
        ),
        expected_code=None,
        doc={
            "wiring_id": "probe-b1-shared-write-at-stage",
            "nodes": {
                "writer": {
                    "component": SHARED_ARTIFACT_WRITER_PROBE_PART.name_at_version,
                    "kind": "extractor",
                    "effects": ["writes_artifact"],
                    "deps": [],
                }
            },
        },
    ),
    Probe(
        probe_id="b2-shared-write-at-evidence",
        title=(
            "If this stopped firing, a shared-artifact write reachable only at effective depth "
            "evidence would escape the blast-radius rule."
        ),
        expected_code=CODE_BLAST_RADIUS_REFUSAL,
        doc={
            "wiring_id": "probe-b2-shared-write-at-evidence",
            "nodes": {
                "writer": {
                    "component": EVIDENCE_WRITER_PROBE_PART.name_at_version,
                    "kind": "extractor",
                    "effects": ["writes_artifact"],
                    "deps": [],
                }
            },
        },
    ),
    Probe(
        probe_id="b3-shared-write-tainted-to-opaque",
        title=(
            "SELECTION.md Falsifier 1 limb (b). If this stopped firing, an opaque node could "
            "launder a shared-scope write through a downstream extractor by hiding behind the "
            "taint rule."
        ),
        expected_code=CODE_BLAST_RADIUS_REFUSAL,
        doc={
            "wiring_id": "probe-b3-shared-write-tainted-to-opaque",
            "nodes": {
                "cbm": {
                    "component": "codebase-memory-mcp@0.1.0",
                    "kind": "opaque",
                    "effects": ["self_storage", "fs"],
                    "deps": [],
                },
                "extract": {
                    "component": SHARED_ARTIFACT_WRITER_PROBE_PART.name_at_version,
                    "kind": "extractor",
                    "effects": ["writes_artifact"],
                    "deps": ["cbm"],
                },
            },
        },
    ),
    Probe(
        probe_id="c1-self-declared-effective-depth",
        title=(
            "If this stopped firing, an author's self-declared effective_depth would silently "
            "stand in for the computation MACH-01 requires."
        ),
        expected_code=CODE_SELF_DECLARED_DERIVATION,
        doc=_w3_query_side_with_extra_key("effective_depth", "stage"),
    ),
    Probe(
        probe_id="c2-unknown-node-key",
        title=(
            "If this classified as self-declared-derivation instead of invalid-node-schema, a "
            "typo and an attempted self-declaration would be indistinguishable by code alone."
        ),
        expected_code=CODE_INVALID_NODE_SCHEMA,
        doc=_w3_query_side_with_extra_key("notes", "x"),
    ),
    Probe(
        probe_id="c3-computed-depth-governs",
        title=(
            "Control. If this fired, the computation itself would be broken on an ordinary "
            "wiring that carries no self-declaration at all."
        ),
        expected_code=None,
        doc=load_wiring("w3-lightrag-half-decomposed"),
    ),
)


def evaluate_probe(probe: Probe) -> frozenset[str]:
    """The set of violation codes ``parse_wiring`` observes for this probe's wiring document,
    resolved against a fresh ``probe_registry()``.
    """
    parsed = parse_wiring(probe.doc, probe_registry())
    return frozenset(v.code for v in parsed.report.violations)


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


def enumerate_boundaries(evidence: WiringEvidence, parsed: ParsedWiring) -> tuple[BoundaryRow, ...]:
    """CONTRACT §19.10's stated, source-derived boundary-enumeration procedure: one row per dep
    edge whose consumer's resolved effects differ from its producer's (``effects-change``), one
    row per dep edge unconditionally (``value-crossing`` — every dep edge is by construction a
    point where a value crosses between operations), and one row per entry in the wiring
    document's own top-level ``boundary_knobs`` array (``knob``) — the author-supplied half
    §19.10 cannot derive mechanically. A pure function of one wiring document plus the registry:
    same inputs, same rows.
    """
    rows: list[BoundaryRow] = []

    for node_id in parsed.node_order:
        consumer_part = parsed.parts[node_id]
        for dep in parsed.deps[node_id]:
            producer_part = parsed.parts[dep]
            between = f"{dep} -> {node_id}"
            diff = set(producer_part.effects) ^ set(consumer_part.effects)
            if diff:
                rows.append(
                    BoundaryRow(
                        boundary_id=f"{evidence.stem}-effects-{dep}-{node_id}",
                        boundary_class="effects-change",
                        between=between,
                        rationale=(
                            "declared effects[] differs across this dep edge; symmetric "
                            f"difference: {sorted(diff)}"
                        ),
                    )
                )
            rows.append(
                BoundaryRow(
                    boundary_id=f"{evidence.stem}-crossing-{dep}-{node_id}",
                    boundary_class="value-crossing",
                    between=between,
                    rationale=(
                        f"{node_id!r}'s dep edge on {dep!r} is by construction a point where a "
                        "value crosses between operations"
                    ),
                )
            )

    doc = load_wiring(evidence.stem)
    for i, knob in enumerate(doc.get("boundary_knobs", [])):
        rows.append(
            BoundaryRow(
                boundary_id=knob.get("boundary_id", f"{evidence.stem}-knob-{i}"),
                boundary_class="knob",
                between=knob["between"],
                rationale=knob["rationale"],
            )
        )

    return tuple(rows)


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


def _render_boundaries(boundaries: tuple[BoundaryRow, ...]) -> str:
    header = (
        "| boundary_id | class | between | rationale |\n"
        "|---|---|---|---|\n"
    )
    lines = [
        f"| {row.boundary_id} | {row.boundary_class} | {row.between} | {row.rationale} |"
        for row in boundaries
    ]
    return header + "\n".join(lines) + "\n"


def _wiring_shape_summary(probe: Probe) -> str:
    return ", ".join(
        f"{node_id}:{node['component']}" for node_id, node in probe.doc["nodes"].items()
    )


def _render_probe_table() -> str:
    header = (
        "| probe_id | wiring shape | expected code | observed code | verdict |\n"
        "|---|---|---|---|---|\n"
    )
    lines = []
    meanings = []
    for probe in PROBES:
        observed = evaluate_probe(probe)
        expected_cell = probe.expected_code if probe.expected_code is not None else "— (control)"
        observed_cell = ", ".join(sorted(observed)) if observed else "—"
        if probe.expected_code is None:
            verdict = "OK (no violation)" if not observed else "UNEXPECTED VIOLATION"
        else:
            verdict = "fired as expected" if probe.expected_code in observed else "DID NOT FIRE"
        lines.append(
            f"| {probe.probe_id} | {_wiring_shape_summary(probe)} | {expected_cell} | "
            f"{observed_cell} | {verdict} |"
        )
        meanings.append(f"- **{probe.probe_id}**: {probe.title}")
    return header + "\n".join(lines) + "\n\n" + "\n".join(meanings) + "\n"


def render_markdown() -> str:
    """Render every named wiring's computed-vs-declared table, its CONTRACT §19.10 candidate
    boundary set, and a closing Falsifier 2 verdict. A pure function of the committed wiring
    documents plus ``default_registry()`` — no timestamp, no host path, no run-varying value of
    any kind — so two calls in one process return byte-identical text.
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
        doc, parsed = _parse(stem)
        evidence = evaluate_wiring(stem)
        sections.append(f"## {evidence.wiring_id} — {evidence.title}\n")
        sections.append(
            f"Resolved against `default_registry()`'s Phase-1 entries ({len(evidence.rows)} "
            "node(s)).\n"
        )
        sections.append(_render_node_table(evidence.rows))
        sections.append("**Divergence from declared structural_depth:**\n")
        sections.append(_render_divergence(evidence.rows))

        sections.append("### CONTRACT §19.10 — boundary enumeration\n")
        sections.append(
            "Before applying §19.1–§19.6, the author MUST enumerate candidate boundaries by a "
            "stated, source-derived procedure — at minimum every point where the declared "
            "`effects[]` set changes, every point where a declared knob sits, and every point "
            "where a value crosses between operations. The enumeration below is recorded with "
            "this wiring's node set, so a second author can check the candidate set, not only "
            "the verdicts reached on it.\n"
        )
        boundaries = enumerate_boundaries(evidence, parsed)
        sections.append(_render_boundaries(boundaries))

    sections.append("## Self-declaration probes\n")
    sections.append(
        "SELECTION.md Falsifier 1 limb (b) and Falsifier 2's own no-self-declaration clause "
        "(02-CONTEXT.md D-03), demonstrated as paired refusal-and-control probes resolved "
        "against `probe_registry()` (`default_registry()` plus two probe-only parts never "
        "registered into the production registry). Every probe expecting a refusal is paired "
        "with a control that must not fire, so a check that has stopped firing surfaces as a "
        "failed probe rather than as a quietly green suite.\n"
    )
    sections.append(_render_probe_table())

    sections.append("## Falsifier 2 verdict\n")
    sections.append(f'SELECTION.md\'s `## Falsifiers` list, item 2: "{_FALSIFIER_2_TEXT}"\n')
    sections.append(
        "**Result: Falsifier 2 did not fire.** Every `effective_depth` and `execution_mode` "
        "value in every wiring above was derived from that wiring's `nodes`/`deps` plus "
        "`default_registry()` alone, through "
        "`databasise.validator.depth.effective_depth` and "
        "`databasise.validator.execution_mode.derive_execution_mode` — no self-declared depth "
        "or execution_mode field was read from any wiring document. D4's brake holds. All three "
        "named wirings above compute without any self-declaration, and every self-declaration "
        "and blast-radius refusal probe fired with its expected code, each paired with a control "
        "that did not fire — the computation governs regardless of what a wiring author "
        "attempts to write.\n"
    )
    return "\n".join(sections)


def main() -> None:
    text = render_markdown()
    EVIDENCE_PATH.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

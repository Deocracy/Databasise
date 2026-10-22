"""Falsifier 2 evidence run — CONTRACT §19.10 and SELECTION.md's ``## Falsifiers`` list item 2.

Falsifier 2, quoted verbatim: "Depth cannot be computed statically. Over three real parts
(decomposed `lightrag-local`, opaque `codebase-memory-mcp`, half-decomposed LightRAG), the
validator cannot derive `depth` from wiring + registry without a self-declaration. Then D4 has no
brake and D's regime was doing structural work."

This module re-runs that falsifier as a committed, ``python -m``-runnable artifact: it loads the
named wirings under ``evidence/wirings/*.json``, resolves them against ``probe_registry()`` (the
real ``default_registry()`` plus the catalogued ``codebase-memory-mcp@0.1.0`` and two probe-only
parts, admitted only there, since 14-07 D-13), computes ``effective_depth``/``execution_mode``/blast-radius per node
through the same functions the runner calls — never a reimplementation, never the superseded
tracer-era ``derive_execution_mode`` in ``databasise/validator/depth.py`` — and renders a Markdown
document a second author can read without opening a test file (02-CONTEXT.md D-03).

It also re-runs MACH-01's no-self-declaration clause and SELECTION.md Falsifier 1 limb (b) as a
committed probe suite (``PROBES``): each probe expecting a refusal is paired with a control that
must not fire, resolved against the same ``probe_registry()``. None of its three additions is
registered into the production registry (02-CONTEXT.md D-03).
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from databasise.cli import InstalledPackageWriteError, refuse, write_committed_documents
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

# The registry every rendered result is computed against (B-WR-01), named once for the render.
_REGISTRY_TEXT = (
    "Every result in this document (the named wirings, the probes and the verdict) is computed "
    "against `probe_registry()`: `default_registry()` plus the catalogued "
    "`codebase-memory-mcp@0.1.0` and the two probe-only parts "
    "`probe/shared-artifact-writer@0.1.0` and `probe/evidence-writer@0.1.0`. These three parts "
    "are admitted only in `probe_registry()`; none is registered in the production "
    "`default_registry()`.\n"
)

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


class MalformedBoundaryKnobError(ValueError):
    """A named wiring's ``boundary_knobs`` entry is not an object carrying both ``between`` and
    ``rationale`` (C-WR-04)."""


def load_wiring(stem: str) -> dict[str, Any]:
    """Load one committed wiring document by its file stem (no ``.json`` suffix)."""
    return json.loads((WIRINGS_DIR / f"{stem}.json").read_text(encoding="utf-8"))


# Two probe-only parts backing the b-family blast-radius probes below. Neither is registered into
# default_registry() — see probe_registry(). artifact_scope is left unset so CONTRACT §3's stated
# default of `shared` applies via blast_radius.py's own `part.artifact_scope or "shared"` rule
# (validator/blast_radius.py:50).
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
    """``default_registry()`` plus the two probe-only parts above and the catalogued
    ``codebase-memory-mcp@0.1.0`` (admitted, not registered in production since 14-07, D-13),
    assembled fresh on every call. Never registers them into a shared or module-level registry: the
    production ``default_registry()`` never carries any of the three, however many times a probe
    runs.
    """
    registry = default_registry()
    registry.register(SHARED_ARTIFACT_WRITER_PROBE_PART)
    registry.register(EVIDENCE_WRITER_PROBE_PART)
    # Lazy: the declaration-only module loads only when a probe registry is built (15-RESEARCH 19).
    from databasise.parts_core.declared_only import CODEBASE_MEMORY_MCP_PART

    registry.register(CODEBASE_MEMORY_MCP_PART)
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
    """A deep copy of W3 with one extra key added to its ``keywords`` node (the real decomposed
    query side's own root node, immediately downstream of the opaque ``ingest`` node — the node
    the old, now-retired single-node ``query-side`` stand-in occupied before 03-08-PLAN.md Task 3
    replaced it with the real decomposed node set) — the shape the ``c1``/``c2`` probes need to
    distinguish a self-declared derived field from an ordinary typo.
    """
    doc = copy.deepcopy(load_wiring("w3-lightrag-half-decomposed"))
    doc["nodes"]["keywords"][key] = value
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
    parsed = parse_wiring(doc, probe_registry())
    return doc, parsed


def evaluate_wiring(stem: str) -> WiringEvidence:
    """Resolve one named wiring against ``probe_registry()`` and compute one ``NodeRow`` per
    node, iterating in ``parsed.node_order`` (sorted node id) order for a deterministic render.
    """
    doc, parsed = _parse(stem)
    rows = []
    raw_nodes = doc.get("nodes") if isinstance(doc, dict) else None
    resolved = set(parsed.parts)
    # A node dropped by parse_wiring (a self-declared field, an unknown component) or a dep on one
    # leaves the graph uncomputable: report the wiring's violations and compute no rows (C-CR-01).
    computable = (
        isinstance(raw_nodes, dict)
        and resolved == set(raw_nodes)
        and all(set(deps) <= resolved for deps in parsed.deps.values())
    )
    if computable:
        depth_map = effective_depth(parsed)
        blast_violations = blast_radius_violations(parsed, depth_map)
    else:
        depth_map, blast_violations = {}, []
    refused_node_ids = {
        v.pointer.split("/")[2] for v in blast_violations if v.code == CODE_BLAST_RADIUS_REFUSAL
    }

    for node_id in parsed.node_order if computable else ():
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
        consumer_part = parsed.parts.get(node_id)
        if consumer_part is None:
            continue  # unresolved node: reported as a violation, no edge to enumerate (C-CR-01)
        for dep in parsed.deps[node_id]:
            producer_part = parsed.parts.get(dep)
            if producer_part is None:
                continue
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
        if not isinstance(knob, dict):
            raise MalformedBoundaryKnobError(
                f"{evidence.stem}'s boundary_knobs[{i}] must be an object with 'between' and "
                "'rationale'"
            )
        between = knob.get("between")
        rationale = knob.get("rationale")
        if between is None or rationale is None:
            missing = [key for key in ("between", "rationale") if knob.get(key) is None]
            raise MalformedBoundaryKnobError(
                f"{evidence.stem}'s boundary_knobs[{i}] is missing required key(s) "
                f"{missing}: every boundary_knobs entry must declare both 'between' and "
                "'rationale'"
            )
        rows.append(
            BoundaryRow(
                boundary_id=knob.get("boundary_id", f"{evidence.stem}-knob-{i}"),
                boundary_class="knob",
                between=between,
                rationale=rationale,
            )
        )

    return tuple(rows)


def _escape_cell(value: str) -> str:
    """Escape a markdown table cell so an author-supplied `|` or newline can't silently
    split a rendered row into extra columns (WR-01)."""
    return value.replace("|", "\\|").replace("\n", " ")


def _render_node_table(rows: tuple[NodeRow, ...]) -> str:
    header = (
        "| node id | component | wiring kind | structural_depth | effective_depth | "
        "execution_mode | part effects | artifact_scope | blast-radius |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for row in rows:
        component_cell = _escape_cell(row.component)
        effects_cell = _escape_cell(", ".join(row.part_effects)) if row.part_effects else "—"
        scope_cell = _escape_cell(row.artifact_scope) if row.artifact_scope else "—"
        lines.append(
            f"| {row.node_id} | {component_cell} | {row.wiring_kind} | {row.structural_depth} | "
            f"{row.effective_depth} | {row.execution_mode} | {effects_cell} | {scope_cell} | "
            f"{row.blast_radius} |"
        )
    return header + "\n".join(lines) + "\n"


def _render_violations(evidence: WiringEvidence) -> str:
    """The validator's own violation and cycle report for one wiring, as read (C-CR-01)."""
    if evidence.violations:
        listed = "\n".join(
            f"- `{v.code}` at `{v.pointer}`: {_escape_cell(v.message)}" for v in evidence.violations
        )
        text = f"**Validator violations:** {len(evidence.violations)}.\n\n{listed}\n"
    else:
        text = "**Validator violations:** none.\n"
    cycles = "; ".join(" -> ".join(cycle) for cycle in evidence.cycles) or "none"
    return f"{text}\n**Cycles:** {cycles}.\n"


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
        f"| {row.boundary_id} | {row.boundary_class} | {_escape_cell(row.between)} | "
        f"{_escape_cell(row.rationale)} |"
        for row in boundaries
    ]
    return header + "\n".join(lines) + "\n"


def _wiring_shape_summary(probe: Probe) -> str:
    return _escape_cell(
        ", ".join(f"{node_id}:{node['component']}" for node_id, node in probe.doc["nodes"].items())
    )


def _probe_verdict(probe: Probe, observed: frozenset[str]) -> str:
    if probe.expected_code is None:
        return "OK (no violation)" if not observed else "UNEXPECTED VIOLATION"
    return "fired as expected" if probe.expected_code in observed else "DID NOT FIRE"


def failing_probes() -> tuple[str, ...]:
    """Ids of the probes whose verdict cell is ``DID NOT FIRE`` or ``UNEXPECTED VIOLATION``."""
    return tuple(
        probe.probe_id
        for probe in PROBES
        if _probe_verdict(probe, evaluate_probe(probe))
        in ("DID NOT FIRE", "UNEXPECTED VIOLATION")
    )


def failing_wirings() -> tuple[str, ...]:
    """Stems of the named wirings the validator reports any violation on (C-CR-01)."""
    return tuple(stem for stem in NAMED_WIRINGS if evaluate_wiring(stem).violations)


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
        verdict = _probe_verdict(probe, observed)
        lines.append(
            f"| {probe.probe_id} | {_wiring_shape_summary(probe)} | {expected_cell} | "
            f"{observed_cell} | {verdict} |"
        )
        meanings.append(f"- **{probe.probe_id}**: {probe.title}")
    return header + "\n".join(lines) + "\n\n" + "\n".join(meanings) + "\n"


def render_markdown() -> str:
    """Render every named wiring's computed-vs-declared table, its CONTRACT §19.10 candidate
    boundary set, and a closing Falsifier 2 verdict. A pure function of the committed wiring
    documents plus ``probe_registry()`` — no timestamp, no host path, no run-varying value of
    any kind — so two calls in one process return byte-identical text.
    """
    sections = [
        "# Falsifier 2 Evidence\n",
        (
            "Computed-vs-declared depth and execution_mode for each of MACH-01's named wirings, "
            "resolved against `probe_registry()` and computed by "
            "`databasise.validator.depth.effective_depth` and "
            "`databasise.validator.execution_mode.derive_execution_mode` — the same functions "
            "the runner calls, never a reimplementation.\n"
        ),
        _REGISTRY_TEXT,
    ]
    for stem in NAMED_WIRINGS:
        doc, parsed = _parse(stem)
        evidence = evaluate_wiring(stem)
        sections.append(f"## {evidence.wiring_id} — {evidence.title}\n")
        sections.append(
            f"Resolved against `probe_registry()` ({len(evidence.rows)} node(s)).\n"
        )
        sections.append(_render_node_table(evidence.rows))
        sections.append(_render_violations(evidence))
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
        "against the same `probe_registry()`. Every probe expecting a refusal is paired "
        "with a control that must not fire, so a check that has stopped firing surfaces as a "
        "failed probe rather than as a quietly green suite.\n"
    )
    sections.append(_render_probe_table())

    sections.append("## Falsifier 2 verdict\n")
    sections.append(f'SELECTION.md\'s `## Falsifiers` list, item 2: "{_FALSIFIER_2_TEXT}"\n')
    failing = failing_probes()
    failing_named = failing_wirings()
    if failing or failing_named:
        reasons = []
        if failing_named:
            reasons.append(
                "A named wiring carries validator violations "
                f"({', '.join(f'`{stem}`' for stem in failing_named)}; listed in its section "
                "above), so its depth is not shown to compute from wiring and registry alone."
            )
        if failing:
            reasons.append(
                "A probe did not behave as expected "
                f"({', '.join(f'`{probe_id}`' for probe_id in failing)}): a refusal that stopped "
                "firing, or a control that fired."
            )
        sections.append(
            f"**Result: Falsifier 2 fired.** {' '.join(reasons)} The no-self-declaration "
            "computation is not demonstrated by this run, and D4's brake is not shown to hold.\n"
        )
    else:
        sections.append(
            "**Result: Falsifier 2 did not fire.** Every `effective_depth` and `execution_mode` "
            "value in every wiring above was derived from that wiring's `nodes`/`deps` plus "
            "`probe_registry()` alone, through "
            "`databasise.validator.depth.effective_depth` and "
            "`databasise.validator.execution_mode.derive_execution_mode` — no self-declared "
            "depth or execution_mode field was read from any wiring document. D4's brake holds. "
            "All three named wirings above compute without any self-declaration, and every "
            "self-declaration and blast-radius refusal probe fired with its expected code, each "
            "paired with a control that did not fire — the computation governs regardless of "
            "what a wiring author attempts to write.\n"
        )
    return "\n".join(sections)


def main(argv: list[str] | None = None) -> int:
    """Write the rendered document; exit 1 when Falsifier 2 fired (a probe did not behave as
    expected, or a named wiring carries a validator violation). A named refusal (a malformed
    ``boundary_knobs`` entry, an installed-package target, an OS read or write error) prints one
    stderr line and returns 1, writing nothing (D-03)."""
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    try:
        text = render_markdown()
        write_committed_documents((EVIDENCE_PATH, text))
    except (MalformedBoundaryKnobError, InstalledPackageWriteError, OSError) as exc:
        return refuse(exc)
    print(text)
    return 1 if failing_probes() or failing_wirings() else 0


if __name__ == "__main__":
    sys.exit(main())

"""Prompt designs D0..D7 for spike 008 (stdlib only, no GPU, no network).

Read-only reuse of spike 003 artefacts: INSTRUCTION (byte-identical for D0),
teacher.json labels (few-shot examples), v0.2 grammar. Nothing here edits 003.

Held-out rule (fixed, deterministic): sort the 20 teacher-labelled documents
by (op_count, doc_id); EXAMPLE_DOCS are the 4 middle entries (indices 8..11);
SCORED_DOCS are the other 16. Every design, including the D0 baseline, is
scored on exactly the SCORED set, so few-shot examples never leak into scores.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPIKE003 = HERE.parent / "003-op-emission-size-sweep"
sys.path.insert(0, str(SPIKE003))
from common import INSTRUCTION, load_units  # noqa: E402 (spike 003, read-only)

DESIGNS = ["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7"]

ENTITY_GBNF_VERSION = "spike008-entities-v1"


def entity_grammar() -> str:
    """GBNF for D3 step 1: {"entities": ["name", ...]} (format only)."""
    return "\n".join([
        f"# MelodyScribe entity list {ENTITY_GBNF_VERSION}",
        'root ::= "{" space "\\"entities\\"" space ":" space "[" '
        'space (string (space "," space string)*)? space "]" space "}"',
        'space ::= " "?',
        'string ::= "\\"" char* "\\""',
        'char ::= [^"\\\\\\x00-\\x1F] | "\\\\" (["\\\\/bfnrt] | "u" '
        "[0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])",
    ]) + "\n"


def _teacher_ops(doc_id: str) -> list[dict]:
    lab = json.loads((SPIKE003 / "teacher.json").read_text())["labels"][doc_id]
    return lab["ops"]


def split_docs() -> tuple[list[str], list[str]]:
    """(EXAMPLE_DOCS, SCORED_DOCS) by the fixed median rule."""
    teacher = json.loads((SPIKE003 / "teacher.json").read_text())
    ranked = sorted(teacher["labels"], key=lambda d: (len(teacher["labels"][d]["ops"]), d))
    assert len(ranked) == 20
    examples = ranked[8:12]
    scored = [d for d in ranked if d not in examples]
    return examples, scored


def example_block(doc_id: str, contents: dict[str, str]) -> str:
    ops_json = json.dumps({"ops": _teacher_ops(doc_id)})
    return f"Section:\n{contents[doc_id]}\n\nJSON:\n{ops_json}"


def vocab_hint(examples: list[str]) -> str:
    """Frequency-ordered 'predicate (n)' list over the example docs' labels."""
    from collections import Counter
    teacher = json.loads((SPIKE003 / "teacher.json").read_text())
    c: Counter[str] = Counter()
    for d in examples:
        for op in teacher["labels"][d]["ops"]:
            c[op.get("p", op.get("attribute"))] += 1
    items = ", ".join(f"{k} ({v})" for k, v in c.most_common(30))
    return (
        "The most common predicates and attributes in labelled sections like "
        f"this one are: {items}. Prefer these spellings when they fit the "
        "section; use a new spelling only when none fits."
    )


D4_INSTRUCTION = (
    "You are a Knowledge Graph Specialist extracting entities and relations "
    "from a text section into stores. "
    "Classify each entity with one of these types: Person (human individuals, "
    "real or fictional), Organization (companies, institutions, groups), "
    "Location (cities, countries, buildings), Event (occurrences, meetings), "
    "Content (films, books, articles, works), Concept (abstract ideas), "
    "Artifact (tools, devices, software), Other (nothing else fits). "
    "Extract ALL clearly stated entities first, then ALL direct binary "
    "relations between them (decompose multi-entity statements into binary "
    "pairs); name subjects and objects explicitly, never with pronouns; keep "
    "names in consistent title case across ops. "
    'Emit one JSON object {"ops":[...]} with at most 32 ops, '
    "targets restricted to [graph,sql]. "
    "Graph op: {\"target\":\"graph\",\"s\":subject,\"p\":relation keywords,"
    "\"o\":object,\"quote\":evidence}. "
    "Sql op: {\"target\":\"sql\",\"subject\":subject,\"attribute\":attribute,"
    "\"value\":value,\"value_type\":\"text\"|\"number\"|\"date\","
    "\"quote\":evidence}; dates as ISO 8601 or a year, numbers as decimals. "
    "Evidence (quote) is a 3-to-256-character VERBATIM substring copied "
    "character-for-character from the section text below; the quoted span "
    "must contain the subject or the value verbatim -- if the value is "
    "normalised (an ISO date, a decimal), quote a span containing the "
    "subject instead. Never invent offsets, never paraphrase the quote. "
    "Emit one graph op and one sql op per distinct checkable fact. "
    'If the section states no checkable fact, emit {"ops":[]}. '
    "Output JSON only, no prose."
)

D3_STEP1_INSTRUCTION = (
    "List every distinct entity named in the text section below: people, "
    "works, places, organizations, events, and dates. "
    'Emit one JSON object {"entities":[...]} with each name spelled exactly '
    "as in the section. Output JSON only, no prose."
)

D7_PLAN_LINE = "Plan: list the entities, then the facts with dates, then the relations."


def build_prompt(design: str, content: str, contents: dict[str, str],
                 examples: list[str]) -> str:
    """Single-decode prompt for every design except D3 (two-step)."""
    assert design in DESIGNS, design
    if design == "D0":
        return INSTRUCTION + "\n\nSection:\n" + content + "\n\nJSON:\n"
    if design == "D1":
        ex = example_block(examples[0], contents)
        return (INSTRUCTION + "\n\nExample:\n" + ex +
                "\n\nSection:\n" + content + "\n\nJSON:\n")
    if design == "D2":
        exs = "\n\n".join(example_block(d, contents) for d in examples[:3])
        return (INSTRUCTION + "\n\nExamples:\n" + exs +
                "\n\nSection:\n" + content + "\n\nJSON:\n")
    if design == "D4":
        return D4_INSTRUCTION + "\n\nSection:\n" + content + "\n\nJSON:\n"
    if design == "D5":
        return (INSTRUCTION + " " + vocab_hint(examples) +
                "\n\nSection:\n" + content + "\n\nJSON:\n")
    if design == "D6":
        return ("Section:\n" + content + "\n\n" + INSTRUCTION + "\n\nJSON:\n")
    if design == "D7":
        return (INSTRUCTION + " " + D7_PLAN_LINE +
                "\n\nSection:\n" + content + "\n\nJSON:\n")
    raise AssertionError(f"D3 has no single prompt (two-step); got {design}")


def d3_step1_prompt(content: str) -> str:
    return D3_STEP1_INSTRUCTION + "\n\nSection:\n" + content + "\n\nJSON:\n"


def d3_step2_prompt(content: str, entities: list[str] | None) -> str:
    ent_line = ("Entities in this section: " + json.dumps(entities)
                if entities else
                "Entities in this section: (entity list unavailable)")
    return (INSTRUCTION + "\n\n" + ent_line +
            "\n\nSection:\n" + content + "\n\nJSON:\n")

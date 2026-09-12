"""MelodyScribe Score compiler (spike 001).

Score XML -> deterministic token plan. Standard library only.

Implements SCORE-IO-SPEC.md sections 2-4: the Score document, the token
policy (token-string level; real token ids are bound per model in spike 002),
and compilation Score -> token plan with invariants I1-I5.

What "deterministic" means here: the plan structure (ordered steps, named
sequences, token strings appended, read positions, grammars, caps) is a pure
function of (Score bytes, DOC_PREFIX_V, INSTRUCTIONS_V, TOKENIZER_VERSION).
The bundled tokenizer is a word-level stand-in; spike 002 replaces encode()
with the model's tokenizer and records real [EMB]/[RQ] ids. The isolation,
order, no-leakage, bounded-decode and one-read claims are tokenizer
independent and are tested in test_spike.py.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------- versions

DOC_PREFIX_V = "score-io-v0.1"
INSTRUCTIONS_V = "score-io-v0.1"
TOKENIZER_VERSION = "toy-word-v1"  # stand-in; spike 002 binds real ids

# v0.1 open decision D4: doc_prefix includes the chat-template system turn.
# Placeholder text owned with the model revision; spike 002 records per model.
DOC_PREFIX = (
    "<|system|>You file Score sections into typed ops. "
    "Emit only what the section directives request.</|system|>"
)

EMB_TOKEN = "[EMB]"
RQ_TOKEN = "[RQ]"

REWRITE_STYLES = ("propositions", "canonical", "summary")
FILE_TARGETS = ("graph", "sql", "folio", "agent")
LINK_SOURCES = ("raw", "graph", "sql", "folio")

REWRITE_MAX_TOKENS = 256
OPS_MAX_TOKENS = 256
TEXT_MAX_TOKENS = 512
TEXT_STOP_SET = ["</score>", "\n\n\n"]

REWRITE_INSTRUCTIONS = {
    "propositions": (
        "Rewrite the section above as one atomic proposition per line. "
        "Add no facts."
    ),
    "canonical": (
        "Rewrite the section above in canonical entity-attribute-value "
        "sentences. Add no facts."
    ),
    "summary": (
        "Summarise the section above in at most three sentences. Add no facts."
    ),
}

ANSWER_INSTRUCTION = (
    "Follow the command in the section above. Answer in plain text."
)


def ops_instruction(file_set: tuple[str, ...]) -> str:
    targets = ",".join(file_set)
    return (
        'Emit one JSON object {"ops":[...]} with at most 32 ops, '
        f"targets restricted to [{targets}]. "
        "Graph and sql ops need a [start,end] evidence span into the section. "
        'Empty list {"ops":[]} means nothing to file.'
    )


# ---------------------------------------------------------------- tokenizer

_TOKEN_RE = re.compile(r"\S+|\s+")


def encode(text: str) -> list[str]:
    """Toy word-level tokenizer. Deterministic; replaced per model in 002."""
    return _TOKEN_RE.findall(text)


# ---------------------------------------------------------------- parsing

ID_RE = re.compile(r"[a-z0-9_-]+\Z")
SECTION_ATTRS = {"id", "embed", "respond", "file", "link"}
SCORE_ATTRS = {"v", "corpus", "doc", "provenance"}


class CompileError(Exception):
    pass


def _parse_list(value: str, allowed: tuple[str, ...], name: str) -> tuple[str, ...]:
    parts = [p.strip() for p in value.split(",")]
    if any(p == "" for p in parts):
        raise CompileError(f"empty entry in {name}={value!r}")
    if len(set(parts)) != len(parts):
        raise CompileError(f"duplicate entry in {name}={value!r}")
    for p in parts:
        if p not in allowed:
            raise CompileError(f"unknown {name} value {p!r} (allowed: {allowed})")
    return tuple(parts)


def parse_score(xml_text: str) -> dict:
    """Parse and validate a Score document. Returns a plain dict spec.

    Raises CompileError on anything the spec refuses: unknown attribute or
    value, duplicate or bad id, file without respond=ops, rewrite without a
    registered style, zero sections, model provenance, nested markup.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise CompileError(f"not well-formed XML: {e}")
    if root.tag != "score":
        raise CompileError(f"root must be <score>, got <{root.tag}>")
    for attr in root.attrib:
        if attr not in SCORE_ATTRS:
            raise CompileError(f"unknown <score> attribute {attr!r}")
    if root.attrib.get("v", "1") != "1":
        raise CompileError(f"unsupported score v={root.attrib.get('v')!r}")
    provenance = root.attrib.get("provenance", "chunker")
    if provenance not in ("chunker", "frontier"):
        # The model never authors directives (MANIFEST D-MS-01/02): a Score
        # claiming model provenance, or any provenance outside the closed
        # set, is refused, never ignored.
        raise CompileError(f"refused provenance {provenance!r}")

    sections = []
    seen_ids = set()
    for el in list(root):
        if el.tag != "section":
            raise CompileError(f"unexpected <{el.tag}> inside <score>")
        for attr in el.attrib:
            if attr not in SECTION_ATTRS:
                raise CompileError(f"unknown <section> attribute {attr!r}")
        sid = el.attrib.get("id")
        if sid is None:
            raise CompileError("section without id")
        if not ID_RE.match(sid):
            raise CompileError(f"bad section id {sid!r}")
        if sid in seen_ids:
            raise CompileError(f"duplicate section id {sid!r}")
        seen_ids.add(sid)

        embed = el.attrib.get("embed", "isolated")
        if embed.startswith("rewrite:"):
            style = embed[len("rewrite:"):]
            if style not in REWRITE_STYLES:
                raise CompileError(f"unregistered rewrite style {style!r}")
        elif embed not in ("isolated", "context", "off"):
            raise CompileError(f"unknown embed value {embed!r}")

        respond = el.attrib.get("respond", "none")
        if respond not in ("none", "ops", "text"):
            raise CompileError(f"unknown respond value {respond!r}")

        file_raw = el.attrib.get("file")
        if file_raw is None:
            file_set = (
                tuple(FILE_TARGETS) if respond == "ops" else ()
            )
        else:
            file_set = _parse_list(file_raw, FILE_TARGETS + ("any",), "file")
            if "any" in file_set:
                if len(file_set) != 1:
                    raise CompileError(
                        f"'any' must stand alone in file={file_raw!r}"
                    )
                file_set = tuple(FILE_TARGETS)
            if respond != "ops":
                raise CompileError(
                    f"section {sid!r}: file= without respond=ops"
                )
        if respond == "ops" and not file_set:
            raise CompileError(f"section {sid!r}: respond=ops with empty file set")

        link = tuple(
            _parse_list(el.attrib.get("link", "raw"), LINK_SOURCES, "link")
        )

        if len(el) != 0:
            raise CompileError(
                f"section {sid!r}: nested markup refused, plain text only"
            )
        content = (el.text or "") + "".join(
            (child.tail or "") for child in el
        )
        # ET already unescaped entities; a literal tag inside content would
        # have parsed as markup, so reaching here means content is pure text.
        sections.append(
            {
                "id": sid,
                "embed": embed,
                "respond": respond,
                "file": file_set,
                "link": link,
                "content": content,
            }
        )
    if not sections:
        raise CompileError("Score with zero sections")
    return {
        "corpus": root.attrib.get("corpus", ""),
        "doc": root.attrib.get("doc", ""),
        "provenance": provenance,
        "sections": sections,
    }


# ---------------------------------------------------------------- compilation

def compile_plan(spec: dict) -> dict:
    """Compile a parsed Score into a token plan (SCORE-IO-SPEC.md section 4).

    Returns {"prefix": {...}, "steps": [...], "versions": {...}}.
    Step kinds: append, copy_prefix, read_vector, free, decode.
    """
    prefix_tokens = encode(DOC_PREFIX)
    steps: list[dict] = []
    s0_len = 0
    # Positions after a decode step are cap-relative: the generated token
    # count is known only at runtime (bounded by cap). Reads and appends
    # record pos_kind so the runtime, not the plan, resolves them.
    s0_exact = True
    reads: list[tuple[str, int]] = []  # (sequence, position) of vector reads

    def s0_append(tokens: list[str]) -> None:
        nonlocal s0_len
        steps.append({"kind": "append", "seq": "S0", "tokens": tokens,
                      "pos_kind": "exact" if s0_exact else "cap_relative"})
        s0_len += len(tokens)

    for index, sec in enumerate(spec["sections"]):
        content_tokens = encode(sec["content"])
        # Every section's content enters S0 in document order (I2).
        s0_append(content_tokens)
        seq = f"E_{index}"

        embed = sec["embed"]
        if embed == "isolated":
            steps.append(
                {"kind": "copy_prefix", "seq": seq, "from": "P",
                 "tokens": list(prefix_tokens)}
            )
            steps.append(
                {"kind": "append", "seq": seq,
                 "tokens": content_tokens + [EMB_TOKEN]}
            )
            pos = len(prefix_tokens) + len(content_tokens) + 1 - 1
            steps.append(
                {"kind": "read_vector", "seq": seq, "at": pos,
                 "token": EMB_TOKEN, "form": "isolated",
                 "pos_kind": "exact", "section": sec["id"]}
            )
            reads.append((seq, pos))
            steps.append({"kind": "free", "seq": seq})
        elif embed == "context":
            pos = s0_len  # position the [EMB] token will occupy
            s0_append([EMB_TOKEN])
            steps.append(
                {"kind": "read_vector", "seq": "S0", "at": pos,
                 "token": EMB_TOKEN, "form": "context",
                 "pos_kind": "exact" if s0_exact else "cap_relative",
                 "section": sec["id"]}
            )
            reads.append(("S0", pos))
        elif embed == "off":
            pass
        elif embed.startswith("rewrite:"):
            style = embed[len("rewrite:"):]
            instr = encode(REWRITE_INSTRUCTIONS[style])
            s0_append(instr)
            cap = REWRITE_MAX_TOKENS
            steps.append(
                {"kind": "decode", "seq": "S0", "what": f"rewrite:{style}",
                 "grammar": None, "stop": list(TEXT_STOP_SET),
                 "cap": cap, "section": sec["id"], "s0_base": s0_len}
            )
            s0_len += cap  # generated tokens stay in S0; cap bounds them
            s0_exact = False
            pos = s0_len
            s0_append([EMB_TOKEN])
            steps.append(
                {"kind": "read_vector", "seq": "S0", "at": pos,
                 "token": EMB_TOKEN, "form": f"rewrite:{style}",
                 "pos_kind": "cap_relative", "section": sec["id"]}
            )
            reads.append(("S0", pos))
        else:  # unreachable: parse_score closed the set
            raise CompileError(f"unknown embed value {embed!r}")

        if sec["respond"] == "ops":
            instr = encode(ops_instruction(sec["file"]))
            s0_append(instr)
            cap = OPS_MAX_TOKENS
            steps.append(
                {"kind": "decode", "seq": "S0", "what": "ops",
                 "grammar": f"G({','.join(sec['file'])})",
                 "stop": None, "cap": cap, "section": sec["id"],
                 "s0_base": s0_len}
            )
            s0_len += cap
            s0_exact = False
        elif sec["respond"] == "text":
            instr = encode(ANSWER_INSTRUCTION)
            s0_append(instr)
            cap = TEXT_MAX_TOKENS
            steps.append(
                {"kind": "decode", "seq": "S0", "what": "text",
                 "grammar": None, "stop": list(TEXT_STOP_SET),
                 "cap": cap, "section": sec["id"], "s0_base": s0_len}
            )
            s0_len += cap
            s0_exact = False

    # I5: each [EMB] position read exactly once.
    if len(reads) != len(set(reads)):
        raise CompileError("duplicate vector read position")
    # I4: every decode step bounded, with grammar or stop set.
    for st in steps:
        if st["kind"] == "decode":
            if not st["cap"] or st["cap"] <= 0:
                raise CompileError("unbounded decode step")
            if st["grammar"] is None and not st["stop"]:
                raise CompileError("decode with neither grammar nor stop set")

    return {
        "prefix": {"name": "P", "version": DOC_PREFIX_V,
                   "tokens": prefix_tokens},
        "steps": steps,
        "versions": {
            "doc_prefix": DOC_PREFIX_V,
            "instructions": INSTRUCTIONS_V,
            "tokenizer": TOKENIZER_VERSION,
            "token_policy": "emb=toy-word-v1:[EMB];rq=toy-word-v1:[RQ];pooling=last",
        },
    }


def compile_score(xml_text: str) -> dict:
    return compile_plan(parse_score(xml_text))


# ---------------------------------------------------------------- projections

def s0_token_stream(plan: dict, generated: dict[str, list[str]] | None = None) -> list[str]:
    """Reconstruct the S0 stream (I2). `generated` maps step index -> tokens
    for decode steps; unfilled decodes contribute their cap as <gen:N> marks
    so positions still account."""
    out: list[str] = []
    generated = generated or {}
    for i, st in enumerate(plan["steps"]):
        if st["kind"] == "append" and st["seq"] == "S0":
            out.extend(st["tokens"])
        elif st["kind"] == "decode":
            out.extend(generated.get(str(i), [f"<gen:{i}>"]))
    return out


def ei_tokens(plan: dict, spec: dict, section_id: str) -> list[str] | None:
    """Token list of the isolated embedding sequence for a section (I1/I3).
    Returns None for non-isolated sections."""
    sec = next(s for s in spec["sections"] if s["id"] == section_id)
    if sec["embed"] != "isolated":
        return None
    return plan["prefix"]["tokens"] + encode(sec["content"]) + [EMB_TOKEN]

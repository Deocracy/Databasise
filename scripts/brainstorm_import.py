#!/usr/bin/env python3
"""Deterministic markdown -> ledger-row planner for import-brainstorm.

No I/O and no model call. The caller reads the file, calls plan_import(),
and only writes when it returns rows. A requirement is a list item (`- `,
`* `, `+ `, `N. ` or `N) `, with an optional `[ ]` / `[x]` checkbox) under a
heading whose text contains "requirement" (any case), up to the next heading
of the same or higher level; headings nested inside keep the section open. A
heading naming out of scope, non-requirements, non-goals, open questions or
traceability never opens a section, and nothing under it imports. Fenced code
blocks and HTML comments are ignored. Nested items (indented past the
section's first item) fold into their parent's text, and a line directly
after an item continues it. No other line in a section is dropped silently:
a table row, a nested item with its own ID, a heading that mixes
requirements with an excluded topic, or an unclosed fence or comment fails
the import, and every other line comes back as skipped.
"""
import re

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
BULLET_RE = re.compile(r"^([ \t]*)(?:[-*+]|[0-9]+[.)])\s+(.*)$")
CHECKBOX_RE = re.compile(r"^\[[ xX]\]\s*")
LEAD_STAR = re.compile(r"^(?:\*\s+)+")
ID_PART = r"([A-Za-z][A-Za-z0-9]*)-([0-9]+)"
BOLD_ID_RE = re.compile(r"^\*\*" + ID_PART + r"\.?\*\*\s*[:\-\u2013\u2014]?\s*")
BARE_ID_RE = re.compile(r"^" + ID_PART + r"\s*[:\-\u2013\u2014]\s*")
ANY_BOLD_ID_RE = re.compile(r"\*\*" + ID_PART + r"\.?\*\*")
REQ_RE = re.compile(r"^REQ-([0-9]+)$")
REQUIRE_WORD = re.compile(r"requirement", re.IGNORECASE)
EXCLUDE_WORD = re.compile(r"\b(?:out[\s-]+of[\s-]+scope|non[\s-]*requirement"
                          r"|non[\s-]*goal|open[\s-]+question|traceability)", re.IGNORECASE)
WS_RE = re.compile(r"\s+")


def _indent_of(leading):
    return len(leading.expandtabs(4))


def _canon(rid):
    """REQ-<n> is REQ-%03d, so REQ-1 and REQ-001 are one ID."""
    m = REQ_RE.match(rid)
    return "REQ-%03d" % int(m.group(1)) if m else rid


def _clean_body(body, known):
    """Split one item body into (id_or_None, text). Bold IDs keep only the
    trailing period: `**AUTH-01**: First.` -> text `First.`, while `- **CART-09.** Fourth`
    (the period inside the bold) drops the ID punctuation -> text `Fourth`.
    A bare ID counts only when its prefix is in `known`, so `UTF-8: ...` stays
    text. IDs match in any case and come back uppercase."""
    body = LEAD_STAR.sub("", body.strip())
    m = BOLD_ID_RE.match(body)
    if not m:
        m = BARE_ID_RE.match(body)
        if m and m.group(1).upper() not in known:
            m = None
    if not m:
        return None, WS_RE.sub(" ", body).strip()
    rid = _canon("%s-%s" % (m.group(1).upper(), m.group(2)))
    return rid, WS_RE.sub(" ", body[m.end():]).strip()


def parse_requirements(text, source, prefixes=()):
    """Parse markdown into (rows, skipped): rows as [{"text", "id" | None,
    "lineno"}], skipped as ["<source>:<line>: <line text>"]. A bare ID counts
    when its prefix is REQ, one of `prefixes` (the ledger's) or a bold ID's
    anywhere in the file. Raises ValueError with the error line on a table
    row, a nested item with its own ID, a heading that mixes requirements
    with an excluded topic, or a code fence or HTML comment that is never
    closed."""
    known = {"REQ", *prefixes}
    known.update(m.group(1).upper() for m in ANY_BOLD_ID_RE.finditer(text))
    out, skipped = [], []
    active_level = None  # level of the open requirements heading
    skip_level = None    # level of an out-of-scope heading: its subsection never imports
    base_indent = None
    fence = fence_line = comment_line = None
    joinable = False     # the previous line was an item or its continuation
    for lineno, raw in enumerate(text.split("\n"), start=1):
        line = raw.rstrip("\r").expandtabs(4).rstrip()
        fm = FENCE_RE.match(line)
        if fence:
            if fm and fm.group(1)[0] == fence[0] and len(fm.group(1)) >= len(fence) \
                    and not fm.group(2).strip():
                fence = None
            continue
        if comment_line:
            if "-->" in line:
                comment_line = None
            continue
        # CommonMark: a backtick fence's info string has no backtick, so
        # ```yaml``` at the start of a line is inline code, not a fence
        if fm and not (fm.group(1)[0] == "`" and "`" in fm.group(2)):
            fence, fence_line, joinable = fm.group(1), lineno, False
            continue
        if line.lstrip().startswith("<!--"):
            if "-->" not in line:
                comment_line = lineno
            joinable = False
            continue
        if not line.strip():
            joinable = False
            continue
        hm = HEADING_RE.match(line)
        if hm:
            level = len(hm.group(1))
            title = hm.group(2)
            joinable = False
            if EXCLUDE_WORD.search(title) \
                    and REQUIRE_WORD.search(EXCLUDE_WORD.sub(" ", title)):
                raise ValueError("%s:%d: heading mixes requirements with an excluded "
                                 "topic; split it into two headings" % (source, lineno))
            if skip_level is not None and level > skip_level:
                continue
            skip_level = None
            base_indent = None  # a heading ends any list above it
            if active_level is not None and level <= active_level:
                active_level = None
            if EXCLUDE_WORD.search(title):
                skip_level = level
            elif active_level is None and REQUIRE_WORD.search(title):
                active_level = level  # a nested heading keeps the open section's level
            continue
        if active_level is None or skip_level is not None:
            continue
        where = "%s:%d" % (source, lineno)
        if line.lstrip().startswith("|"):
            raise ValueError(where + ": table row in a requirements section; "
                             "write requirements as list items")
        bm = BULLET_RE.match(line)
        if not bm:
            if joinable:
                extra = WS_RE.sub(" ", line).strip()
                out[-1]["text"] = " ".join(p for p in (out[-1]["text"], extra) if p)
            else:
                skipped.append("%s: %s" % (where, raw.strip()))
            continue
        joinable = True
        indent = _indent_of(bm.group(1))
        rid, cleaned = _clean_body(CHECKBOX_RE.sub("", bm.group(2)), known)
        if base_indent is None:
            base_indent = indent
        if indent > base_indent:
            if rid:
                raise ValueError("%s: nested item has its own id %s; "
                                 "make it a top-level item" % (where, rid))
            out[-1]["text"] = " / ".join(
                part for part in (out[-1]["text"], cleaned) if part)
            continue
        base_indent = indent
        out.append({"text": cleaned, "id": rid, "lineno": lineno})
    if fence:  # an open fence or comment hides every line after it
        raise ValueError("%s:%d: code fence is never closed" % (source, fence_line))
    if comment_line:
        raise ValueError("%s:%d: HTML comment is never closed" % (source, comment_line))
    return out, skipped


def _norm(text):
    return WS_RE.sub(" ", str(text).strip())


def _ledger_best(ops, items):
    best = 0
    for op in ops or []:
        if isinstance(op, dict) and op.get("op") == "add":
            m = REQ_RE.match(str(op.get("id", "")))
            if m:
                best = max(best, int(m.group(1)))
    for row in items or []:
        if isinstance(row, dict):
            m = REQ_RE.match(str(row.get("id", "")))
            if m:
                best = max(best, int(m.group(1)))
    return best


def plan_import(text, source, ops, items):
    """Validate a document against the ledger. Returns (rows, skipped, None)
    with rows as [(rid, text, spec_ref)] and skipped as ["<source>:<line>:
    <line text>"], or (None, None, error_line) with nothing to write."""
    ledger_rows = [row for row in items or [] if isinstance(row, dict)]
    prefixes = {str(row.get("id", "")).split("-")[0] for row in ledger_rows}
    try:
        parsed, skipped = parse_requirements(text, source, prefixes)
    except ValueError as exc:
        return None, None, str(exc)
    if not parsed:
        return None, None, "%s: no requirement lines found" % source
    for p in parsed:
        if not p.get("text", ""):
            return None, None, "%s:%d: empty requirement text" % (source, p["lineno"])
    seen_ids = {}
    seen_texts = {}
    for p in parsed:
        key = _norm(p["text"])
        if p.get("id"):
            if p["id"] in seen_ids:
                return None, None, "%s:%d: duplicate id %s" % (source, p["lineno"], p["id"])
            seen_ids[p["id"]] = p["lineno"]
        if key in seen_texts:
            return None, None, "%s:%d: duplicate text" % (source, p["lineno"])
        seen_texts[key] = p["lineno"]
    ledger_ids = set()
    ledger_texts = {}
    for row in ledger_rows:
        if isinstance(row.get("id"), str):
            ledger_ids.add(_canon(row["id"]))
        ledger_texts[_norm(row.get("text", ""))] = str(row.get("id", "?"))
    best = _ledger_best(ops, items)
    rows = []
    assigned = set()
    for p in parsed:
        if p.get("id"):
            rid = p["id"]
            if rid in ledger_ids:
                return None, None, "%s:%d: %s: id was already added" % (
                    source, p["lineno"], rid)
            if rid in assigned:
                return None, None, "%s:%d: duplicate id %s" % (source, p["lineno"], rid)
            m = REQ_RE.match(rid)
            if m:
                best = max(best, int(m.group(1)))
        else:
            best += 1
            rid = "REQ-%03d" % best
            while rid in ledger_ids or rid in assigned or rid in seen_ids:
                best += 1
                rid = "REQ-%03d" % best
        assigned.add(rid)
        key = _norm(p["text"])
        if key in ledger_texts:
            return None, None, "%s:%d: text already in ledger (%s)" % (
                source, p["lineno"], ledger_texts[key])
        rows.append((rid, _norm(p["text"]), "%s:%d" % (source, p["lineno"])))
    return rows, skipped, None

#!/usr/bin/env python3
"""Mockup port check: every data-mock-id in the frozen variant must reach the built UI."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

ID_RE = re.compile(
    r"(?<![\[\w-])data-mock-id\s*=\s*\"([^\"]+)\""
    r"|(?<![\[\w-])data-mock-id\s*=\s*'([^']+)'"
    r"|(?<![\[\w-])data-mock-id\s*=\s*\{\s*\"([^\"]+)\"\s*\}"
    r"|(?<![\[\w-])data-mock-id\s*=\s*\{\s*'([^']+)'\s*\}"
)
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv",
             "__pycache__", ".claude", ".planning", "mockups",
             "dist", "build", "out", ".next", ".nuxt", ".svelte-kit",
             "coverage", "storybook-static",
             "tests", "test", "e2e", "__tests__"}
UI_SUFFIXES = {".html", ".htm", ".jsx", ".tsx", ".js", ".ts",
               ".vue", ".svelte", ".astro"}
SKIP_LINE = ("mockup check skipped (no frozen variant; "
             "S8-lean: gates on checkable items only)")
ROW_REF_RE = re.compile(r"\b[A-Z][A-Z0-9]*-[0-9]+\b")
VARIANT_RE = re.compile(
    r"(?<![\[\w-])data-mock-variant\s*=\s*\"([^\"]+)\""
    r"|(?<![\[\w-])data-mock-variant\s*=\s*'([^']+)'"
)
TAG_RE = re.compile(r"<(/?)\s*([A-Za-z][A-Za-z0-9-]*)([^<>]*?)(/?)>")
# Comments and <script>/<style> bodies are opaque to span matching: a tag
# inside them never opens or closes a variant element (as in html.parser).
OPAQUE_RE = re.compile(
    r"<!--.*?-->|<script\b.*?</script\s*>|<style\b.*?</style\s*>",
    re.S | re.I)


def find_ids(text):
    """data-mock-id string literals in text.

    Plain, JSX-brace and Vue-colon forms all count; the Vue form captures
    its inner quotes, so one layer of inner quotes is stripped. Selector
    strings such as [data-mock-id="x"] never count (lookbehind)."""
    ids = set()
    for m in ID_RE.finditer(text):
        val = m.group(1) or m.group(2) or m.group(3) or m.group(4)
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        if val:
            ids.add(val)
    return ids


def _scannable(name):
    low = name.lower()
    return ".spec." not in low and ".test." not in low


def ui_files(root, frozen_rel, bases):
    """UI source files to scan, sorted. Skips version-control, dependency,
    kit-state, mockup, build-output and test directories plus spec/test
    files and the frozen file itself, so the check cannot pass by finding
    the IDs in the mockup it compares, in a test selector, or in stale
    build output."""
    try:
        frozen = str((Path(root) / frozen_rel).resolve())
    except OSError:
        frozen = ""
    out = []
    seen = set()
    for base in bases:
        if base.is_file():
            if base.suffix.lower() in UI_SUFFIXES and _scannable(base.name):
                try:
                    rp = str(base.resolve())
                except OSError:
                    continue
                if rp not in seen and rp != frozen:
                    seen.add(rp)
                    out.append(base)
            continue
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                p = Path(dirpath) / name
                if p.suffix.lower() not in UI_SUFFIXES or not _scannable(name):
                    continue
                try:
                    rp = str(p.resolve())
                except OSError:
                    continue
                if rp in seen or rp == frozen:
                    continue
                seen.add(rp)
                out.append(p)
    return sorted(out)


def _variant_value(attrs):
    m = VARIANT_RE.search(attrs)
    if not m:
        return None
    return m.group(1) or m.group(2)


def _opaque_spans(text):
    return [(m.start(), m.end()) for m in OPAQUE_RE.finditer(text)]


def _in_opaque(pos, opaque):
    return any(s <= pos < e for s, e in opaque)


def variant_spans(text, variant):
    """(start, end) offsets of elements carrying data-mock-variant=variant.

    Each target start tag is matched with the close tag of the same name,
    so nested elements count as inside the variant. Tags in comments and
    script/style bodies are ignored."""
    opaque = _opaque_spans(text)
    spans = []
    for m in TAG_RE.finditer(text):
        if m.group(1) or _in_opaque(m.start(), opaque):
            continue
        if _variant_value(m.group(3) or "") != variant:
            continue
        if m.group(4):
            continue
        tag = m.group(2).lower()
        depth = 1
        end = len(text)
        for n in TAG_RE.finditer(text, m.end()):
            if _in_opaque(n.start(), opaque):
                continue
            if n.group(2).lower() != tag:
                continue
            if n.group(1):
                depth -= 1
                if depth == 0:
                    end = n.end()
                    break
            elif not n.group(4):
                depth += 1
        spans.append((m.start(), end))
    return spans


def frozen_want_ids(text, variant, rel):
    """(want, error): data-mock-id set required by the recorded variant.

    A frozen file with no data-mock-variant attribute counts whole-file;
    otherwise only IDs inside the recorded variant's element count. An empty
    scope in a file that has IDs is an error, never a vacuous pass (a marker
    on a tab button instead of the variant's content)."""
    if not VARIANT_RE.search(text):
        return find_ids(text), None
    spans = variant_spans(text, variant)
    if not spans:
        return set(), f"mockup variant {variant} not found in frozen file {rel}"
    want = find_ids("\n".join(text[s:e] for s, e in spans))
    if not want and find_ids(text):
        return set(), (f"mockup variant {variant} has no data-mock-id "
                       f"elements in frozen file {rel}")
    return want, None


def names_id(row_text, mock_id):
    """True when mock_id is a whole token in row_text: board.cancel does not
    match inside board.cancel-btn or board.cancel.x, while a period that ends
    a sentence is not part of the token."""
    pat = (r"(?<![\w-])(?<![\w-]\.)" + re.escape(mock_id)
           + r"(?![\w-]|\.[\w-])")
    return re.search(pat, row_text) is not None


def port_overrides(path, items):
    """(exempt, mapped, errors) from a MOCKUP-PORT.md table.

    intentionally-dropped cites ledger row IDs in Notes and is exempt only
    when a cited row's status is dropped or deferred-approved (both
    user-only) and its text names the mockup ID as a whole token (ledger
    text is fixed at add, so an agent cannot rename a decided row onto an
    ID); otherwise it is a violation. renamed-with-mapping exempts the old
    ID and requires the mapped one; without a mapped ID it is a violation.
    Any other status word means ported (fail closed)."""
    exempt, mapped, errors = set(), {}, []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return exempt, mapped, [f"mockup port file unreadable: {path}"]
    approved = {}
    if isinstance(items, list):
        for row in items:
            if isinstance(row, dict) \
                    and row.get("status") in ("dropped", "deferred-approved"):
                rid = row.get("id")
                if isinstance(rid, str) and rid:
                    row_text = row.get("text")
                    approved[rid] = row_text if isinstance(row_text, str) else ""
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cols = [c.strip() for c in s.strip("|").split("|")]
        if len(cols) < 7:
            continue
        mock_id, _src, _dst, _props, new_id, status, notes = cols[:7]
        if not mock_id or mock_id == "Mockup ID" \
                or set(mock_id) <= {"-", ":", " "}:
            continue
        st = status.strip().lower()
        if st == "intentionally-dropped":
            cited = [c for c in ROW_REF_RE.findall(notes) if c in approved]
            if not cited:
                errors.append(f"mockup {mock_id}: dropped without user approval "
                              f"(no dropped/deferred-approved ledger row)")
            elif any(names_id(approved[c], mock_id) for c in cited):
                exempt.add(mock_id)
            else:
                errors.append(f"mockup {mock_id}: cited ledger row {cited[0]} "
                              f"does not name this mockup ID")
        elif st == "renamed-with-mapping":
            if new_id.strip():
                mapped[mock_id] = new_id.strip()
            else:
                errors.append(f"mockup {mock_id}: renamed without a mapped ID")
    return exempt, mapped, errors


def main():
    ap = argparse.ArgumentParser(prog="mockup-id-check.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--port", default=None,
                    help="MOCKUP-PORT.md path; defaults to <root>/MOCKUP-PORT.md when present")
    ap.add_argument("--src", action="append", default=[],
                    help="extra project-relative source file or directory to scan")
    args = ap.parse_args()
    root = Path(args.root)
    ledger = root / "ledger" / "REQUIREMENTS.json"
    if not ledger.is_file():
        print("LEDGER: REQUIREMENTS.json missing")
        return 1
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except Exception:
        print("LEDGER: REQUIREMENTS.json unparsable")
        return 1
    freeze = data.get("mockup_freeze")
    if freeze is None:
        print(SKIP_LINE)
        return 0
    if not isinstance(freeze, dict) \
            or not isinstance(freeze.get("variant"), str) \
            or not freeze.get("variant", "").strip() \
            or not isinstance(freeze.get("path"), str) \
            or not freeze.get("path", "").strip() \
            or not isinstance(freeze.get("sha256"), str):
        print("LEDGER: mockup_freeze must be an object or null")
        return 1
    rel = freeze["path"]
    frozen = root / rel
    if not frozen.is_file():
        print(f"mockup frozen file missing: {rel}")
        return 1
    try:
        blob = frozen.read_bytes()
    except OSError:
        print(f"mockup frozen file unreadable: {rel}")
        return 1
    if hashlib.sha256(blob).hexdigest() != freeze["sha256"]:
        print(f"mockup frozen file changed since freeze: {rel}")
        return 1
    want, verr = frozen_want_ids(blob.decode("utf-8", "replace"),
                                 freeze["variant"], rel)
    if verr is not None:
        print(verr)
        return 1
    port = Path(args.port) if args.port else root / "MOCKUP-PORT.md"
    if args.port or port.is_file():
        exempt, mapped, errors = port_overrides(port, data.get("items"))
    else:
        exempt, mapped, errors = set(), {}, []
    out = list(errors)
    bases = [root / s for s in args.src] if args.src else [root]
    have = set()
    for f in ui_files(root, rel, bases):
        try:
            have |= find_ids(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    for mid in sorted(want):
        if mid in exempt or mid in mapped:
            continue
        if mid not in have:
            out.append(f"mockup {mid}: present in frozen mockup {rel} "
                       f"but missing from UI sources")
    for old, new in sorted(mapped.items()):
        if new not in have:
            out.append(f"mockup {old}: mapped ID {new} missing from UI sources")
    for line in out:
        print(line)
    return 1 if out else 0


if __name__ == "__main__":
    raise SystemExit(main())

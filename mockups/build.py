#!/usr/bin/env python3
"""Assemble mockups/operator-console.html from mockups/src/ (stdlib only, deterministic).

Directives, all HTML comments inside src files:
  <!--@include NAME key=value ...-->   src/NAME with each {{key}} replaced
  <!--@repeat VAR N-->BODY<!--@end VAR-->   BODY for VAR = 1..N, {{VAR}} replaced
  <!--@glob PATTERN-->                 every src file matching PATTERN, sorted, concatenated
  <!--@fixtures-->                     one JSON object: src/fixtures/*.json by stem, refusals, resolution

Usage: build.py [--check] [--src DIR] [--out FILE]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "mockups" / "src"
OUT = ROOT / "mockups" / "operator-console.html"
# D-04 and D-06: generated elsewhere, embedded here, never retyped.
SHARED_FIXTURES = {
    "refusals": ROOT / "docs" / "gui" / "refusals.json",
    "resolution": ROOT / "databasise" / "tests" / "fixtures" / "selector-resolution.json",
}

REPEAT = re.compile(r"<!--@repeat\s+(\w+)\s+(\d+)\s*-->(.*?)<!--@end\s+\1\s*-->", re.S)
DIRECTIVE = re.compile(r"<!--@(\w+)(.*?)-->", re.S)
OPAQUE = re.compile(r"<(script|style)\b.*?</\1\s*>", re.S | re.I)


def fail(where: str, message: str):
    raise SystemExit(f"{where}: {message}")


def read(path: Path, where: str) -> str:
    if not path.is_file():
        fail(where, f"missing file {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def fixtures_json(src: Path) -> str:
    data = {}
    for path in sorted((src / "fixtures").glob("*.json")):
        data[path.stem] = json.loads(read(path, path.name))
    for key, path in SHARED_FIXTURES.items():
        data[key] = json.loads(read(path, key))
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return text.replace("</", "<\\/")  # fixture text must not close the script block


def expand(text: str, where: str, src: Path) -> str:
    def repeat(m: re.Match) -> str:
        var, count, body = m.group(1), int(m.group(2)), m.group(3)
        return "".join(
            expand(body.replace("{{%s}}" % var, str(i)), where, src) for i in range(1, count + 1)
        )

    def directive(m: re.Match) -> str:
        name, arg = m.group(1), m.group(2).strip()
        if name == "include":
            target, _, rest = arg.partition(" ")
            if not target:
                fail(where, "include without a file name")
            body = read(src / target, where + ": include " + target)
            for key, value in re.findall(r"(\w+)=(\S+)", rest):
                body = body.replace("{{%s}}" % key, value)
            return expand(body, target, src)
        if name == "glob":
            files = sorted(p for p in src.glob(arg) if p.is_file())
            return "".join(expand(read(p, where), p.relative_to(src).as_posix(), src) for p in files)
        if name == "fixtures":
            return fixtures_json(src)
        return fail(where, f"unknown directive <!--@{name}-->")

    return DIRECTIVE.sub(directive, REPEAT.sub(repeat, text))


def build(src: Path = SRC) -> str:
    html = expand(read(src / "page.html", "page.html"), "page.html", src)
    markup = OPAQUE.sub("", html)
    for token in ("<!--@", "{{"):
        if token in markup:
            line = next(ln for ln in markup.splitlines() if token in ln)
            fail("page.html", f"unresolved {token!r} after expansion: {line.strip()[:80]}")
    return html.rstrip("\n") + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="build.py")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--src", type=Path, default=SRC)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    src, out = args.src.resolve(), args.out.resolve()
    html = build(src)
    if args.check:
        current = out.read_text(encoding="utf-8") if out.is_file() else None
        if current != html:
            print(
                f"{out.relative_to(ROOT)} is stale; run databasise/.venv/bin/python mockups/build.py"
                + ("" if (src, out) == (SRC, OUT) else f" --src {src.relative_to(ROOT)} --out {out.relative_to(ROOT)}"),
                file=sys.stderr,
            )
            return 1
        return 0
    out.write_bytes(html.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

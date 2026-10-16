#!/usr/bin/env python3
"""commit-msg hook: require a conventional subject and a REQ/phase trailer."""
import re
import subprocess
import sys
from pathlib import Path

USAGE = "check-commit-msg: usage: check-commit-msg.py MSG_FILE"
SUBJECT_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(\(.+\))?!?: .{10,}")
TRAILER_RE = re.compile(r"\b(?:REQ-[0-9]+|phase/[0-9]+|Refs #[0-9]+)\b")
BLOCK_SUBJECT = "STOP: use conventional type: <10+ chars>"
BLOCK_TRAILER = ("STOP: commit msg needs REQ-ID or phase/NN trailer "
                 "(REQ-123, phase/07 or Refs #N)")
SCISSORS_BODY = re.compile(r"-{8,}\s*>8\s*-{8,}")
EXEMPT_PREFIXES = ("Merge ", "fixup! ", "squash! ", "amend! ")


def comment_char():
    try:
        proc = subprocess.run(
            ["git", "config", "core.commentChar"],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "#"
    if proc.returncode != 0:
        return "#"
    char = proc.stdout.strip().splitlines()
    if not char or not char[0]:
        return "#"
    return char[0][:1]


def is_scissors(line, comment):
    for prefix in (comment, "#"):
        if prefix and line.startswith(prefix):
            if SCISSORS_BODY.search(line[len(prefix):]):
                return True
    return False


def clean(text, comment):
    lines = text.split("\n")
    kept = []
    for line in lines:
        if is_scissors(line, comment):
            break
        if comment and line.startswith(comment):
            continue
        if line.startswith("#"):
            continue
        kept.append(line)
    while kept and not kept[0].strip():
        kept.pop(0)
    return "\n".join(kept)


def main(argv):
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        text = Path(argv[1]).read_text(encoding="utf-8-sig",
                                       errors="replace")
    except OSError:
        print(f"check-commit-msg: cannot read {argv[1]}", file=sys.stderr)
        return 2
    text = clean(text, comment_char())
    lines = text.splitlines()
    subject = lines[0] if lines else ""
    if subject.startswith(EXEMPT_PREFIXES):
        return 0
    if subject.startswith('Revert "'):
        if not TRAILER_RE.search(text):
            print(BLOCK_TRAILER, file=sys.stderr)
            return 1
        return 0
    if not SUBJECT_RE.match(subject):
        print(BLOCK_SUBJECT, file=sys.stderr)
        return 1
    if not TRAILER_RE.search(text):
        print(BLOCK_TRAILER, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

#!/usr/bin/env python3
"""Apply an expansion JSON: check six categories per source, add D-* rows.

Reads one expansion file, validates that every source carries exactly the six
checklist categories, refuses any source already expanded in the ledger before
adding anything, and adds one D-NNN ledger row per applicable entry for new
sources through ledger-amend.py add with spec_ref naming the source ID.
Applicable rows past --project-cap are added and then moved to
deferred-requested (the deferral queue); not-applicable entries are skipped,
never added. The cap counts rows already in the ledger, so a second run can
only fill what is left of the cap; --project-cap/--round-cap can only lower
the 30-per-project / 5-per-round defaults.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CATEGORIES = ["storage", "route", "validation", "default", "reset",
              "read-site"]
DEFAULT_PROJECT_CAP = 30
DEFAULT_ROUND_CAP = 5
ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]+$")
D_RE = re.compile(r"^D-([0-9]+)$")


def fail(msg, code=1):
    print(f"expand-apply: error: {msg}", file=sys.stderr)
    return code


def next_d_num(items):
    best = 0
    for row in items:
        if isinstance(row, dict):
            m = D_RE.match(str(row.get("id", "")))
            if m:
                best = max(best, int(m.group(1)))
    return best + 1


def expanded_range(items, source):
    nums = sorted(
        int(m.group(1)) for row in items if isinstance(row, dict)
        and str(row.get("spec_ref", "")) == source
        for m in [D_RE.match(str(row.get("id", "")))] if m)
    if not nums:
        return None
    return f"D-{nums[0]:03d}..D-{nums[-1]:03d}"


def amend(root, *args):
    cmd = [sys.executable,
           str(Path(__file__).resolve().parent / "ledger-amend.py"),
           "--root", str(root), *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="expand-apply.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--expansion", required=True)
    ap.add_argument("--project-cap", type=int, default=DEFAULT_PROJECT_CAP)
    ap.add_argument("--round-cap", type=int, default=DEFAULT_ROUND_CAP)
    ap.add_argument("--owner", default=None)
    ap.add_argument("--phase", default=None)
    args = ap.parse_args(argv)
    if args.project_cap < 1 or args.round_cap < 1:
        return fail("caps must be positive ints", 2)
    if args.project_cap > DEFAULT_PROJECT_CAP:
        return fail(f"--project-cap above {DEFAULT_PROJECT_CAP} is refused; "
                    "the flag can only lower the cap", 2)
    if args.round_cap > DEFAULT_ROUND_CAP:
        return fail(f"--round-cap above {DEFAULT_ROUND_CAP} is refused; "
                    "the flag can only lower the cap", 2)
    try:
        raw = Path(args.expansion).read_text(encoding="utf-8")
    except OSError as exc:
        return fail(f"cannot read expansion file: {exc}", 2)
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        return fail(f"expansion file unparsable: {exc}", 2)
    expansions = doc.get("expansions") if isinstance(doc, dict) else None
    if not isinstance(expansions, list) or not expansions:
        return fail("expansion file needs a non-empty expansions list", 2)
    ledger_file = Path(args.root) / "ledger" / "REQUIREMENTS.json"
    try:
        data = json.loads(ledger_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"cannot read ledger: {exc}")
    if not isinstance(data.get("items"), list):
        return fail("items must be a list")
    known = {str(r.get("id")) for r in data["items"] if isinstance(r, dict)}
    planned = []
    for pos, block in enumerate(expansions):
        tag = f"expansion {pos + 1}"
        if not isinstance(block, dict):
            return fail(f"{tag}: entry must be an object")
        source = str(block.get("source_id", ""))
        if not ID_RE.match(source):
            return fail(f"{tag}: malformed source id {source!r}")
        if source not in known:
            return fail(f"{source}: unknown source id")
        entries = block.get("entries")
        if not isinstance(entries, dict):
            return fail(f"{source}: entries must be an object")
        for cat in CATEGORIES:
            if cat not in entries:
                return fail(f"{source}: missing category {cat}")
        for cat in entries:
            if cat not in CATEGORIES:
                return fail(f"{source}: unknown category {cat}")
            entry = entries[cat]
            if not isinstance(entry, dict) or not isinstance(
                    entry.get("applicable"), bool):
                return fail(f"{source}: {cat} needs a boolean applicable")
            if entry["applicable"]:
                text = entry.get("text", "")
                if not isinstance(text, str) or not text.strip():
                    return fail(f"{source}: {cat} needs a non-empty text")
                planned.append((source, cat, text.strip(), None))
            else:
                reason = entry.get("reason", "")
                if not isinstance(reason, str) or not reason.strip():
                    return fail(
                        f"{source}: {cat} marked not applicable needs a reason")
                planned.append((source, cat, "", reason.strip()))
    applicable = [p for p in planned if p[3] is None]
    skipped = [p for p in planned if p[3] is not None]
    seen = []
    for block in expansions:
        if isinstance(block, dict):
            src = str(block.get("source_id", ""))
            if src in seen:
                return fail(f"{src}: repeated source id in one file")
            seen.append(src)
    refused = []
    for source in seen:
        span = expanded_range(data["items"], source)
        if span is not None:
            refused.append(
                f"{source}: already expanded as {span}; restore the ledger "
                "(git checkout -- ledger/) or add extra rows one at a time "
                "with ledger-amend.py add --id D-NNN --spec-ref "
                f"{source} before re-applying")
    if refused:
        for line in refused:
            print(f"expand-apply: error: {line}", file=sys.stderr)
        return 1
    used = sum(1 for r in data["items"] if isinstance(r, dict)
               and D_RE.match(str(r.get("id", ""))))
    free = max(0, args.project_cap - used)
    overflow = applicable[free:]
    if overflow and (not args.owner or not args.phase):
        return fail("overflow past --project-cap needs --owner and --phase", 2)
    num = next_d_num(data["items"])
    applied = []
    deferred = []
    for index, (source, cat, text, _reason) in enumerate(applicable):
        did = f"D-{num:03d}"
        num += 1
        tagged = f"[{cat}] {text}"
        proc = amend(args.root, "add", "--id", did, "--text", tagged,
                     "--spec-ref", source)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip().splitlines()
            tail = detail[-1] if detail else "ledger-amend.py failed"
            return fail(f"{did}: {tail}")
        if index < free:
            applied.append((did, source, cat))
        else:
            reason = (f"expansion over-cap ({args.project_cap} per project, "
                      f"{args.round_cap} per round): {cat} for {source}")
            proc = amend(args.root, "set-status", "--id", did,
                         "--status", "deferred-requested",
                         "--reason", reason, "--owner", args.owner,
                         "--phase", args.phase)
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout).strip().splitlines()
                tail = detail[-1] if detail else "ledger-amend.py failed"
                return fail(f"{did}: {tail}")
            deferred.append((did, source, cat))
        known.add(did)
    for source, cat, _text, reason in skipped:
        print(f"SKIPPED {source}/{cat}: {reason}")
    for did, source, cat in applied + deferred:
        print(f"APPLIED {did} {source}/{cat}")
    open_ids = [did for did, _s, _c in applied]
    for n in range(0, len(open_ids), args.round_cap):
        chunk = open_ids[n:n + args.round_cap]
        print(f"ROUND {n // args.round_cap + 1}: {' '.join(chunk)}")
    for did, source, cat in deferred:
        print(f"DEFERRED {did} {source}/{cat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Per-part install report for the Build Assurance Kit (ruling K14)."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path

PARTS = [
    ("1.1 ledger-amend", ("scripts/ledger-amend.py", "core/scripts/ledger-amend.py")),
    ("1.3 check-ledger", ("scripts/check-ledger.py", "core/scripts/check-ledger.py")),
    ("3.2 phase-gate", ("scripts/phase-gate.py", "core/scripts/phase-gate.py")),
    ("3.3 run-checks", ("scripts/run-checks.py", "core/scripts/run-checks.py")),
    ("3.9 trace-check", ("scripts/trace-check.py", "core/scripts/trace-check.py")),
    ("3.10 gate-loop", ("scripts/gate-loop.py", "core/scripts/gate-loop.py")),
    ("3.11 merge-check", ("scripts/merge-check.py", "core/scripts/merge-check.py")),
    ("3.12 gate-filter", ("scripts/gate-filter.py", "core/scripts/gate-filter.py")),
    ("4.1 plan-gate", ("scripts/plan-gate.py", "core/scripts/plan-gate.py")),
    ("4.2 size-gate", ("scripts/size-gate.py", "core/scripts/size-gate.py")),
    ("3.7 verdict-check", ("scripts/verdict-check.py", "core/scripts/verdict-check.py")),
    ("5.1 ledger-session-check", (".claude/hooks/ledger-session-check.py", "adapters/claude-code/hooks/ledger-session-check.py")),
    ("5.3 worktree-session-guard", (".claude/hooks/worktree-session-guard.py", "adapters/claude-code/hooks/worktree-session-guard.py")),
    ("6.1 ledger-verify-hook", (".claude/hooks/ledger-verify-hook.py", "adapters/claude-code/hooks/ledger-verify-hook.py")),
    ("6.2 ledger-checksum-guard", (".claude/hooks/ledger-checksum-guard.py", "adapters/claude-code/hooks/ledger-checksum-guard.py")),
    ("6.3 ledger-stop-gate", (".claude/hooks/ledger-stop-gate.py", "adapters/claude-code/hooks/ledger-stop-gate.py")),
    ("6.4 check-edit-guard", (".claude/hooks/check-edit-guard.py", "adapters/claude-code/hooks/check-edit-guard.py")),
    ("2.3 ledger-approve-hook", (".claude/hooks/ledger-approve-hook.py", "adapters/claude-code/hooks/ledger-approve-hook.py")),
    ("8.1 bak-init", ("scripts/bak-init.py", "core/scripts/bak-init.py")),
]

TAIL_BYTES = 1024 * 1024
OWNER_OPS = {"approve", "reject", "drop", "freeze", "set-check", "lock-checks",
             "baseline-checks", "lock-scope", "freeze-variant", "resume-gate"}  # gate-loop.py's R13 set


def kit_root():
    return Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _tail_lines(log_path):
    try:
        size = os.path.getsize(log_path)
    except OSError:
        return None
    try:
        with open(log_path, "rb") as fh:
            if size > TAIL_BYTES:
                fh.seek(-TAIL_BYTES, 2)
                fh.readline()
            data = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    return data.splitlines()


def last_seen(log_path, part):
    lines = _tail_lines(log_path)
    if lines is None:
        return "never"
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("part") == part:
            return f"{row.get('ts', '?')} {row.get('decision', '?')} {row.get('reason', '')}".rstrip()
    return "never"


def _when(value):
    try:
        t = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def open_stalls(root):
    """Latest line per C12.5 key, minus `resolved` keys and hand-offs that an
    owner op newer than the hand-off has ended (R13). OSError or ValueError
    when debug/stalls.jsonl is missing or unparsable."""
    last = {}
    for raw in (root / "debug" / "stalls.jsonl").read_text(encoding="utf-8").splitlines():
        s = json.loads(raw) if raw.strip() else None
        if isinstance(s, dict) and isinstance(s.get("key"), str):
            last.pop(s["key"], None)
            last[s["key"]] = s
    owner = None
    try:
        log = (root / "ledger" / "history" / "log.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        log = []
    for raw in log:
        try:
            op = json.loads(raw)
        except ValueError:
            continue
        t = _when(op.get("ts")) if isinstance(op, dict) and op.get("op") in OWNER_OPS else None
        if t and (owner is None or t > owner):
            owner = t
    out = []
    for s in last.values():
        t = _when(s.get("ts"))
        if s.get("action") == "resolved" or (s.get("action") == "handoff" and owner and t and owner > t):
            continue
        out.append(s)
    return out


def kit_version(kit):
    try:
        pkg = json.loads((kit / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    version = pkg.get("version")
    return str(version) if version else None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bak-status.py")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    root = Path(args.root)
    kit = kit_root()
    version = kit_version(kit)
    if version is not None:
        print(f"kit version: {version}")
    log_path = root / ".bak" / "bak-log.jsonl"
    for part, (proj_rel, kit_rel) in PARTS:
        proj = root / proj_rel
        ref = kit / kit_rel
        if not proj.is_file():
            if proj_rel.startswith(".claude/hooks/") and (kit / "adapters" / "claude-code" / "hooks" / Path(proj_rel).name).is_file():
                state = "plugin"
            else:
                state = "missing"
        elif ref.is_file():
            try:
                state = "installed identical" if sha(proj) == sha(ref) else "installed modified"
            except OSError:
                state = "installed unreadable"
        else:
            state = "installed"
        print(f"{part}: {state}; last-seen {last_seen(log_path, part)}")
    try:
        stalls = open_stalls(root)
        print(f"stalls: {len(stalls)} open")
        for s in stalls[-5:]:
            print(f"stall: {s.get('key')} ({s.get('action')})")
    except (OSError, ValueError):
        print("stalls: unknown (no debug/stalls.jsonl)")
    try:
        hand = root / "debug" / "HANDOFF.md"
        if hand.is_file() and "## Stall hand-off" in hand.read_text(encoding="utf-8"):
            print("stall hand-off: debug/HANDOFF.md")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

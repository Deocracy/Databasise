#!/usr/bin/env python3
"""Mechanical SD2/SD3: locate a stall key in the records, propose a verdict."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

VERDICTS = {"repeat-block": "correct-block", "no-change-loop": "correct-block",
            "oscillation": "correct-block", "no-progress": "correct-block",
            "hang": "environment", "dead-end": "missing-exit",
            "owner-wait": "owner-wait", "deadlock": "missing-exit",
            "infra": "environment", "silent-release": "missing-exit"}
# C12.4: these verdicts, and the class dead-end, hand off at once.
OWNER_ONLY = {"project-harness", "owner-wait"}


def read_jsonl(path):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def from_baklog(root, key):
    """SD2 for a reported key with no stalls.jsonl line: the bak-log lines
    for its part and target are the records; none means no such stall."""
    parts = key.split(":", 2)
    if len(parts) != 3:
        return None
    cls, part, target = parts
    lines = [e for e in read_jsonl(root / ".bak" / "bak-log.jsonl")
             if isinstance(e, dict) and e.get("part") == part and e.get("target") == target]
    if not lines:
        return None
    return {"ts": lines[-1].get("ts", ""), "key": key, "class": cls, "part": part,
            "target": target, "count": len(lines), "budget": 0,
            "evidence": [str(e.get("reason", "")) for e in lines[-5:]],
            "session": str(lines[-1].get("session") or ""),
            "harness": lines[-1].get("harness")}


def hand_off(root, key):
    """PS-R6: hand off through gate-loop.py --handoff-stall (the only
    HANDOFF.md writer, which also runs notify_cmd). Its STALL HAND-OFF line,
    or None when it cannot run."""
    script = Path(__file__).resolve().parent / "gate-loop.py"
    try:
        proc = subprocess.run([sys.executable, str(script), "--root", str(root),
                               "--handoff-stall", key],
                              capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    return next((line for line in proc.stdout.splitlines()
                 if line.startswith("STALL HAND-OFF: ")), None)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="stall-locate.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--key", default=None)
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--issue", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    if bool(args.key) == bool(args.latest):
        print("stall-locate.py: give --key KEY or --latest", file=sys.stderr)
        return 2
    stalls = read_jsonl(root / "debug" / "stalls.jsonl")
    if args.latest:
        if not stalls:
            print("stall-locate.py: no stall recorded", file=sys.stderr)
            return 1
        entry = stalls[-1]
        key = entry.get("key")
    else:
        key = args.key
        matches = [e for e in stalls if isinstance(e, dict) and e.get("key") == key]
        entry = matches[-1] if matches else from_baklog(root, key)
        if entry is None:
            print(f"stall-locate.py: no such stall {key}", file=sys.stderr)
            return 1
    cls = entry.get("class", "")
    part = entry.get("part", "")
    target = entry.get("target", "")
    evidence = entry.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = [str(evidence)]
    verdict = VERDICTS.get(cls, "correct-block")
    diagnosed = {"ts": entry.get("ts", ""), "key": key, "class": cls, "part": part,
                 "target": target, "count": entry.get("count", 0),
                 "budget": entry.get("budget", 0), "action": "diagnosed",
                 "verdict": verdict, "route": None,
                 "evidence": [str(e) for e in evidence][:5],
                 "session": entry.get("session"), "harness": entry.get("harness")}
    try:
        (root / "debug").mkdir(parents=True, exist_ok=True)
        with (root / "debug" / "stalls.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(diagnosed) + "\n")
    except OSError:
        pass
    handoff = None
    if cls == "dead-end" or verdict in OWNER_ONLY:
        handoff = hand_off(root, key)
    if args.json:
        print(json.dumps({"key": key, "class": cls, "part": part,
                          "target": target, "verdict": verdict,
                          "evidence": diagnosed["evidence"], "handoff": handoff}))
    else:
        print(f"class: {cls}\npart: {part}\ntarget: {target}\nverdict: {verdict}")
        for e in diagnosed["evidence"]:
            print(f"evidence: {e}")
        if handoff:
            print(handoff)
    if args.issue:
        debug = root / "debug"
        debug.mkdir(parents=True, exist_ok=True)
        n = len(list(debug.glob("stall-issue-*.md"))) + 1
        path = debug / f"stall-issue-{n}.md"
        path.write_text(
            f"---\nid: STALL-{n:03d}\nkind: stall\nclass: {cls}\npart: {part}\n"
            f"verdict: {verdict}\nbudget: {entry.get('budget')}, observed {entry.get('count')}\n"
            f"time_lost: unknown, from the records\nbypass_used: none\nstatus: open\nseverity: medium\n---\n\n"
            f"# STALL-{n:03d}: {cls} at {part}\n\n## Summary\n\nStall key {key}.\n\n"
            f"## Stall evidence\n\n" + "".join(f"- {e}\n" for e in diagnosed["evidence"]) + "\n"
            f"## Expected behavior\n\nThe part names its exit so the agent can proceed.\n\n"
            f"## Root cause in BAK\n\nUnknown; see evidence.\n\n## Proposed fix\n\nTriage per verdict {verdict}.\n\n"
            f"## Reproduction\n\nQ3 fixture for class {cls}.\n\n"
            f"## Acceptance check\n\nThe reproduction ends within budget with class {cls}, and Q1, Q2, Q3 and the corpus still pass.\n\n## Log\n\n- diagnosed {key}.\n",
            encoding="utf-8")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

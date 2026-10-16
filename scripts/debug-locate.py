#!/usr/bin/env python3
"""Mechanical D1/D2: for one ID, walk trace files S7 back to S2 and report
the first step where the item is not present, with C6 class and gate.
Never judges content: presence only. A file or entry that trace-check.py
--json rejects (invalid, stale, quote-not-found) counts as not present; this
script does not re-validate trace files itself (M10)."""
import argparse
import datetime
import glob
import json
import subprocess
import sys
from pathlib import Path

GATE_OF = {"S2": "G1", "S3": "G2", "S4": "G3", "S5": "G4",
           "S6": "G5", "S7": "G6"}
LOSS_OF = {"S2": "never-captured", "S3": "not-planned", "S4": "not-planned",
           "S5": "not-built", "S6": "lost-in-merge"}
WALK = ["S7", "S6", "S5", "S4", "S3", "S2"]
REJECT_CLASSES = ("invalid", "stale", "quote-not-found")


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def ledger_rows(root):
    try:
        data = json.loads((Path(root) / "ledger" / "REQUIREMENTS.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return None
    return {str(r.get("id")): r for r in data["items"] if isinstance(r, dict)}


def rejected_by_trace_check(root):
    """({file: detail}, {(file, id): detail}): the trace files and entries
    that trace-check.py --json, beside this script, rejects. None when its
    output cannot be read."""
    script = Path(__file__).resolve().parent / "trace-check.py"
    try:
        proc = subprocess.run([sys.executable, str(script), "--root", str(root), "--json"],
                              capture_output=True, text=True, timeout=300)
        viols = json.loads(proc.stdout)["violations"]
    except Exception:
        return None
    if not isinstance(viols, list):
        return None
    files, entries = {}, {}
    for v in viols:
        if not isinstance(v, dict) or v.get("class") not in REJECT_CLASSES \
                or not v.get("file"):
            continue
        if v.get("id") is not None:
            entries.setdefault((v["file"], v["id"]), str(v.get("detail")))
        elif v["class"] != "quote-not-found":  # an extra's quote, not an item's
            files.setdefault(v["file"], str(v.get("detail")))
    return files, entries


def listed(data, key):
    value = data.get(key) if isinstance(data, dict) else None
    return value if isinstance(value, list) else []


def file_state(path, step, want, rows, rejected):
    name = Path(path).name
    key = f"trace/{name}"
    files, entries = rejected
    if key in files:
        return ("invalid", files[key])
    if (key, want) in entries:
        return ("invalid", entries[(key, want)])
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return ("invalid", f"invalid {name}: unreadable")
    if step == "S2":
        for c in listed(data, "candidates"):
            if isinstance(c, dict) and c.get("id") == want:
                if c.get("decision") == "not-a-requirement":
                    return ("cut", f"cut in {name} as not-a-requirement")
                return ("present", "")
        return ("no-entry", f"no entry for {want} in {name}")
    for entry in listed(data, "items"):
        if isinstance(entry, dict) and entry.get("id") == want:
            status = entry.get("status")
            if status == "present":
                return ("present", "")
            if status == "missing":
                return ("missing", f"missing in {name}")
            if status == "cut":
                row = (rows or {}).get(want, {})
                if row.get("status") in ("dropped", "deferred-approved"):
                    return ("present", "")
                return ("cut-no-owner", f"cut in {name} with row status {row.get('status')}")
            return ("invalid", f"invalid {name}: bad status")
    return ("no-entry", f"no entry for {want} in {name}")


def ledger_history(root):
    try:
        lines = (Path(root) / "ledger" / "history" / "log.jsonl").read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    ops = []
    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            return None
        ops.append(obj)
    return ops


def s2_applies(root, want):
    """True when the row is subject to contract C4: the ledger is frozen,
    trace was enabled at or before the freeze, and the row was added at or
    before the freeze. Otherwise S2 says nothing about the row."""
    try:
        data = json.loads((Path(root) / "ledger" / "REQUIREMENTS.json").read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(data, dict) or data.get("frozen_at") is None:
        return False
    trace = data.get("trace")
    if not isinstance(trace, dict) or not isinstance(trace.get("since"), int):
        return False
    ops = ledger_history(root)
    if ops is None:
        return False
    try:
        freeze_v = next(o["v"] for o in ops
                        if isinstance(o, dict) and o.get("op") == "freeze"
                        and isinstance(o.get("v"), int))
    except StopIteration:
        return False
    if trace["since"] > freeze_v:
        # Trace recorded as enabled after the freeze op (e.g. enable-trace
        # ran after freeze in a fixture, so since > freeze op version):
        # C4 exempts only rows added after trace was enabled. A row from
        # at or before the freeze still gets S2.
        add_vs = [o["v"] for o in ops
                  if isinstance(o, dict) and o.get("op") == "add"
                  and o.get("id") == want and isinstance(o.get("v"), int)]
        if not add_vs:
            return bool(step_files(root, "S2"))
        return min(add_vs) <= freeze_v
    add_vs = [o["v"] for o in ops
              if isinstance(o, dict) and o.get("op") == "add"
              and o.get("id") == want and isinstance(o.get("v"), int)]
    if not add_vs:
        return False
    return min(add_vs) <= freeze_v


def step_files(root, step):
    trace = Path(root) / "trace"
    if step == "S2":
        out = [str(trace / "s2-a.json"), str(trace / "s2-b.json")]
        return [p for p in out if Path(p).is_file()]
    found = sorted(glob.glob(str(trace / f"s{step[1:]}.json")))
    found += sorted(glob.glob(str(trace / f"s{step[1:]}-*.json")))
    return found


def s7_pass_files(root, want, rejected):
    """Names of S7 files where the ID is present with verdict PASS."""
    files, entries = rejected
    found = []
    for path in step_files(root, "S7"):
        key = f"trace/{Path(path).name}"
        if key in files or (key, want) in entries:
            continue
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        if any(isinstance(entry, dict) and entry.get("id") == want
               and entry.get("status") == "present"
               and entry.get("verdict") == "PASS"
               for entry in listed(data, "items")):
            found.append(Path(path).name)
    return found


def s2_present(root, want, rows, rejected):
    """True when S2 files reference the ID (present, cut, or missing).
    S2 wins its row regardless of C4 history: files on disk are the
    fresher signal (fixtures predate the rule)."""
    if not step_files(root, "S2"):
        return False
    votes = [file_state(p, "S2", want, rows, rejected)
             for p in step_files(root, "S2")]
    return any(v[0] in ("present", "cut-no-owner", "missing") for v in votes)


def step_state(root, step, want, rows, rejected):
    files = step_files(root, step)
    if not files:
        if step in ("S2", "S6", "S7"):
            return None  # S2: no files; S6/S7: phase not run yet
        return ("absent", "not-checked", GATE_OF[step], f"no {step} trace file")
    if step == "S2" and not s2_present(root, want, rows, rejected) \
            and not s2_applies(root, want):
        return None  # no S2 reference and row not subject to C4: S2 says nothing
    votes = [file_state(p, step, want, rows, rejected) for p in files]
    if any(v[0] == "present" for v in votes):
        return ("present", None, None, "")
    if any(v[0] == "cut-no-owner" for v in votes):
        note = next(v[1] for v in votes if v[0] == "cut-no-owner")
        return ("absent", "cut-without-owner", GATE_OF[step], note)
    if any(v[0] == "missing" for v in votes):
        note = next(v[1] for v in votes if v[0] == "missing")
        if step == "S7":
            return ("absent", "not-checked", "G6", note)
        return ("absent", LOSS_OF[step], GATE_OF[step], note)
    if step == "S2":
        return ("absent", "never-captured", "G1", votes[0][1])
    return ("absent", "not-checked", GATE_OF[step], votes[0][1])


def locate_one(root, want, rows, rejected):
    earliest = None
    for step in ["S2", "S3", "S4", "S5", "S6", "S7"]:
        seen = step_state(root, step, want, rows, rejected)
        if seen is None or seen[0] == "present":
            continue
        if earliest is None:
            earliest = (step,) + seen[1:]
        if step == "S7":
            continue  # an S7 absence never wins: check wrongly-passed first
        if earliest is not None and earliest[0] != step:
            break
        # A valid S7 PASS upgrades the earliest absence to wrongly-passed,
        # unless the row never made it through S2.
        passed = s7_pass_files(root, want, rejected)
        if passed and s2_present(root, want, rows, rejected):
            _, _, _, note = seen
            return (step, "wrongly-passed", "G6",
                    f"{note}; present with verdict PASS in {passed[0]} "
                    f"(gate {GATE_OF[step]} should have caught it)")
        _, cls, gate, note = seen
        return (step, cls, gate, note)
    if earliest is not None and earliest[0] != "S7":
        passed = s7_pass_files(root, want, rejected)
        if passed and s2_present(root, want, rows, rejected):
            step, _, _, note = earliest
            return (step, "wrongly-passed", "G6",
                    f"{note}; present with verdict PASS in {passed[0]} "
                    f"(gate {GATE_OF[step]} should have caught it)")
        step, cls, gate, note = earliest
        return (step, cls, gate, note)
    return ("S7", "wrongly-passed", "G6",
            "trace shows present from S2 to S7")


def locate_extra(root, where, rejected):
    for step in WALK:
        for path in step_files(root, step):
            if f"trace/{Path(path).name}" in rejected[0]:
                continue
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
            except Exception:
                continue
            for entry in listed(data, "extra"):
                if isinstance(entry, dict) and entry.get("where") == where:
                    return (step, "extra-no-source", GATE_OF[step],
                            f"extra at {where} in {Path(path).name}")
    return (None, None, None, "")


def append_line(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="debug-locate.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--id", dest="ids", action="append", default=[])
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--extra", default=None)
    args = ap.parse_args(argv)
    root = str(args.root)
    if args.extra is None and not args.ids:
        print("debug-locate.py: needs --id ID", file=sys.stderr)
        return 2
    rejected = rejected_by_trace_check(root)
    if rejected is None:
        print("debug-locate.py: cannot read trace-check.py --json output", file=sys.stderr)
        return 1
    if args.extra is not None:
        step, cls, gate, evidence = locate_extra(root, args.extra, rejected)
        if step is None:
            print(f"no extra entry at {args.extra}")
            return 1
        print(json.dumps({"where": args.extra, "step_lost": step,
                          "class": cls, "gate": gate, "evidence": evidence}))
        return 0
    rows = ledger_rows(root)
    out = []
    for want in args.ids:
        step, cls, gate, evidence = locate_one(root, want, rows, rejected)
        obj = {"id": want, "step_lost": step, "class": cls,
               "gate": gate, "evidence": evidence}
        out.append(obj)
        if args.write:
            ts = utcnow()
            append_line(str(Path(root) / "debug" / "findings.jsonl"),
                        {"ts": ts, "round": args.round, "id": want,
                         "step_lost": step, "class": cls, "gate": gate,
                         "evidence": evidence, "fix": ""})
            append_line(str(Path(root) / "debug" / "loss-log.jsonl"),
                        {"ts": ts, "step": step, "class": cls,
                         "gate": gate, "id": want})
    for obj in out:
        print(json.dumps(obj))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

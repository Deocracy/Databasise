#!/usr/bin/env python3
"""Ledger gate: row rules, ID-set equality, deferral owner/phase/age."""
import argparse
import datetime
import hashlib
import json
import os
import re
import signal
import sys
from pathlib import Path


def _baklog(root, part, event, decision, reason, target=None, session=None):
    try:
        import importlib.util
        here = Path(__file__).resolve()
        for cand in (here.parent / "baklog.py",):  # the kit copy beside this script
            if cand.is_file():
                spec = importlib.util.spec_from_file_location("baklog", str(cand))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod.append(str(root), part, event, decision, reason, target=target, session=session)
    except BaseException:
        pass
    return None


ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]+$")
STATUS_VALUES = ["open", "done", "verified", "deferred-requested",
                 "deferred-approved", "dropped", "disputed", "parked"]
DEFERRAL_SET = {"deferred-requested", "deferred-approved"}
ROW_FIELDS = ["id", "text", "status", "spec_ref", "test_ref", "code_ref",
              "evidence", "owner", "phase", "deferred_at", "reason"]


def parse_phase(value):
    if isinstance(value, str) and value.strip().lower() == "backlog":
        return (10 ** 9,)
    try:
        parts = str(value).strip().split(".")
        if not parts or any(p == "" for p in parts):
            return None
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def tree_fingerprint(root):
    """sha256 over HEAD, the binary worktree diff, and each untracked non-ignored
    path plus its content, excluding .claude/ledger-state/ itself (the cache's
    own directory, or the cache would never hit). None when git is unavailable
    or any git call fails."""
    import subprocess
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"],
                              cwd=str(root), capture_output=True,
                              text=True, timeout=10)
        diff = subprocess.run(["git", "diff", "HEAD", "--binary"],
                              cwd=str(root), capture_output=True,
                              text=True, timeout=10)
        others = subprocess.run(["git", "ls-files", "--others",
                                 "--exclude-standard", "-z"],
                                cwd=str(root), capture_output=True,
                                text=True, timeout=10)
        if head.returncode != 0 or diff.returncode != 0 or others.returncode != 0:
            return None
        h = hashlib.sha256()
        h.update(head.stdout.encode("utf-8", "replace"))
        h.update(b"\x00")
        h.update(diff.stdout.encode("utf-8", "replace"))
        h.update(b"\x00")
        for name in sorted(p for p in others.stdout.split("\x00") if p):
            if name == ".claude/ledger-state/check-pass" or name.startswith(".claude/ledger-state/"):
                continue
            h.update(name.encode("utf-8", "replace"))
            h.update(b"\x00")
            try:
                h.update((Path(root) / name).read_bytes())
            except OSError:
                return None
            h.update(b"\x00")
        return h.hexdigest()
    except Exception:
        return None


def mockup_id_violations(root, data):
    """IDs of the frozen mockup variant missing from the built UI sources.

    Runs only when the user froze a variant (top-level mockup_freeze); with
    no frozen variant there is nothing checkable (S8-lean). The worker is
    scripts/mockup-id-check.py (G11 layout, else the kit copy); its lines
    are already exact violation lines, so they join the gate output as-is."""
    import subprocess
    import sys
    freeze = data.get("mockup_freeze")
    if freeze is None:
        return []
    if not isinstance(freeze, dict):
        return ["LEDGER: mockup_freeze must be an object or null"]
    script = None
    for cand in (Path(root) / "scripts" / "mockup-id-check.py",
                 Path(root) / "core" / "scripts" / "mockup-id-check.py",
                 Path(__file__).with_name("mockup-id-check.py")):
        if cand.is_file():
            script = cand
            break
    if script is None:
        return ["mockup check unavailable: mockup-id-check.py not found (G11 layout)"]
    try:
        proc = subprocess.run([sys.executable, str(script),
                               "--root", str(root)],
                              capture_output=True, text=True, timeout=30)
    except Exception:
        return ["mockup check could not run: mockup-id-check.py failed to execute"]
    lines = [line.strip() for line in
             (proc.stdout + "\n" + proc.stderr).splitlines()
             if line.strip()]
    if proc.returncode == 0:
        return []
    return lines if lines else ["mockup check failed with no output"]


def append_hang(root, cmd, secs, evidence):
    """PS-R7: a check_cmd killed at its timeout appends the C12 hang alarm
    line (C12.5) to debug/stalls.jsonl, the check as target."""
    import math
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from stall_time import iso_now
        ts = iso_now()
    except Exception:
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    mins = max(1, math.ceil(secs / 60))
    target = cmd[:200]
    entry = {"ts": ts, "key": f"hang:1.3 check-ledger:{target}", "class": "hang",
             "part": "1.3 check-ledger", "target": target, "count": mins,
             "budget": mins, "action": "alarm", "verdict": None, "route": None,
             "evidence": [evidence], "session": "",
             "harness": os.environ.get("BAK_HARNESS", "cli")}
    try:
        path = Path(root) / "debug" / "stalls.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def run_check_command(root, data, args):
    raw = data.get("check_cmd")
    cmd = raw.strip() if isinstance(raw, str) else ""
    if not cmd:
        print("check_cmd not set; skipping runnable check "
              "(S8-lean: gates on checkable items only)")
        return []
    state_dir = Path(root) / ".claude" / "ledger-state"
    stamp = state_dir / "check-pass"
    fingerprint = tree_fingerprint(root)
    if fingerprint is not None:
        try:
            if stamp.read_text(encoding="utf-8").strip() == fingerprint:
                print("check_cmd skipped (tree unchanged since last pass)")
                return []
        except OSError:
            pass
    try:
        timeout = float(args.check_timeout)
    except (TypeError, ValueError):
        print("LEDGER: --check-timeout must be a number")
        return ["LEDGER: --check-timeout must be a number"]
    import subprocess
    try:
        child = subprocess.Popen(["bash", "-o", "pipefail", "-c", cmd], cwd=str(root),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, start_new_session=True)
    except OSError:
        return ["check_cmd could not run: bash not found"]
    try:
        stdout, stderr = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        try:
            stdout, stderr = child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        label = str(int(timeout)) if float(timeout).is_integer() else ("%g" % timeout)
        append_hang(root, cmd, timeout, f"check_cmd timed out after {label}s: {cmd}")
        return [f"check_cmd timed out after {label}s: {cmd}"]
    if child.returncode == 0:
        if not ((stdout or "").strip() or (stderr or "").strip()):
            return [f"check_cmd printed nothing: {cmd}"]
        if fingerprint is not None:
            try:
                state_dir.mkdir(parents=True, exist_ok=True)
                ignore = state_dir / ".gitignore"
                if not ignore.exists():
                    ignore.write_text("*\n", encoding="utf-8")
                stamp.write_text(fingerprint, encoding="utf-8")
            except OSError:
                pass
        return []
    lines = [f"check_cmd failed with exit {child.returncode}: {cmd}"]
    all_lines = [line for line in ((stdout or "") + "\n" + (stderr or "")).splitlines()
                 if line.strip()]
    tail = all_lines[-20:]
    kept = [line for line in all_lines if line.startswith("TIMEOUT ") and line not in tail]
    lines.extend(f"check output: {line.rstrip()}" for line in kept)
    lines.extend(f"check output: {line.rstrip()}" for line in tail)
    return lines


def run_scope_check(root):
    """Scope-lock lines for --complete: run plan-gate.py --check-scope from the
    G11 layout. Fail closed when the script is missing or cannot run."""
    import subprocess
    import sys
    for cand in (Path(root) / "scripts" / "plan-gate.py",
                 Path(root) / "core" / "scripts" / "plan-gate.py",
                 Path(__file__).with_name("plan-gate.py")):
        if cand.is_file():
            script = cand
            break
    else:
        return ["scope check unavailable: plan-gate.py not found (G11 layout)"]
    try:
        proc = subprocess.run([sys.executable, str(script),
                               "--root", str(root), "--check-scope"],
                              capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        return ["LEDGER: scope check timed out"]
    except Exception:
        return ["scope check cannot run: plan-gate.py --check-scope failed to start"]
    if proc.returncode == 0:
        return []
    lines = [line.strip() for line in
             (proc.stdout + "\n" + proc.stderr).splitlines()
             if line.strip()]
    return lines if lines else ["scope check cannot run: plan-gate.py produced no output"]


def run_phase_gate(root):
    """Violation lines from phase-gate.py, so --complete joins the checks-before-code gate."""
    import subprocess
    for cand in (Path(root) / "scripts" / "phase-gate.py",
                 Path(root) / "core" / "scripts" / "phase-gate.py",
                 Path(__file__).resolve().parent / "phase-gate.py"):
        if cand.is_file():
            script = cand
            break
    else:
        return ["LEDGER: phase-gate.py not found; install the kit scripts (G11 layout)"]
    try:
        child = subprocess.run([sys.executable, str(script),
                                "--root", str(root)],
                               capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return ["LEDGER: phase-gate.py timed out after 30s"]
    except Exception:
        return ["LEDGER: phase-gate.py could not run"]
    if child.returncode == 0:
        return []
    lines = [line.strip() for line in (child.stdout + child.stderr).splitlines()
             if line.strip()]
    return lines or [f"LEDGER: phase-gate.py failed with exit {child.returncode}"]


def run_trace_gate(root):
    """Violation lines from trace-check.py, so --complete joins the trace gate.

    Runs trace-check.py with --json, prints each hard violation's detail,
    and saves the whole JSON object to .bak/last-trace.json so the Stop
    hook can record a round without running trace-check twice (ruling R12).
    Extra and info classes never fail --complete."""
    import subprocess
    for cand in (Path(root) / "scripts" / "trace-check.py",
                 Path(root) / "core" / "scripts" / "trace-check.py",
                 Path(__file__).resolve().parent / "trace-check.py"):
        if cand.is_file():
            script = cand
            break
    else:
        return ["LEDGER: trace-check.py not found; install the kit scripts (G11 layout)"]
    try:
        child = subprocess.run([sys.executable, str(script),
                                "--root", str(root), "--json"],
                               capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return ["LEDGER: trace-check.py timed out after 30s"]
    except Exception:
        return ["LEDGER: trace-check.py could not run"]
    try:
        payload = json.loads(child.stdout)
    except Exception:
        lines = [line.strip() for line in (child.stdout + child.stderr).splitlines()
                 if line.strip()]
        return lines or [f"LEDGER: trace-check.py failed with exit {child.returncode}"]
    if not isinstance(payload, dict) or not isinstance(payload.get("violations"), list):
        return [f"LEDGER: trace-check.py failed with exit {child.returncode}"]
    try:
        bak = Path(root) / ".bak"
        bak.mkdir(parents=True, exist_ok=True)
        ignore = bak / ".gitignore"
        if not ignore.exists():
            ignore.write_text("*\n", encoding="utf-8")
        (bak / "last-trace.json").write_text(
            json.dumps(payload) + "\n", encoding="utf-8")
    except OSError:
        pass
    lines = [str(v.get("detail", "")).strip() for v in payload["violations"]
             if isinstance(v, dict) and v.get("class") not in ("extra", "info")]
    lines = [line for line in lines if line]
    if lines:
        return lines
    if child.returncode == 0:
        return []
    return [f"LEDGER: trace-check.py failed with exit {child.returncode}"]


def run_deferral_scan(root):
    """Violation lines from deferral-scan.py, so --complete joins the capture gate."""
    import subprocess
    import sys
    for cand in (Path(root) / "scripts" / "deferral-scan.py",
                 Path(root) / "core" / "scripts" / "deferral-scan.py",
                 Path(__file__).resolve().parent / "deferral-scan.py"):
        if cand.is_file():
            script = cand
            break
    else:
        return ["LEDGER: deferral-scan.py not found; install the kit scripts (G11 layout)"]
    try:
        child = subprocess.run([sys.executable, str(script),
                                "--root", str(root)],
                               capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return ["LEDGER: deferral-scan.py timed out after 60s"]
    except Exception:
        return ["LEDGER: deferral-scan.py could not run"]
    if child.returncode == 0:
        return []
    lines = [line.strip() for line in (child.stdout + child.stderr).splitlines()
             if line.strip()]
    return lines or [f"LEDGER: deferral-scan.py failed with exit {child.returncode}"]


def main():
    ap = argparse.ArgumentParser(prog="check-ledger.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--current-phase", default=None)
    ap.add_argument("--base-log", default=None,
                    help="history log from the base commit; the current log must extend it")
    ap.add_argument("--complete", action="store_true",
                    help="also fail due open rows, unapproved deferrals and overdue deferrals")
    ap.add_argument("--verbose", action="store_true",
                    help="with --complete and no current_phase, list the open rows")
    ap.add_argument("--release", action="store_true",
                    help="with --complete, gate every requirement and finding row for release")
    ap.add_argument("--run-check", action="store_true",
                    help="also run the ledger check_cmd through the shell")
    # Budget under the 600 s Stop hook timeout (a killed hook does not block):
    # git fingerprint 3x10 + check_cmd 450 + kill wait 5 + mockup 30 + scope 15
    # + phase gate 30 + trace 30 = 590 s.
    ap.add_argument("--check-timeout", type=float, default=450,
                    help="seconds before check_cmd counts as timed out")
    args = ap.parse_args()
    root = Path(args.root)
    event = "check-ledger --complete" if args.complete else "check-ledger"
    ledger = root / "ledger" / "REQUIREMENTS.json"
    log = root / "ledger" / "history" / "log.jsonl"
    sums = root / "ledger" / "checksums.sha256"
    if not ledger.is_file():
        print("LEDGER: REQUIREMENTS.json missing")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: REQUIREMENTS.json missing")
        return 1
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except Exception:
        print("LEDGER: REQUIREMENTS.json unparsable")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: REQUIREMENTS.json unparsable")
        return 1
    if not isinstance(data, dict):
        print("LEDGER: REQUIREMENTS.json must be a JSON object")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: REQUIREMENTS.json must be a JSON object")
        return 1
    if not log.is_file():
        print("LEDGER: history/log.jsonl missing")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: history/log.jsonl missing")
        return 1
    ops = []
    try:
        for line in log.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ops.append(json.loads(line))
    except Exception:
        print("LEDGER: history/log.jsonl unparsable")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: history/log.jsonl unparsable")
        return 1
    if not sums.is_file():
        print("LEDGER: checksums.sha256 missing")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: checksums.sha256 missing")
        return 1
    try:
        lines = sums.read_text(encoding="utf-8").splitlines()
    except OSError:
        print("LEDGER: checksums.sha256 unparsable")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: checksums.sha256 unparsable")
        return 1
    want = {}
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            want[parts[1]] = parts[0]
    out = []
    n_hard = None
    info = []
    for name, path in (("REQUIREMENTS.json", ledger),
                       ("history/log.jsonl", log)):
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            out.append(f"LEDGER: checksum mismatch for {name}")
            continue
        if want.get(name) != digest:
            out.append(f"LEDGER: checksum mismatch for {name}")
    if args.base_log is not None:
        # A ledger rolled back to an older commit is consistent with itself, so only
        # the base commit's log can show that entries were removed or rewritten.
        try:
            base_ops = [json.loads(line) for line in
                        Path(args.base_log).read_text(encoding="utf-8").splitlines()
                        if line.strip()]
        except (OSError, ValueError):
            print("LEDGER: base log unreadable")
            _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: base log unreadable")
            return 1
        if ops[:len(base_ops)] != base_ops:
            out.append("LEDGER: history log does not extend the base log "
                       "(entries changed or removed)")
    for key in ("current_phase", "check_cmd"):
        if key in data and data[key] is not None and not isinstance(data[key], str):
            print(f"LEDGER: {key} must be a string or null")
            _baklog(root, "1.3 check-ledger", event, "fail", f"LEDGER: {key} must be a string or null")
            return 1
    mf = data.get("mockup_freeze")
    if mf is not None and not isinstance(mf, dict):
        print("LEDGER: mockup_freeze must be an object or null")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: mockup_freeze must be an object or null")
        return 1
    if "scope_lock" in data and data["scope_lock"] is not None \
            and not isinstance(data["scope_lock"], dict):
        print("LEDGER: scope_lock must be an object or null")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: scope_lock must be an object or null")
        return 1
    locks = data.get("check_locks")
    if locks is not None and not (
            isinstance(locks, dict) and isinstance(locks.get("commit"), str)
            and isinstance(locks.get("files"), dict)
            and all(isinstance(v, str) for v in locks["files"].values())):
        print("LEDGER: check_locks must be an object or null")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: check_locks must be an object or null")
        return 1
    guard = data.get("check_guard")
    if guard is not None and not (isinstance(guard, list)
                                  and all(isinstance(p, str) for p in guard)):
        print("LEDGER: check_guard must be a list or null")
        return 1
    grants = data.get("check_edit_grants")
    if grants is not None and not isinstance(grants, dict):
        print("LEDGER: check_edit_grants must be an object or null")
        return 1
    base = data.get("check_baseline")
    if base is not None and (not isinstance(base, int) or isinstance(base, bool)):
        print("LEDGER: check_baseline must be an integer or null")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: check_baseline must be an integer or null")
        return 1
    trace = data.get("trace", None)
    if trace is not None and not (
            isinstance(trace, dict) and trace.get("kind") in ("code", "document")
            and isinstance(trace.get("since"), int)
            and not isinstance(trace.get("since"), bool)):
        print("LEDGER: trace must be null or {kind, since}")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: trace must be null or {kind, since}")
        return 1
    if args.current_phase is None:
        cur = data.get("current_phase")
        if isinstance(cur, str) and cur.strip():
            args.current_phase = cur
    items = data.get("items")
    if not isinstance(items, list):
        print("LEDGER: items is not a list")
        _baklog(root, "1.3 check-ledger", event, "fail", "LEDGER: items is not a list")
        return 1
    seen = {}
    for row in items:
        rid = str(row.get("id", "?")) if isinstance(row, dict) else "?"
        seen[rid] = seen.get(rid, 0) + 1
    for rid, count in seen.items():
        if count > 1:
            out.append(f"{rid}: duplicate id")
    current = set()
    for row in items:
        if not isinstance(row, dict):
            out.append("?: row must be an object")
            continue
        rid = str(row.get("id", "?"))
        current.add(rid)
        for key in ROW_FIELDS:
            if key not in row:
                out.append(f"{rid}: missing field {key}")
        if not ID_RE.match(rid):
            out.append(f"{rid}: malformed id")
        if not isinstance(row.get("text"), str) or not row.get("text", ""):
            out.append(f"{rid}: empty text")
        if row.get("status") not in STATUS_VALUES:
            out.append(f"{rid}: bad status {row.get('status')}")
        kind = row.get("kind", "requirement")
        if kind not in ("requirement", "finding", "follow-up"):
            out.append(f"{rid}: bad kind {kind}")
        if row.get("status") == "parked" and kind != "follow-up":
            out.append(f"{rid}: parked needs kind follow-up")
        if str(row.get("phase", "")).strip().lower() == "backlog" \
                and row.get("status") not in ("parked", "deferred-requested",
                                              "deferred-approved"):
            out.append(f"{rid}: backlog needs status parked, deferred-requested "
                       f"or deferred-approved (found {row.get('status')})")
        if row.get("status") in DEFERRAL_SET:
            for key in ("owner", "phase", "reason"):
                if not isinstance(row.get(key), str) or not row.get(key, ""):
                    out.append(f"{rid}: deferral missing {key}")
            try:
                day = datetime.date.fromisoformat(str(row.get("deferred_at", "")))
            except ValueError:
                out.append(f"{rid}: deferral bad deferred_at")
            else:
                if day > datetime.date.today():
                    out.append(f"{rid}: deferred_at in the future")
            if args.current_phase is not None:
                now_p = parse_phase(args.current_phase)
                tgt_p = parse_phase(str(row.get("phase", "")))
                if now_p is not None and tgt_p is not None and tgt_p < now_p:
                    out.append(f"{rid}: deferral overdue (target phase "
                               f"{row.get('phase')}, current phase "
                               f"{args.current_phase})")
    added = {}
    for op in ops:
        if isinstance(op, dict) and op.get("op") in ("add", "add-finding", "add-follow-up") \
                and isinstance(op.get("id"), str):
            added.setdefault(op["id"], op.get("v", "?"))
    for rid in sorted(set(added) - current):
        out.append(f"{rid}: deleted (added in v{added[rid]})")
    for rid in sorted(current - set(added)):
        if rid != "?":
            out.append(f"{rid}: not added through ledger-amend.py")
    quoted = set()
    for op in ops:
        if not isinstance(op, dict):
            continue
        if op.get("op") in ("approve", "drop") \
                and isinstance(op.get("id"), str) \
                and isinstance(op.get("quote"), str) \
                and op.get("quote", "").strip():
            quoted.add((op["op"], op["id"]))
    for row in items:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id", "?"))
        if row.get("status") == "deferred-approved" \
                and ("approve", rid) not in quoted:
            out.append(f"{rid}: deferred-approved without a recorded user approval quote")
        if row.get("status") == "dropped" \
                and ("drop", rid) not in quoted:
            out.append(f"{rid}: dropped without a recorded user cut quote")
    if args.release and not args.complete:
        print("check-ledger.py: --release needs --complete")
        return 2
    if args.complete:
        try:
            findings = sorted((Path(root) / "verifier").glob("findings-*.json"))
        except OSError:
            findings = []
        named = set()
        for row in items:
            if isinstance(row, dict) and isinstance(row.get("finding"), dict):
                named.add((str(row["finding"].get("source", "")),
                           str(row["finding"].get("key", ""))))
        for path in findings:
            try:
                rel = path.relative_to(Path(root)).as_posix()
            except ValueError:
                rel = path.name
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                err = " ".join(str(exc).split())[:200] or exc.__class__.__name__
                out.append(f"{rel}: unreadable findings file ({err})")
                continue
            if not isinstance(payload, dict):
                out.append(f"{rel}: unreadable findings file "
                           f"(top level must be an object)")
                continue
            entries = payload.get("findings")
            if not isinstance(entries, list):
                out.append(f"{rel}: unreadable findings file "
                           f"(findings must be a list)")
                continue
            for i, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    shown = repr(entry)[:120]
                    out.append(f"{rel}: finding entry {i} is not an object ({shown})")
                    continue
                key = entry.get("key")
                if not isinstance(key, str) or not key.strip():
                    out.append(f"{rel}: finding entry {i} has bad key ({key!r})")
                    continue
                sev = entry.get("severity")
                norm = sev.lower() if isinstance(sev, str) else ""
                if norm not in ("critical", "important", "minor"):
                    out.append(f"{rel}: finding entry {i} ({key}) has bad "
                               f"severity ({sev!r})")
                    continue
                if norm == "minor":
                    continue
                if (rel, key) not in named and \
                        (str(path), key) not in named and \
                        (path.name, key) not in named and \
                        (f"verifier/{path.name}", key) not in named:
                    out.append(f"{rel}: finding {key} "
                               f"({norm}) has no ledger row (add-finding)")
        cur_raw = data.get("current_phase")
        cur_set = isinstance(cur_raw, str) and bool(cur_raw.strip())
        cur_str = cur_raw.strip() if cur_set else "unset"
        cur_p = parse_phase(cur_raw) if cur_set else None
        if not cur_set:
            n_open = sum(1 for row in items
                         if isinstance(row, dict) and row.get("status") == "open")
            if n_open:
                out.append(f"current_phase not set: set it (set-phase) so rows planned for later phases are not reported as due; {n_open} open rows")
            for row in items:
                if not isinstance(row, dict):
                    continue
                rid = str(row.get("id", "?"))
                status = row.get("status")
                if status == "deferred-requested":
                    out.append(f"{rid}: deferred-requested without user approval")
                elif status == "disputed":
                    out.append(f"{rid}: check disputed; the owner approves the proposed check "
                               "(approve) or refuses it (reject)")
            if args.verbose:
                for row in items:
                    if not isinstance(row, dict):
                        continue
                    if row.get("status") != "open":
                        continue
                    rid = str(row.get("id", "?"))
                    rp_raw = str(row.get("phase", ""))
                    rp_str = rp_raw.strip() if rp_raw.strip() else "unset"
                    out.append(f"{rid}: open (phase {rp_str})")
        else:
            later = []
            info = []
            backlog_n = sum(1 for row in items if isinstance(row, dict)
                            and str(row.get("phase", "")).strip().lower() == "backlog"
                            and row.get("status") in ("parked", "deferred-approved"))
            for row in items:
                if not isinstance(row, dict):
                    continue
                rid = str(row.get("id", "?"))
                status = row.get("status")
                rp_raw = str(row.get("phase", ""))
                is_backlog = rp_raw.strip().lower() == "backlog"
                row_p = parse_phase(rp_raw) if rp_raw.strip() else None
                if status == "open":
                    rp_str = rp_raw.strip() if rp_raw.strip() else "unset"
                    if is_backlog:
                        pass
                    elif not rp_raw.strip() or row_p is None or row_p <= cur_p:
                        out.append(f"{rid}: open and due (row phase {rp_str}, current phase {cur_str})")
                    else:
                        later.append((rid, row_p))
                elif status == "deferred-requested":
                    out.append(f"{rid}: deferred-requested without user approval")
                elif status == "disputed":
                    if not rp_raw.strip() or cur_p is None or row_p is None or row_p <= cur_p:
                        out.append(f"{rid}: check disputed; the owner approves the proposed check "
                                   "(approve) or refuses it (reject)")
                elif status in ("parked", "deferred-approved"):
                    if not is_backlog and row_p is not None and row_p <= cur_p:
                        out.append(f"{rid}: back due (parked until phase {rp_raw.strip()})")
                    elif not is_backlog and row_p is not None and row_p > cur_p:
                        later.append((rid, row_p))
            if later:
                phases = sorted({q for _, q in later})
                nxt = ".".join(str(n) for n in phases[0])
                at_next = sum(1 for _, q in later if q == phases[0])
                info.append(f": info (planned later: {len(later)} rows; next phase {nxt}: {at_next} rows)")
            info.append(f": info (backlog: {backlog_n} rows)")
        if args.release:
            for row in items:
                if not isinstance(row, dict):
                    continue
                rid = str(row.get("id", "?"))
                kind = row.get("kind", "requirement")
                status = row.get("status")
                if kind in ("requirement", "finding"):
                    if status not in ("done", "verified", "deferred-approved", "dropped"):
                        out.append(f"{rid}: not releasable (status {status})")
                elif status == "parked":
                    rp_raw = str(row.get("phase", ""))
                    rp_str = rp_raw.strip() if rp_raw.strip() else "unset"
                    info.append(f"{rid}: info (parked follow-up, target phase {rp_str})")
        out.extend(run_deferral_scan(root))
        out.extend(mockup_id_violations(root, data))
        n_hard = len(out)
        out.extend(info)
    if args.complete and isinstance(data.get("scope_lock"), dict):
        out.extend(run_scope_check(root))
    if args.run_check:
        code = run_check_command(root, data, args)
        out.extend(code)
    if args.complete and isinstance(data.get("trace"), dict):
        out.extend(run_trace_gate(root))
    if args.complete and not (isinstance(data.get("trace"), dict)
                              and data["trace"].get("kind") == "document"):
        out.extend(run_phase_gate(root))
    for line in out:
        print(line)
    if isinstance(n_hard, int):
        hard = out[:n_hard] + out[n_hard + len(info):]
    else:
        hard = out
    hard_fail = [line for line in hard if str(line).strip()]
    _baklog(root, "1.3 check-ledger", event, "fail" if hard_fail else "pass", "\n".join(map(str, out)) or "no violations")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

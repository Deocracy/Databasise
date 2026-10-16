#!/usr/bin/env python3
"""Labeled check runner (contract C11.4): per-check timeout, TIMEOUT names the hung check."""
import argparse
import math
import os
import signal
import subprocess
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


def parse_list(path):
    rows = []
    seen = set()
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        return None, f"run-checks.py: cannot read list file: {exc}"
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        label, tab, cmd = raw.partition("\t")
        label = label.strip()
        cmd = cmd.strip()
        if not tab or not label or not cmd:
            return None, f"run-checks.py: line {lineno} needs <label><TAB><command>"
        if label in seen:
            return None, f"run-checks.py: duplicate label {label}"
        seen.add(label)
        rows.append((label, cmd))
    return rows, ""


def parse_timeout(value):
    try:
        secs = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(secs) or secs <= 0:
        return None
    return secs


def usage(err):
    print(err, file=sys.stderr)
    return 2, err


# PB-R11 (I4): a SIGTERM/SIGINT/SIGHUP kills the current check's group and
# exits 143, so no orphan survives. Set in run_list; restored in a finally.
_current = {"proc": None}


def _on_term(_signum, _frame):
    proc = _current["proc"]
    if proc is not None and proc.poll() is None:
        try:
            if hasattr(os, "killpg"):
                os.killpg(proc.pid, signal.SIGKILL)
            else:  # no process groups (Windows): kill the shell itself
                proc.kill()
        except OSError:
            pass
    raise SystemExit(143)


def _pdeathsig_preexec():
    """On Linux, die with the runner: a SIGKILL of run-checks.py then reaches
    the check's process group too (ctypes PR_SET_PDEATHSIG in preexec_fn)."""
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        libc.prctl(1, signal.SIGTERM, 0, 0, 0)  # PR_SET_PDEATHSIG = 1
    except BaseException:
        pass


def _spawn(cmd):
    """Spawn one check in its own process group; wrap it so a SIGKILL of the
    runner reaches the group: the bash wrapper traps TERM/HUP/INT and kills
    its own group, and on Linux PDEATHSIG fires when the runner dies."""
    wrapped = "trap 'kill -KILL 0' TERM HUP INT\n{\n" + cmd + "\n} &\nwait $!\n"
    kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                  start_new_session=True, text=True, errors="replace")
    if sys.platform.startswith("linux"):
        kwargs["preexec_fn"] = _pdeathsig_preexec
    return subprocess.Popen(
        ["bash", "-o", "pipefail", "-c", wrapped], **kwargs)


def stall_line(root, label, shown):
    """Append one C12 hang line to debug/stalls.jsonl for a killed check;
    count and budget are whole minutes (C12.5)."""
    import datetime
    import json as _json
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from stall_time import iso_now
        ts = iso_now()
    except Exception:
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace(
            "+00:00", "Z")
    mins = max(1, math.ceil(parse_timeout(shown) / 60))
    entry = {"ts": ts, "key": f"hang:3.3 run-checks:{label}",
             "class": "hang", "part": "3.3 run-checks", "target": label,
             "count": mins, "budget": mins, "action": "alarm", "verdict": None,
             "route": None, "evidence": [f"TIMEOUT {label} after {shown}s"],
             "session": "",
             "harness": os.environ.get("BAK_HARNESS", "cli")}
    try:
        d = Path(root) / "debug"
        d.mkdir(parents=True, exist_ok=True)
        with (d / "stalls.jsonl").open("a", encoding="utf-8") as f:
            f.write(_json.dumps(entry) + "\n")
    except OSError:
        pass


def append_stall_hang(root, label, shown):
    stall_line(root, label, shown)


def run_list(argv):
    """Run the list; return (exit code, bak-log reason)."""
    ap = argparse.ArgumentParser(
        prog="run-checks.py",
        description=("Per-check timeouts only bound each check: keep "
                     "each-timeout x the number of checks under "
                     "check-ledger's --check-timeout (450 s default)."))
    ap.add_argument("--list", required=True)
    ap.add_argument("--each-timeout", required=True)
    ap.add_argument("--only", default=None)
    ap.add_argument("--root", default=".",
                    help="project root for debug/stalls.jsonl (default: the current directory)")
    args = ap.parse_args(argv)
    secs = parse_timeout(args.each_timeout)
    if secs is None:
        return usage("run-checks.py: --each-timeout must be seconds greater than 0")
    rows, err = parse_list(args.list)
    if rows is None:
        return usage(err)
    if args.only is not None:
        rows = [(label, cmd) for label, cmd in rows if label == args.only]
        if not rows:
            return usage(f"run-checks.py: --only {args.only} matches no label")
    old = {}
    for name in ("SIGTERM", "SIGINT", "SIGHUP"):
        if hasattr(signal, name):
            try:
                old[name] = signal.signal(getattr(signal, name), _on_term)
            except (OSError, ValueError, RuntimeError):
                pass
    shown = str(args.each_timeout)
    passed = failed = timed = 0
    try:
        for label, cmd in rows:
            try:
                child = _spawn(cmd)
                _current["proc"] = child
            except OSError:
                print(f"FAIL {label} exit 127", flush=True)
                failed += 1
                continue
            try:
                try:
                    text, _ = child.communicate(timeout=secs)
                except subprocess.TimeoutExpired:
                    try:
                        if hasattr(os, "killpg"):
                            os.killpg(child.pid, signal.SIGKILL)
                        else:  # no process groups (Windows): kill the shell itself
                            child.kill()
                    except OSError:
                        pass
                    try:
                        child.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                    print(f"TIMEOUT {label} after {shown}s", flush=True)
                    timed += 1
                    append_stall_hang(args.root, label, shown)
                    continue
            finally:
                _current["proc"] = None
            code = child.returncode
            if code == 0 and not (text or "").strip():
                print(f"FAIL {label} no output", flush=True)
                failed += 1
            elif code == 0:
                print(f"PASS {label}", flush=True)
                passed += 1
            else:
                print(f"FAIL {label} exit {code}", flush=True)
                failed += 1
    finally:
        for name, handler in old.items():
            try:
                signal.signal(getattr(signal, name), handler)
            except (OSError, ValueError, RuntimeError):
                pass
    summary = f"checks: {passed} pass, {failed} fail, {timed} timeout"
    print(summary, flush=True)
    return (1 if (failed or timed) else 0), summary


def main(argv=None):
    code, reason = run_list(argv)
    # A check_cmd runs with the project root as cwd, so bak-log goes there (C8).
    _baklog(".", "3.3 run-checks", "run-checks", "fail" if code else "pass", reason)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

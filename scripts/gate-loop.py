#!/usr/bin/env python3
"""Gate loop (contract C6, rulings R12 and R13).

With --record (run by the Stop hook, never by the agent) it appends one line
per failed stop to trace/rounds.jsonl, from the violations check-ledger saved
in .bak/last-trace.json (--from), so trace-check never runs twice. The round
after the third consecutive failure, or the first round whose open items are
all owner-only, writes a handoff line and debug/HANDOFF.md instead. A stop
with no hard violations appends a pass line only when a series is open, which
closes it (R22). Without --record it prints the status and the next step and
writes nothing."""
import argparse
import datetime
import hashlib
import json
import os
import re
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


CHECKER_STEP = {"S2": "list-items", "S3": "check-coverage",
                "S4": "check-coverage", "S5": "check-coverage",
                "S6": "merge check", "S7": "review"}
RETRY_CLASSES = {"not-checked", "stale", "invalid", "quote-not-found", "unknown-item"}
SOFT_CLASSES = ("extra", "info")
OWNER_ONLY = "cut-without-owner"
# C11.1: a disputed or timed-out check; the Stop hook records such check-ledger lines (C11.4).
OWNER_ONLY_CLASSES = (OWNER_ONLY, "check-at-fault")
ROUNDS = "trace/rounds.jsonl"
REWRITTEN = f"{ROUNDS} rewritten since HEAD"
# acknowledge-handoff is not here: it ends the pause hand-off, not a gate one (R24).
OWNER_OPS = {"approve", "reject", "drop", "freeze", "set-check", "lock-checks",
             "baseline-checks", "lock-scope", "freeze-variant", "resume-gate"}
RESUME = ("python3 scripts/ledger-amend.py resume-gate "
          "--reason <text> --quote <your words>")
OWNER_ANSWER = {OWNER_ONLY: "type `DROP <ID> <reason>` to confirm the cut, "
                            "or `APPROVE <ID>` for a pending deferral",
                "check-at-fault": "for a disputed check, type `APPROVE <ID>` to take the "
                                  "proposed check or `REJECT <ID> <reason>` to keep the "
                                  "old one; for a timed-out check, fix the hang, then run "
                                  f"`{RESUME}`"}
DEFAULT_ANSWER = (f"instruct the fix, then run `{RESUME}`; "
                  "or type `DROP <ID> <reason>` to cut the row")


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def head_of(root):
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, cwd=str(root), timeout=10)
        sha = proc.stdout.strip()
        if proc.returncode == 0 and sha:
            return sha
    except Exception:
        pass
    return ""


def rounds_path(root):
    return Path(root) / ROUNDS


def rewritten_since_head(root):
    """True when HEAD holds trace/rounds.jsonl and the working-tree file does
    not begin with it byte for byte: the round log is append-only (R13)."""
    try:
        proc = subprocess.run(["git", "show", f"HEAD:./{ROUNDS}"],
                              capture_output=True, cwd=str(root), timeout=10)
    except Exception:
        return False
    if proc.returncode != 0:
        return False  # no repository, no commit, or HEAD has no round log
    try:
        now = rounds_path(root).read_bytes()
    except OSError:
        now = b""
    return not now.startswith(proc.stdout)


def hard_of(violations):
    return [v for v in violations
            if isinstance(v, dict) and v.get("class") not in SOFT_CLASSES]


def read_ledger(root):
    try:
        data = json.loads((Path(root) / "ledger" / "REQUIREMENTS.json")
                          .read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def read_rounds(root):
    """Round lines with a known result and an integer round. Undecodable or
    unparsable lines are skipped, never repaired: the file is append-only."""
    try:
        text = rounds_path(root).read_bytes().decode("utf-8", "replace")
    except FileNotFoundError:
        return []
    rows = []
    for line in text.splitlines():
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("result") in ("pass", "fail", "handoff"):
            try:
                int(obj.get("round"))
            except (TypeError, ValueError):
                continue
            rows.append(obj)
    return rows


def owner_version(root):
    """Highest `v` of an owner op in ledger/history/log.jsonl, else -1."""
    try:
        lines = (Path(root) / "ledger" / "history" / "log.jsonl") \
            .read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return -1
    best = -1
    for line in lines:
        try:
            op = json.loads(line)
        except ValueError:
            continue
        if isinstance(op, dict) and op.get("op") in OWNER_OPS \
                and isinstance(op.get("v"), int):
            best = max(best, op["v"])
    return best


def series(rows, owner_v):
    """(fails, handed_off) of the current round series. A series ends at a
    pass, or at a hand-off that an owner op newer than its ledger_version
    has ended (R13); handoff lines never count as rounds."""
    fails, handed_off = 0, False
    for row in reversed(rows):
        if row["result"] == "pass":
            break
        if row["result"] == "handoff":
            version = row.get("ledger_version")
            if owner_v > (version if isinstance(version, int) else -1):
                break
            handed_off = True
            continue
        fails += 1
    return fails, handed_off


def atomic_write(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def append_round(root, entry):
    """Append one round line, adding a missing trailing newline first so
    the new line does not join the previous one."""
    p = rounds_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_file():
        with open(p, "rb+") as fh:
            fh.seek(0, 2)
            if fh.tell() > 0:
                fh.seek(fh.tell() - 1)
                if fh.read(1) != b"\n":
                    fh.write(b"\n")
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def default_checker():
    here = Path(__file__).resolve().parent
    return ["python3", str(here / "trace-check.py"), "--json"]


def run_checker(root, checker):
    try:
        proc = subprocess.run(checker + ["--root", str(root)], capture_output=True,
                              text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return None, "checker timed out"
    except Exception:
        return None, "checker could not start"
    try:
        text = proc.stdout
        try:
            payload = json.loads(text)
        except Exception:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end < 0 or end < start:
                raise ValueError("bad payload")
            payload = json.loads(text[start:end + 1])
        if not isinstance(payload, dict):
            raise ValueError("bad payload")
        viols = payload.get("violations")
        if not isinstance(viols, list):
            raise ValueError("bad violations")
        hard = hard_of(viols)
        if proc.returncode not in (0, 1):
            raise ValueError("bad exit code")
        if proc.returncode == 0 and hard:
            raise ValueError("exit 0 with hard violations")
        if proc.returncode == 1 and not hard:
            raise ValueError("exit 1 with no hard violations")
        return viols, ""
    except Exception:
        return None, "checker output unparsable"


def violations_of(root, args):
    """(violations, error): from --from FILE (relative to --root) when given,
    else from the checker."""
    if args.from_file is None:
        return run_checker(root, args.checker or default_checker())
    src = Path(args.from_file)
    if not src.is_absolute():
        src = Path(root) / src
    try:
        payload = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("violations"), list):
        return payload["violations"], ""
    return None, f"{args.from_file} is not trace-check --json output"


def is_ledger_violation(first):
    if not isinstance(first, dict):
        return False
    if first.get("class") == "invalid" \
            and str(first.get("file") or "").startswith("ledger/"):
        return True
    return first.get("step") is None


def hint_for(hard, handed_off=False):
    if not hard:
        return "gate passes"
    if handed_off:
        return "read debug/HANDOFF.md and stop for the owner"
    # Owner-only items go to the hand-off; name an item the agent can fix.
    first = next((v for v in hard if v.get("class") != OWNER_ONLY), hard[0])
    if first.get("file") == ROUNDS:
        return f"ask the owner to restore {ROUNDS} from HEAD"
    if is_ledger_violation(first):
        return "fix the ledger error and re-run the gate"
    step = str(first.get("step") or "")
    cls = str(first.get("class") or "")
    rid = first.get("id")
    path = str(first.get("file") or f"trace/{step.lower()}.json")
    if cls in RETRY_CLASSES:
        return f"run the {CHECKER_STEP.get(step, 'check-coverage')} checker for {step} ({path})"
    label = rid or first.get("detail", "the extra entry")
    return f"run the debugger for {label} ({cls} at {step})"


STALL_PART = "3.10 gate-loop"
STALL_CLASSES = ("repeat-block", "no-change-loop", "oscillation", "no-progress", "hang",
                 "dead-end", "owner-wait", "deadlock", "infra", "silent-release")
# PS-R2: the Stop gate lets a stop through while check-ledger --complete fails.
RELEASE_KEY = "silent-release:6.3 ledger-stop-gate:check-ledger --complete"
STALL_STATE = ".bak/stall-state.json"


def stall_now():
    """C12.2 clock: stall_time.py beside this script honours BAK_NOW."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from stall_time import iso_now
        return iso_now()
    except Exception:
        return utcnow()


def run_notify(root, kind, key):
    """C12.6, after every hand-off: notify_cmd as `bash -c CMD` with a 10 s
    timeout, output discarded; a failure is one bak-log alarm line."""
    cmd = (read_ledger(root) or {}).get("notify_cmd")
    if not isinstance(cmd, str) or not cmd.strip():
        return
    env = dict(os.environ, BAK_HANDOFF="debug/HANDOFF.md", BAK_HANDOFF_KIND=kind,
               BAK_STALL_KEY=key, BAK_DEFERRED="debug/DEFERRED.md")
    try:
        proc = subprocess.run(["bash", "-c", cmd], cwd=str(root), env=env,
                              capture_output=True, timeout=10)
    except Exception as exc:
        _baklog(root, STALL_PART, "notify", "alarm",
                f"notify_cmd failed ({exc.__class__.__name__})")
        return
    if proc.returncode != 0:
        _baklog(root, STALL_PART, "notify", "alarm",
                f"notify_cmd failed with exit {proc.returncode}")


def stall_state(root):
    try:
        st = json.loads((Path(root) / STALL_STATE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    return st if isinstance(st, dict) else {}


def save_stall_state(root, st):
    try:
        atomic_write(Path(root) / STALL_STATE, json.dumps(st) + "\n")
    except OSError:
        pass


def open_stall_handoffs(root, st):
    """Stall keys handed off with no owner op newer than the hand-off (R13)."""
    owner_v = owner_version(root)
    marks = st.get("handed_off")
    return {k for k, v in (marks.items() if isinstance(marks, dict) else ())
            if owner_v <= (v if isinstance(v, int) else -1)}


def append_stall(root, key, count, budget, action, evidence):
    cls, part, target = key.split(":", 2)
    entry = {"ts": stall_now(), "key": key, "class": cls, "part": part,
             "target": target, "count": count, "budget": budget, "action": action,
             "verdict": None, "route": None, "evidence": evidence, "session": "",
             "harness": os.environ.get("BAK_HARNESS", "cli")}
    try:
        path = Path(root) / "debug" / "stalls.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def handoff_stall(root, key, count=0, budget=0, evidence=()):
    """C12.5: a `## Stall hand-off` section in debug/HANDOFF.md, the
    stalls.jsonl handoff line, then notify_cmd. A key already handed off is
    refused with the same line and writes nothing (R13). Never blocks."""
    cls, part, target = key.split(":", 2)
    line = (f"STALL HAND-OFF: {cls} at {part} on {target}; written to "
            "debug/HANDOFF.md for the owner; stop and wait for the owner.")
    st = stall_state(root)
    if key not in open_stall_handoffs(root, st):
        try:
            path = Path(root) / "debug" / "HANDOFF.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"\n## Stall hand-off\n\n- {key}\n\nOwner commands: "
                         f"`python3 scripts/stall-locate.py --key \"{key}\"` shows the "
                         f"evidence; instruct the fix, then run `{RESUME}`.\n\n"
                         "An owner command newer than this hand-off ends it.\n")
        except OSError:
            pass
        append_stall(root, key, count, budget, "handoff", list(evidence))
        marks = st.get("handed_off") if isinstance(st.get("handed_off"), dict) else {}
        marks[key] = (read_ledger(root) or {}).get("ledger_version")
        st["handed_off"] = marks
        save_stall_state(root, st)
        run_notify(root, "stall", key)
    print(line)
    _baklog(root, STALL_PART, "gate-loop --handoff-stall", "alarm", line, target=target)
    return 0


def round_set(root):
    """Digest of this round's hard violations (debug/last-round.json)."""
    try:
        viols = json.loads((Path(root) / "debug" / "last-round.json")
                           .read_text(encoding="utf-8"))["violations"]
        canon = sorted(json.dumps(v, sort_keys=True) for v in viols)
    except Exception:
        return None
    return hashlib.sha256(json.dumps(canon).encode()).hexdigest()[:16]


def loop_hit(root, rows, st, same):
    """No-change-loop and oscillation on this stop's new fail round, over
    the trailing run of fail rounds; a pass or a handoff ends the run.
    (class, count, budget, again) or None; `again` means the key already
    alarmed in this run, so this crossing hands off (C12.4)."""
    # PS-R3: a pass directly followed by a handoff is part of that hand-off.
    seq = [r for i, r in enumerate(rows) if not (
        r["result"] == "pass" and i + 1 < len(rows) and rows[i + 1]["result"] == "handoff")]
    if not seq or seq[-1]["result"] != "fail" or str(seq[-1].get("ts")) == st.get("gate_seen"):
        return None
    sets = st.get("gate_sets") if isinstance(st.get("gate_sets"), dict) else {}
    sets[str(seq[-1].get("ts"))] = round_set(root)
    st["gate_seen"] = str(seq[-1].get("ts"))
    run = []  # (ts, digest) of the trailing fail rounds, newest first
    for r in reversed(seq):
        if r["result"] != "fail":
            break
        run.append((str(r.get("ts")), sets.get(str(r.get("ts")))))
    stamps = [ts for ts, _ in run]
    st["gate_sets"] = {ts: d for ts, d in run if d is not None}
    alarms = st.get("gate_alarms") if isinstance(st.get("gate_alarms"), dict) else {}
    alarms = st["gate_alarms"] = {k: v for k, v in alarms.items() if v in stamps}
    same_run = []
    for ts, d in run:
        if d is None or d != run[0][1]:
            break
        same_run.append(ts)
    since = same_run.index(alarms["no-change-loop"]) if alarms.get("no-change-loop") in same_run else None
    count = len(same_run) if since is None else since
    if count >= same:
        if since is None:
            alarms["no-change-loop"] = run[0][0]
        return ("no-change-loop", count, same, since is not None)
    d = [x[1] for x in run[:3]]
    if len(d) == 3 and None not in d and d[0] == d[2] != d[1]:
        again = alarms.get("oscillation") in stamps[1:]
        if not again:
            alarms["oscillation"] = run[0][0]
        return ("oscillation", 1, 1, again)
    return None


def stall_check(root, release, evidence=()):
    """PS-R2, run by the Stop hook after this stop's round is recorded. It
    does nothing while the gate loop is handed off. --release: the Stop gate
    lets this stop through with hard failures open (`evidence`, M10), so with
    no hand-off open it writes the silent-release hand-off."""
    rows = read_rounds(root)
    if series(rows, owner_version(root))[1]:
        print("stall: the gate loop has handed off")
        _baklog(root, STALL_PART, "gate-loop --stall-check", "info",
                "stall: the gate loop has handed off")
        return 0
    budgets = (read_ledger(root) or {}).get("stall_budgets")
    same = budgets.get("same_rounds") if isinstance(budgets, dict) else None
    same = same if isinstance(same, int) and same > 0 else 2
    st = stall_state(root)
    hit = loop_hit(root, rows, st, same)
    save_stall_state(root, st)
    release = release and not open_stall_handoffs(root, st)
    if hit is not None:
        cls, count, budget, again = hit
        key = f"{cls}:{STALL_PART}:{ROUNDS}"
        rounds = [json.dumps(r) for r in rows[-3:]]
        if again or key in open_stall_handoffs(root, st):
            return handoff_stall(root, key, count, budget, rounds)
        line = (f"STALL ALARM: {cls} at {STALL_PART} on {ROUNDS} ({count} of {budget}); "
                "stop this approach, run the stall debugger once (skill debug-stall), "
                "and fix only product-side causes.")
        append_stall(root, key, count, budget, "alarm", rounds)
        _baklog(root, STALL_PART, "gate-loop --stall-check", "alarm", line, target=ROUNDS)
        if not release:  # M11: a release records its alarm, then hands off
            print(line)
            return 2
    if release:
        return handoff_stall(root, RELEASE_KEY, 1, 1, list(evidence) or [
            "check-ledger --complete fails and the Stop gate lets the stop through"])
    print("stall: ok")
    _baklog(root, STALL_PART, "gate-loop --stall-check", "info", "stall: ok")
    return 0


def write_handoff(root, fails, max_rounds, hard):
    lines = ["# Gate hand-off", "",
             f"Rounds used: {fails} of {max_rounds}. The trace gate still fails; "
             "work stops for the owner.",
             "", "Open items (id, step, class, detail):", ""]
    lines += [f"- {v.get('id') or '-'}, {v.get('step') or '-'}, {v.get('class')}: "
              f"{v.get('detail')}" for v in hard]
    lines += ["", "Owner commands:", ""]
    lines += [f"- {cls}: {OWNER_ANSWER.get(cls, DEFAULT_ANSWER)}"
              for cls in sorted({str(v.get("class")) for v in hard})]
    lines += ["", "An owner command newer than this hand-off ends it; the next "
              "failing stop starts round 1 of a new series."]
    atomic_write(Path(root) / "debug" / "HANDOFF.md",
                 "\n".join(lines) + "\n" + open_stall_sections(root))


def open_stall_sections(root):
    """M7: the `## Stall hand-off` sections of debug/HANDOFF.md whose key is
    still open, which the gate hand-off's rewrite keeps."""
    try:
        text = (Path(root) / "debug" / "HANDOFF.md").read_text(encoding="utf-8")
    except (OSError, ValueError):
        return ""
    keys = open_stall_handoffs(root, stall_state(root))
    head = "\n## Stall hand-off\n"
    return "".join(head + s for s in text.split(head)[1:]
                   if s.lstrip("\n").split("\n", 1)[0][2:] in keys)


def hang_key(v):
    """PS-R7: the stall key of an owner-only check hang (a run-checks TIMEOUT
    line or check-ledger's check_cmd timeout line), the check as target;
    else None."""
    detail = str(v.get("detail"))
    if v.get("class") != "check-at-fault":
        return None
    if re.fullmatch(r"TIMEOUT \S+ after \S+s", detail):
        return f"hang:3.3 run-checks:{detail.split()[1][:200]}"
    if detail.startswith("check_cmd timed out after ") and ": " in detail:
        return f"hang:1.3 check-ledger:{detail.split(': ', 1)[1][:200]}"
    return None


def notice_due(root, rows, handed_off):
    """M7 (spec 17.5): a gate hand-off notifies once. While it stays open
    (R13; a PS-R3 pass-handoff pair is one hand-off) it notifies again only
    once per owner_wait_h."""
    pair = len(rows) > 1 and rows[-1]["result"] == "pass" \
        and rows[-2]["result"] == "handoff" and series(rows[:-1], owner_version(root))[1]
    st = stall_state(root)
    now = stall_now()
    if handed_off or pair:
        budgets = (read_ledger(root) or {}).get("stall_budgets")
        hours = budgets.get("owner_wait_h") if isinstance(budgets, dict) else None
        hours = hours if isinstance(hours, int) and hours > 0 else 24
        try:
            since = datetime.datetime.fromisoformat(now.replace("Z", "+00:00")) - \
                datetime.datetime.fromisoformat(str(st.get("gate_notice")).replace("Z", "+00:00"))
            if since < datetime.timedelta(hours=hours):
                return False
        except (TypeError, ValueError):
            pass
    st["gate_notice"] = now
    save_stall_state(root, st)
    return True


def record(root, hard, max_rounds, ledger_version):
    """Append this stop's line to trace/rounds.jsonl; 0 on a pass, else 1."""
    tampered = rewritten_since_head(root)
    if tampered:
        hard = hard + [{"id": None, "step": None, "class": "invalid",
                        "file": ROUNDS, "detail": REWRITTEN}]
    rows = read_rounds(root)
    fails, handed_off = series(rows, owner_version(root))
    if not (hard or fails or handed_off):
        # R22: a pass line only closes an open series; with none open, write nothing.
        print(f"round 1 of {max_rounds}: pass")
        print("next step: gate passes")
        _baklog(root, "3.10 gate-loop", "gate-loop --record", "pass", f"round 1 of {max_rounds}: pass")
        return 0
    atomic_write(Path(root) / "debug" / "last-round.json",
                 json.dumps({"violations": hard}) + "\n")
    entry = {"round": fails + 1, "ts": utcnow(), "head": head_of(root),
             "ledger_version": ledger_version, "violations": len(hard)}
    if tampered:
        entry["detail"] = REWRITTEN
    for v in hard:
        print(v.get("detail"))
    if not hard:
        append_round(root, {**entry, "result": "pass"})
        print(f"round {fails + 1} of {max_rounds}: pass")
        print("next step: gate passes")
        _baklog(root, "3.10 gate-loop", "gate-loop --record", "pass", f"round {fails + 1} of {max_rounds}: pass")
        return 0
    if handed_off or fails >= max_rounds \
            or all(v.get("class") in OWNER_ONLY_CLASSES for v in hard):
        append_round(root, {**entry, "result": "handoff"})
        write_handoff(root, fails, max_rounds, hard)
        hangs = [hang_key(v) for v in hard]
        for key, v in zip(hangs, hard):
            if key:
                handoff_stall(root, key, evidence=[str(v.get("detail"))])
        # A hang-only hand-off notifies once, through its stall hand-off.
        if not all(hangs) and notice_due(root, rows, handed_off):
            run_notify(root, "gate", "")
        print("HANDOFF debug/HANDOFF.md")
        _baklog(root, "3.10 gate-loop", "gate-loop --record", "block", "handoff")
        return 1
    append_round(root, {**entry, "result": "fail"})
    print(f"round {fails + 1} of {max_rounds}: fail")
    print(f"next step: {hint_for(hard)}")
    _baklog(root, "3.10 gate-loop", "gate-loop --record", "fail", f"round {fails + 1} of {max_rounds}: fail")
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gate-loop.py", allow_abbrev=False)
    ap.add_argument("--root", default=".")
    ap.add_argument("--max-rounds", type=int, default=3)
    ap.add_argument("--record", action="store_true",
                    help="append this round to trace/rounds.jsonl (the Stop hook does this)")
    ap.add_argument("--from", dest="from_file", default=None,
                    help="trace-check --json output to read instead of running the checker")
    ap.add_argument("--owner-only", action="store_true",
                    help="with --record --from: the file holds owner-only check-ledger "
                         "items (C11.4); record them whether or not trace is enabled")
    ap.add_argument("--checker", nargs=argparse.REMAINDER, default=None)
    ap.add_argument("--stall-check", action="store_true",
                    help="check no-change-loop, oscillation and silent-release (the Stop hook runs this)")
    ap.add_argument("--release", action="store_true",
                    help="with --stall-check: the Stop gate lets this stop through with hard "
                         "failures open; --from FILE lists them as violation details")
    ap.add_argument("--handoff-stall", default=None, metavar="KEY",
                    help="write a stall hand-off for KEY (<class>:<part>:<target>)")
    args = ap.parse_args(argv)
    root = str(args.root)
    if args.max_rounds < 1:
        print("gate-loop.py: --max-rounds must be >= 1", file=sys.stderr)
        return 2
    if args.handoff_stall is not None:
        parts = args.handoff_stall.split(":", 2)
        if len(parts) != 3 or parts[0] not in STALL_CLASSES or not all(parts):
            print("gate-loop.py: --handoff-stall needs KEY as <class>:<part>:<target>",
                  file=sys.stderr)
            return 2
        return handoff_stall(root, f"{parts[0]}:{parts[1]}:{parts[2][:200]}")
    if args.stall_check:
        viols = violations_of(root, args)[0] if args.from_file else None
        return stall_check(root, args.release, [str(v.get("detail")) for v in viols or ()
                                                if isinstance(v, dict)])
    data = read_ledger(root)
    if data is None:
        print("LEDGER: REQUIREMENTS.json missing or unreadable")
        _baklog(root, "3.10 gate-loop", "gate-loop --record" if args.record else "gate-loop", "fail" if args.record else "info", "LEDGER: REQUIREMENTS.json missing or unreadable")
        return 1
    if data.get("trace") is None and not (args.record and args.owner_only and args.from_file):
        print("trace: not enabled")
        _baklog(root, "3.10 gate-loop", "gate-loop --record" if args.record else "gate-loop", "info", "trace: not enabled")
        return 0
    viols, err = violations_of(root, args)
    if viols is None:
        print(f"next step: run the checker again ({err})")
        _baklog(root, "3.10 gate-loop", "gate-loop --record" if args.record else "gate-loop", "fail" if args.record else "info", f"next step: run the checker again ({err})")
        return 1
    hard = hard_of(viols)
    try:
        if args.record:
            return record(root, hard, args.max_rounds, data.get("ledger_version"))
        _, handed_off = series(read_rounds(root), owner_version(root))
    except OSError as exc:
        print(f"gate-loop.py: cannot use trace/rounds.jsonl ({exc})", file=sys.stderr)
        _baklog(root, "3.10 gate-loop", "gate-loop --record" if args.record else "gate-loop", "fail" if args.record else "info", f"gate-loop.py: cannot use trace/rounds.jsonl ({exc})")
        return 1
    for v in hard:
        print(v.get("detail"))
    print(f"next step: {hint_for(hard, handed_off)}")
    _baklog(root, "3.10 gate-loop", "gate-loop", "info", f"next step: {hint_for(hard, handed_off)}")
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())

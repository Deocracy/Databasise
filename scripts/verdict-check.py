#!/usr/bin/env python3
"""Verdict gate: validate verifier verdict files and merge one report."""
import argparse
import json
import re
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
VERDICTS = ("PASS", "FAIL", "REVIEW")
FILE_LINE_RE = re.compile(r"^[^:\s]+\.[A-Za-z0-9]+:\d+$")
EXIT_RE = re.compile(r"exit\s*[:=]?\s*\d+", re.IGNORECASE)
EXIT0_RE = re.compile(r"exit\s*[:=]?\s*0\b", re.IGNORECASE)
SCREEN_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
RANK = {"PASS": 1, "REVIEW": 2, "FAIL": 3}


def split_parts(evidence):
    return [p.strip() for p in evidence.split(";") if p.strip()]


def is_screenshot_shape(part):
    text = part.strip()
    path = text[2:] if text.startswith("./") else text
    low = path.lower()
    return path.startswith("verifier/evidence/") and low.endswith(SCREEN_EXTS)


def resolve_under(root_resolved, rel):
    try:
        target = (root_resolved / rel).resolve()
    except Exception:
        return None
    try:
        if not target.is_relative_to(root_resolved):
            return None
    except Exception:
        return None
    return target


def file_line_ok(part, root_resolved):
    if not FILE_LINE_RE.match(part):
        return False
    path_s, _, line_s = part.rpartition(":")
    try:
        lineno = int(line_s)
    except ValueError:
        return False
    if lineno < 1:
        return False
    path = path_s.strip()
    target = resolve_under(root_resolved, path)
    if target is None:
        return False
    try:
        if not target.is_file():
            return False
        with target.open(encoding="utf-8", errors="ignore") as fh:
            n = sum(1 for _ in fh)
        return lineno <= n
    except OSError:
        return False


def screenshot_ok(part, root_resolved):
    if not is_screenshot_shape(part):
        return False
    text = part.strip()
    rel = text[2:] if text.startswith("./") else text
    target = resolve_under(root_resolved, rel)
    if target is None:
        return False
    try:
        ev_dir = (root_resolved / "verifier" / "evidence").resolve()
    except Exception:
        return False
    try:
        if not target.is_relative_to(ev_dir):
            return False
    except Exception:
        return False
    try:
        return target.is_file()
    except OSError:
        return False


RUN_RE = __import__("re").compile(r"^run:(\d+)$")


def check_runs_by_version(root):
    try:
        lines = (Path(root) / "ledger" / "history" / "log.jsonl").read_text(
            encoding="utf-8").splitlines()
    except OSError:
        return {}
    runs = {}
    for line in lines:
        if not line.strip():
            continue
        try:
            op = json.loads(line)
        except ValueError:
            continue
        if isinstance(op, dict) and op.get("op") == "check-run" \
                and isinstance(op.get("v"), int) and not isinstance(op.get("v"), bool):
            runs[op["v"]] = op
    return runs


def completed_after_since(root, trace_since):
    try:
        lines = (Path(root) / "ledger" / "history" / "log.jsonl").read_text(
            encoding="utf-8").splitlines()
    except OSError:
        return {}
    done_at = {}
    for line in lines:
        if not line.strip():
            continue
        try:
            op = json.loads(line)
        except ValueError:
            continue
        if not isinstance(op, dict) or not isinstance(op.get("v"), int):
            continue
        changes = op.get("changes")
        moved = changes.get("status") if isinstance(changes, dict) else None
        if isinstance(moved, list) and len(moved) == 2 \
                and moved[0] not in ("done", "verified") \
                and moved[1] in ("done", "verified"):
            done_at[str(op.get("id", "?"))] = op["v"]
    return {rid: (v is not None and trace_since is not None and v > trace_since)
            for rid, v in done_at.items()}


def _cmd_names_path(cmd, path_part):
    """PB-R9: the run's cmd must name the check path, as record-fail requires
    (the path in the command itself, not in a # comment)."""
    import shlex as _shlex
    if not isinstance(cmd, str) or not isinstance(path_part, str):
        return False
    if not path_part.strip():
        return False
    try:
        raw = _shlex.split(cmd, comments=False)
        tokens = []
        for token in raw:
            if token.startswith("#"):
                break
            tokens.append(token)
    except ValueError:
        return False
    return any(path_part in token for token in tokens)


def run_part_ok(part, rid, test_ref, commit, runs):
    m = RUN_RE.match(part.strip())
    if not m:
        return False
    if not isinstance(commit, str) or not commit.strip():
        return False
    op = runs.get(int(m.group(1)))
    if not isinstance(op, dict) or op.get("id") != rid:
        return False
    if not (op.get("exit") == 0 and op.get("tree_clean") is True
            and op.get("head") == commit):
        return False
    ref = op.get("ref")
    if not isinstance(ref, str) or not ref.strip():
        return False
    if not isinstance(test_ref, str) or not test_ref.strip():
        return False
    if ref != test_ref:
        return False
    path_part = test_ref.split("::", 1)[0].strip()
    if not _cmd_names_path(op.get("cmd"), path_part):
        return False
    out = op.get("output")
    return isinstance(out, str) and bool(out.strip())


def _is_document_kind(data):
    """R38: the ledger's trace kind is `document` (a text row has no test_ref,
    so no recorded run of its own check can exist)."""
    trace = data.get("trace") if isinstance(data, dict) else None
    return isinstance(trace, dict) and trace.get("kind") == "document"


def pass_evidence_ok(evidence, root_resolved, rid=None, test_ref=None,
                     commit=None, runs=None, document_kind=False):
    if not isinstance(evidence, str):
        return False, False
    parts = split_parts(evidence)
    if not parts:
        return False, False
    runs = runs if isinstance(runs, dict) else {}
    has_file = any(file_line_ok(p, root_resolved) for p in parts)
    has_exit0 = any(EXIT0_RE.search(p) and not RUN_RE.match(p.strip()) for p in parts)
    has_shot = any(screenshot_ok(p, root_resolved) for p in parts)
    has_run = any(run_part_ok(p, rid or "", test_ref or "", commit, runs)
                  for p in parts)
    if document_kind:
        return has_file, False
    return has_file and (has_exit0 or has_shot or has_run), \
        (has_file and has_exit0 and not has_shot and not has_run)


def file_line_shape(part):
    return bool(FILE_LINE_RE.match(part.strip()))


def fail_evidence_shape(evidence):
    if not isinstance(evidence, str):
        return False
    parts = split_parts(evidence)
    if not parts:
        return False
    for p in parts:
        if FILE_LINE_RE.match(p) or is_screenshot_shape(p):
            return True
        if EXIT_RE.search(p):
            return True
    return False


def fail_part_valid(part, root_resolved):
    if FILE_LINE_RE.match(part):
        return file_line_ok(part, root_resolved)
    if is_screenshot_shape(part):
        return screenshot_ok(part, root_resolved)
    return bool(EXIT_RE.search(part))


def main():
    ap = argparse.ArgumentParser(prog="verdict-check.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--report", default=None)
    ap.add_argument("--ids", default=None)
    ap.add_argument("verdicts", nargs="+")
    args = ap.parse_args()
    root = Path(args.root)
    try:
        root_resolved = root.resolve()
    except Exception:
        root_resolved = root
    ledger_path = root / "ledger" / "REQUIREMENTS.json"
    try:
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
    except Exception:
        print("LEDGER: REQUIREMENTS.json missing or unparsable")
        _baklog(root, "3.7 verdict-check", "verdict-check", "fail", "LEDGER: REQUIREMENTS.json missing or unparsable")
        return 1
    items = data.get("items")
    if not isinstance(items, list):
        print("LEDGER: items is not a list")
        _baklog(root, "3.7 verdict-check", "verdict-check", "fail", "LEDGER: items is not a list")
        return 1
    known = set()
    required = set()
    for row in items:
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            known.add(row["id"])
            if row.get("status") in ("done", "verified"):
                required.add(row["id"])
    if args.ids is not None:
        wanted = {s.strip() for s in args.ids.split(",") if s.strip()}
        if not wanted:
            print("LEDGER: --ids names no IDs")
            return 2
        unknown = sorted(wanted - known)
        if unknown:
            print(f"LEDGER: unknown id in --ids: {', '.join(unknown)}")
            return 2
        required = required & wanted
    try:
        ledger_version = int(data.get("ledger_version", 0))
    except (TypeError, ValueError):
        print("LEDGER: ledger_version is not an integer")
        _baklog(root, "3.7 verdict-check", "verdict-check", "fail", "LEDGER: ledger_version is not an integer")
        return 1
    out = []
    notes = []
    candidates = {}
    for name in args.verdicts:
        try:
            payload = json.loads(Path(name).read_text(encoding="utf-8"))
        except Exception:
            out.append(f"LEDGER: verdict file {name} unparsable")
            continue
        if not isinstance(payload, dict):
            out.append(f"LEDGER: verdict file {name} must be an object")
            continue
        bm = payload.get("builder_model")
        vm = payload.get("verifier_model")
        if isinstance(bm, str) or isinstance(vm, str):
            b_show = bm if isinstance(bm, str) else "unknown"
            v_show = vm if isinstance(vm, str) else "unknown"
            notes.append(f"LEDGER: verdict file {name} builder_model "
                         f"{b_show} verifier_model {v_show}")
            if (isinstance(bm, str) and isinstance(vm, str)
                    and bm and bm == vm):
                notes.append(f"LEDGER: builder and verifier used the same "
                             f"model {bm}; independence is not shown")
        file_version = payload.get("ledger_version")
        if not isinstance(file_version, int):
            out.append(f"LEDGER: verdict file {name} needs integer ledger_version")
            continue
        if "commit" in payload and not isinstance(payload.get("commit"), str):
            out.append(f"LEDGER: verdict file {name} commit must be a string")
            continue
        if file_version != ledger_version:
            out.append(f"LEDGER: verdict file {name} ledger_version "
                       f"{file_version} != ledger {ledger_version}")
        entries = payload.get("verdicts")
        if not isinstance(entries, list):
            out.append(f"LEDGER: verdict file {name} verdicts is not a list")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                out.append("?: verdict entry must be an object")
                continue
            rid = entry.get("id")
            if not isinstance(rid, str) or not ID_RE.match(rid):
                out.append(f"{rid}: malformed id")
                continue
            if rid not in known:
                out.append(f"{rid}: unknown id {rid}")
                continue
            verdict = entry.get("verdict")
            if verdict not in VERDICTS:
                out.append(f"{rid}: bad verdict {verdict}")
                continue
            if verdict == "REVIEW":
                reason = entry.get("reason") if "reason" in entry else None
                if reason is None or (isinstance(reason, str)
                                      and not reason.strip()):
                    out.append(f"{rid}: REVIEW without a reason")
                    continue
                if not isinstance(reason, str):
                    out.append(f"{rid}: reason must be a string")
                    continue
                raw_evidence = entry.get("evidence")
                if raw_evidence is None:
                    evidence_str = ""
                elif isinstance(raw_evidence, str):
                    evidence_str = raw_evidence.strip()
                else:
                    out.append(f"{rid}: evidence must be a string")
                    continue
                candidates.setdefault(rid, []).append(
                    {"id": rid, "verdict": verdict,
                     "evidence": evidence_str, "reason": reason})
                continue
            evidence = entry.get("evidence")
            if verdict == "PASS":
                runs = check_runs_by_version(root)
                trace = data.get("trace") if isinstance(data, dict) else None
                since = trace.get("since") if isinstance(trace, dict) else None
                since = since if isinstance(since, int) and not isinstance(since, bool) else None
                commit = payload.get("commit")
                test_ref = next((r.get("test_ref") for r in items
                                 if isinstance(r, dict) and r.get("id") == rid),
                                None)
                document_kind = _is_document_kind(data)
                ok, only_exit0 = pass_evidence_ok(evidence, root_resolved, rid,
                                                  test_ref, commit, runs,
                                                  document_kind=document_kind)
                # C11.6: typed `exit 0` stays enough with trace off and for rows
                # not done after trace.since (set-status logs every done move).
                # R38: in a document project the file:line alone is enough.
                if ok and only_exit0 and not document_kind and since is not None \
                        and completed_after_since(root, since).get(rid, False):
                    out.append(f"{rid}: PASS evidence \"exit 0\" is not a recorded run "
                               f"(use run:<version>)")
                    continue
                if not ok:
                    out.append(f"{rid}: verdict without evidence")
                    continue
            else:
                if not fail_evidence_shape(evidence):
                    out.append(f"{rid}: verdict without evidence")
                    continue
                if not any(fail_part_valid(p, root_resolved)
                           for p in split_parts(evidence)):
                    out.append(f"{rid}: verdict without evidence")
                    continue
            reason = entry.get("reason", "")
            if reason is None:
                reason = ""
            if not isinstance(reason, str):
                out.append(f"{rid}: reason must be a string")
                continue
            candidates.setdefault(rid, []).append(
                {"id": rid, "verdict": verdict,
                 "evidence": str(evidence).strip(), "reason": reason})
    merged = {}
    for rid in sorted(candidates):
        entries = candidates[rid]
        worst = max(entries, key=lambda e: RANK[e["verdict"]])["verdict"]
        worst_entries = [e for e in entries if e["verdict"] == worst]
        chosen = sorted(worst_entries,
                        key=lambda e: (e["evidence"], e["reason"]))[0]
        merged[rid] = chosen
        tokens = {e["verdict"] for e in entries}
        if len(entries) > 1 and len(tokens) > 1:
            out.append(f"{rid}: conflicting verdicts; keeping {worst}")
    for rid in sorted(required):
        if rid not in merged:
            out.append(f"{rid}: no verdict")
    invalid_for_report = sorted(out)
    failures = sorted(rid for rid, v in merged.items() if v["verdict"] == "FAIL")
    for rid in failures:
        out.append(f"{rid}: FAIL {merged[rid]['evidence']}")
    reviews = sorted(rid for rid, v in merged.items() if v["verdict"] == "REVIEW")
    review_lines = []
    for rid in reviews:
        reason_text = merged[rid]["reason"]
        evidence_text = merged[rid]["evidence"]
        if evidence_text:
            review_lines.append(f"{rid}: REVIEW {reason_text} | {evidence_text}")
        else:
            review_lines.append(f"{rid}: REVIEW {reason_text}")
    passes = sorted(rid for rid, v in merged.items() if v["verdict"] == "PASS")
    if args.report is not None:
        report = {"ledger_version": ledger_version,
                  "pass": passes,
                  "fail": [{"id": rid, "evidence": merged[rid]["evidence"],
                            "reason": merged[rid]["reason"]} for rid in failures],
                  "review": [{"id": rid, "evidence": merged[rid]["evidence"],
                              "reason": merged[rid]["reason"]} for rid in reviews],
                  "invalid": invalid_for_report}
        Path(args.report).write_text(json.dumps(report, indent=2) + "\n",
                                     encoding="utf-8")
    for line in sorted(out):
        print(line)
    for line in review_lines:
        print(line)
    for line in notes:
        print(line)
    # `out` holds only problem lines (FAIL verdicts, invalid entries, file or
    # version problems); REVIEW listings live in `review_lines` and model
    # lines in `notes`, neither of which fails the gate.
    _baklog(root, "3.7 verdict-check", "verdict-check", "fail" if out else "pass", "\n".join(sorted(out)) or "no violations")
    return 1 if out else 0


if __name__ == "__main__":
    raise SystemExit(main())

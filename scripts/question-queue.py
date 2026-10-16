#!/usr/bin/env python3
"""File question queue: ask, answer, expire, list.

Owns <root>/questions/queue.md and <root>/questions/answers/<QID>.md (never
under .planning/). A timeout marks a question EXPIRED, never ANSWERED; only
the answer subcommand writes an answers file, and only it flips OPEN to
ANSWERED. Claude Code keeps AskUserQuestion; this queue replaces chat on DSH
only.
"""
import argparse
import datetime
import os
import re
import sys
import tempfile
import time
from pathlib import Path

Q_RE = re.compile(r"^Q-([0-9]+)$")
HEAD_RE = re.compile(r"^## (Q-[0-9]+) \((OPEN|ANSWERED|EXPIRED)\)$")
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
STATUSES = ("OPEN", "ANSWERED", "EXPIRED")
LOCK_TIMEOUT = 5.0


def fail(msg, code=1):
    print(f"question-queue: error: {msg}", file=sys.stderr)
    return code


def paths(root):
    qdir = Path(root) / "questions"
    return qdir / "queue.md", qdir / "answers"


def today():
    return datetime.date.today().isoformat()


def parse_date(value):
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


class QueueLocked(Exception):
    pass


def lock_path(queue_path):
    return queue_path.parent / "queue.md.lock"


def acquire_lock(queue_path, timeout=LOCK_TIMEOUT):
    lock = lock_path(queue_path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise QueueLocked("queue is locked by another writer")
            time.sleep(0.02)
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))
        return lock
    raise AssertionError("unreachable")  # pragma: no cover


def release_lock(lock):
    try:
        os.unlink(str(lock))
    except OSError:
        pass


def load(queue_path):
    try:
        text = queue_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"cannot read queue: {exc}"
    entries = []
    current = None
    for line in text.splitlines():
        head = HEAD_RE.match(line.strip())
        if head:
            if current is not None:
                entries.append(current)
            current = {"id": head.group(1), "status": head.group(2),
                       "asked": "", "timeout": "", "text": ""}
            continue
        if current is None:
            continue
        for key in ("Asked", "Timeout", "Text"):
            if line.startswith(key + ":"):
                current[key.lower()] = line[len(key) + 1:].strip()
    if current is not None:
        entries.append(current)
    for entry in entries:
        if not Q_RE.match(entry["id"]) or entry["status"] not in STATUSES:
            return None, f"{entry['id']}: queue file unparsable"
        if not DATE_RE.match(entry["timeout"]) or not entry["text"]:
            return None, f"{entry['id']}: queue file unparsable"
    return entries, None


def save(queue_path, entries):
    lines = ["# Question queue", ""]
    for entry in entries:
        lines.append(f"## {entry['id']} ({entry['status']})")
        lines.append(f"Asked: {entry['asked']}")
        lines.append(f"Timeout: {entry['timeout']}")
        lines.append(f"Text: {entry['text']}")
        lines.append("")
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(queue_path.parent),
                               prefix="queue.md.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        os.replace(tmp, queue_path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def valid_date(value):
    return DATE_RE.match(value) is not None and parse_date(value) is not None


def next_qid(entries):
    best = 0
    for entry in entries:
        m = Q_RE.match(entry["id"])
        if m:
            best = max(best, int(m.group(1)))
    return f"Q-{best + 1:03d}"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="question-queue.py")
    ap.add_argument("--root", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_ask = sub.add_parser("ask")
    p_ask.add_argument("--text", required=True)
    p_ask.add_argument("--timeout", required=True)
    p_ask.add_argument("--id", default=None)
    p_answer = sub.add_parser("answer")
    p_answer.add_argument("--id", required=True)
    p_answer.add_argument("--text", required=True)
    p_expire = sub.add_parser("expire")
    p_expire.add_argument("--now", default=None)
    sub.add_parser("list")
    args = ap.parse_args(argv)
    queue_path, answers_dir = paths(args.root)
    if args.cmd == "list":
        if not queue_path.is_file():
            return fail("no question queue: ask first")
        entries, err = load(queue_path)
        if err is not None:
            return fail(err)
        for entry in entries:
            if parse_date(entry["timeout"]) is None:
                return fail(f"{entry['id']}: bad timeout "
                            f"{entry['timeout']!r} in queue file")
        for entry in entries:
            print(f"{entry['id']} {entry['status']} "
                  f"{entry['timeout']} {entry['text']}")
        return 0
    try:
        lock = acquire_lock(queue_path)
    except QueueLocked as exc:
        return fail(str(exc))
    try:
        return dispatch(args, queue_path, answers_dir)
    finally:
        release_lock(lock)


def dispatch(args, queue_path, answers_dir):
    if args.cmd == "ask":
        if not valid_date(args.timeout):
            return fail(f"bad timeout {args.timeout!r}: use YYYY-MM-DD", 2)
        if parse_date(args.timeout) < datetime.date.today():
            return fail(f"bad timeout {args.timeout!r}: already in the past", 2)
        if "\n" in args.text or "\r" in args.text:
            return fail("bad text: question must be a single line", 2)
        if queue_path.is_file():
            entries, err = load(queue_path)
            if err is not None:
                return fail(err)
        else:
            entries = []
        qid = args.id or next_qid(entries)
        if not Q_RE.match(qid):
            return fail(f"bad id {qid!r}: use Q-NNN", 2)
        if any(e["id"] == qid for e in entries):
            return fail(f"{qid}: question already asked")
        entries.append({"id": qid, "status": "OPEN", "asked": today(),
                        "timeout": args.timeout, "text": args.text.strip()})
        save(queue_path, entries)
        print(f"ASKED {qid}")
        return 0
    if args.cmd == "answer":
        if not Q_RE.match(args.id):
            return fail(f"bad id {args.id!r}: use Q-NNN", 2)
        if not queue_path.is_file():
            return fail("no question queue: ask first")
        entries, err = load(queue_path)
        if err is not None:
            return fail(err)
        entry = next((e for e in entries if e["id"] == args.id), None)
        if entry is None:
            return fail(f"{args.id}: unknown question")
        if entry["status"] == "ANSWERED":
            return fail(f"{args.id}: already ANSWERED")
        if entry["status"] == "EXPIRED":
            return fail(f"{args.id}: is EXPIRED; re-ask it as a new question")
        due = parse_date(entry["timeout"])
        if due is None:
            return fail(f"{args.id}: bad timeout {entry['timeout']!r} in queue file")
        if due < datetime.date.today():
            entry["status"] = "EXPIRED"
            save(queue_path, entries)
            return fail(f"{args.id}: is EXPIRED; re-ask it as a new question")
        answers_dir.mkdir(parents=True, exist_ok=True)
        (answers_dir / f"{args.id}.md").write_text(
            f"# {args.id} answer\n\nQuestion: {entry['text']}\n\n"
            f"Answer: {args.text.strip()}\n\nAnswered: {today()}\n",
            encoding="utf-8")
        entry["status"] = "ANSWERED"
        save(queue_path, entries)
        print(f"ANSWERED {args.id}")
        return 0
    if args.cmd == "expire":
        now = args.now or today()
        if not valid_date(now):
            return fail(f"bad date {now!r}: use YYYY-MM-DD", 2)
        if not queue_path.is_file():
            return fail("no question queue: ask first")
        entries, err = load(queue_path)
        if err is not None:
            return fail(err)
        for entry in entries:
            if parse_date(entry["timeout"]) is None:
                return fail(f"{entry['id']}: bad timeout "
                            f"{entry['timeout']!r} in queue file")
        changed = []
        for entry in entries:
            if entry["status"] == "OPEN" and entry["timeout"] < now:
                entry["status"] = "EXPIRED"
                changed.append(entry["id"])
        if changed:
            save(queue_path, entries)
            for qid in changed:
                print(f"EXPIRED {qid}")
        else:
            print("no questions expired")
        return 0
    if args.cmd == "list":
        if not queue_path.is_file():
            return fail("no question queue: ask first")
        entries, err = load(queue_path)
        if err is not None:
            return fail(err)
        for entry in entries:
            if parse_date(entry["timeout"]) is None:
                return fail(f"{entry['id']}: bad timeout "
                            f"{entry['timeout']!r} in queue file")
        for entry in entries:
            print(f"{entry['id']} {entry['status']} "
                  f"{entry['timeout']} {entry['text']}")
        return 0
    return fail("unknown command", 2)


if __name__ == "__main__":
    raise SystemExit(main())

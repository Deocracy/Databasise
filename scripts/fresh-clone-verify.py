#!/usr/bin/env python3
"""Clone the repo at a pinned commit into a temp dir and run one command there.

It never reads the ledger and never reads any check_cmd: the caller passes
the command with --cmd.
"""
import argparse
import os
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(prog="fresh-clone-verify.py")
    ap.add_argument("--repo", required=True,
                    help="local path or URL to clone")
    ap.add_argument("--commit", required=True,
                    help="commit sha, branch or tag to check out")
    ap.add_argument("--cmd", required=True,
                    help="shell command run with sh -c inside the clone")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()
    work = Path(tempfile.mkdtemp(prefix="fresh-clone-verify-"))
    clone = work / "clone"

    def run_git(*args):
        try:
            return subprocess.run(["git", *args],
                                  capture_output=True, text=True)
        except OSError as exc:
            print(f"fresh-clone-verify: cannot run git: {exc}")
            raise SystemExit(1)

    def last_line(stderr):
        lines = [ln for ln in stderr.splitlines() if ln.strip()]
        return lines[-1] if lines else "no detail"

    try:
        hit = run_git("clone", "--quiet", args.repo, str(clone))
        if hit.returncode != 0:
            print("fresh-clone-verify: git clone failed")
            print(f"fresh-clone-verify: {last_line(hit.stderr)}")
            return 1
        hit = run_git("-C", str(clone), "checkout", "--quiet", args.commit)
        if hit.returncode != 0:
            print(f"fresh-clone-verify: git checkout {args.commit} failed")
            print(f"fresh-clone-verify: {last_line(hit.stderr)}")
            return 1
        proc = None
        try:
            proc = subprocess.Popen(["sh", "-c", args.cmd], cwd=str(clone),
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True, start_new_session=True)
            try:
                out, _ = proc.communicate(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    pass
                proc.wait()
                print("fresh-clone-verify: command timed out")
                return 1
        except OSError as exc:
            print(f"fresh-clone-verify: cannot run command: {exc}")
            return 1
        if proc is None:
            print("fresh-clone-verify: cannot run command: no process")
            return 1
        hit = proc
        if out:
            print(out, end="")
        if hit.returncode != 0:
            print(f"fresh-clone-verify: command failed with exit {hit.returncode}")
            return 1
        print("fresh-clone-verify: ok")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Install worktree-local gates: lefthook hooks plus the lock exclude."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

LOCK_LINE = ".worktree-lock"


def kit_root():
    return Path(__file__).resolve().parents[2]


def script_dir():
    return Path(__file__).resolve().parent


def find_source(root, rel):
    for cand in (Path(root) / rel, kit_root() / rel):
        if cand.is_file():
            return cand
    return None


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd),
                          capture_output=True, text=True, timeout=30)


def toplevel(root):
    try:
        proc = git(["rev-parse", "--show-toplevel"], root)
    except (OSError, subprocess.SubprocessError):
        return Path(root)
    if proc.returncode != 0:
        return Path(root)
    top = proc.stdout.strip()
    return Path(top) if top else Path(root)


def ensure_copy(src, dest):
    if dest.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dest)
    return True


def exclude_path(top):
    try:
        proc = git(["rev-parse", "--git-path", "info/exclude"], top)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    raw = proc.stdout.strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path(top) / path
    return path


def ensure_excluded(top):
    path = exclude_path(top)
    if path is None:
        print("install-worktree: cannot locate git exclude file",
              file=sys.stderr)
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = path.read_text(encoding="utf-8") if path.is_file() else ""
    wanted = {LOCK_LINE, LOCK_LINE + ".tmp"}
    present = {line.strip() for line in raw.splitlines()}
    if wanted <= present:
        return False
    with path.open("a", encoding="utf-8") as fh:
        if raw and not raw.endswith("\n"):
            fh.write("\n")
        for line in sorted(wanted - present):
            fh.write(line + "\n")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    top = toplevel(args.root)
    if not top.is_dir():
        print(f"install-worktree: cannot find worktree {args.root}",
              file=sys.stderr)
        return 1
    dest_cfg = Path(top) / "lefthook.yml"
    dest_checker = Path(top) / "scripts" / "check-commit-msg.py"
    template = checker = None
    if not dest_cfg.is_file():
        for cand in (Path(args.root) / "core/templates/lefthook.yml",
                     kit_root() / "core/templates/lefthook.yml"):
            if cand.is_file():
                template = cand
                break
        if template is None:
            print("install-worktree: core/templates/lefthook.yml not found; "
                  "copy core/templates/lefthook.yml to the worktree root",
                  file=sys.stderr)
            return 1
    if not dest_checker.is_file():
        for cand in (script_dir() / "check-commit-msg.py",
                     Path(args.root) / "core/scripts/check-commit-msg.py",
                     kit_root() / "core/scripts/check-commit-msg.py"):
            if cand.is_file() and cand.parent != dest_checker.parent:
                checker = cand
                break
        if checker is None:
            print("install-worktree: core/scripts/check-commit-msg.py "
                  "not found", file=sys.stderr)
            return 1
    copied_cfg = ensure_copy(template, dest_cfg) if template else False
    copied_script = ensure_copy(
        checker, dest_checker) if checker else False
    excluded = ensure_excluded(top)
    if shutil.which("lefthook") is None:
        print("install-worktree: lefthook is not installed; "
              "run the Phase 1 install first", file=sys.stderr)
        return 1
    try:
        proc = subprocess.run(["lefthook", "install"], cwd=str(top),
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"install-worktree: lefthook install failed: {exc}",
              file=sys.stderr)
        return 1
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        print(detail or "install-worktree: lefthook install failed",
              file=sys.stderr)
        return 1
    print(f"install-worktree: worktree {top}")
    print("install-worktree: lefthook.yml "
          f"{'copied' if copied_cfg else 'already present'}")
    print("install-worktree: scripts/check-commit-msg.py "
          f"{'copied' if copied_script else 'already present'}")
    print("install-worktree: lefthook hooks installed")
    print(f"install-worktree: {LOCK_LINE} "
          f"{'added to' if excluded else 'already in'} git exclude")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

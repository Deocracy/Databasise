#!/usr/bin/env python3
"""Proof tool: merge a commit onto a ref and record one check-run per ID."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(msg):
    print(f"prove-on-merge: error: {msg}", file=sys.stderr)
    return 1


def sh(root, *args, timeout=30):
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, timeout=timeout)


def lock_path(root):
    return Path(root) / ".bak" / "prove-on-merge.lock"


def read_lock(root):
    try:
        return json.loads(lock_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_lock(root, record):
    path = lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    ignore = path.parent / ".gitignore"
    try:
        if not ignore.exists():
            ignore.write_text("*\n", encoding="utf-8")
    except OSError:
        pass
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def clear_lock(root):
    try:
        lock_path(root).unlink()
    except OSError:
        pass


def _rmtree(path):
    """Remove a tree whose ledger files are read-only (0o444)."""
    import shutil as _shutil

    def _chmod(p):
        try:
            os.chmod(p, 0o644)
        except OSError:
            pass

    def _onexc(func, p, _exc):
        _chmod(p)
        func(p)

    try:
        _shutil.rmtree(path, onexc=_onexc)
    except TypeError:  # Python < 3.12: onerror instead of onexc
        _shutil.rmtree(path, onerror=lambda f, p, e: (_chmod(p), f(p)))


def _pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _names_test(text, path, node):
    """phase-gate's counting rule, loaded from the kit beside this tool (M5).

    Fail closed: when the rule cannot be loaded, the check-fail is skipped
    rather than replayed on a substring guess."""
    import importlib.util as _ilu
    try:
        _spec = _ilu.spec_from_file_location(
            "_prove_phase_gate",
            str(Path(__file__).resolve().parent / "phase-gate.py"))
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        return bool(_mod.names_test(text, path, node))
    except Exception:
        return False


def proof_copy(root):
    """PB-R5: the ledger copy an --in-place run records into."""
    return Path(root) / ".bak" / "prove-ledger"


def import_runs(root, kit):
    """PB-R5: append the runs recorded in the ledger copy to the ledger, once the
    checkout is back on its starting commit. True when no copy is left."""
    staging = Path(root) / ".bak" / "prove-ledger.importing"
    if not proof_copy(root).exists() and not staging.exists():
        return True
    p = subprocess.run([sys.executable, str(kit), "--root", str(root), "import-runs"],
                       capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        print(p.stderr, file=sys.stderr, end="")
        return False
    return True


def restore_leftover(root, record):
    """Repair a killed --in-place run without ever discarding user work (C2).

    Returns (note, error): note describes what was done for the caller's
    stderr line ("" when nothing needed doing), error is non-empty when the
    start must refuse instead.
    """
    if not isinstance(record, dict):
        return "", ""
    worktree = record.get("worktree", "")
    if worktree:
        try:
            subprocess.run(["git", "-C", str(root), "worktree", "remove",
                            "--force", worktree],
                           capture_output=True, timeout=60)
        except Exception:
            pass
        try:
            _rmtree(worktree)
        except OSError:
            pass
    if record.get("mode") != "in-place" or not record.get("head"):
        clear_lock(root)
        return "", ""
    head = record["head"]
    branch = record.get("branch", "")
    if _pid_alive(record.get("pid")):
        return "", ("the previous prove-on-merge run may still be alive "
                    f"(pid {record.get('pid')}); the owner stops it before re-running")
    if branch:
        tipped = sh(root, "rev-parse", "--verify", "--quiet", branch)
        tipped = tipped.stdout.strip() if tipped.returncode == 0 else ""
        if tipped != head:
            # The user kept working on the branch after the kill: only the
            # lock is cleared so import-runs can pick up the recorded runs.
            clear_lock(root)
            return ("leftover lock cleared without restoring the checkout "
                    "(the branch moved since the killed run)", "")
    cur = sh(root, "rev-parse", "HEAD")
    if cur.returncode != 0:
        return "", "git rev-parse HEAD failed"
    if cur.stdout.strip() == head:
        cur_branch = sh(root, "branch", "--show-current")
        cur_branch = cur_branch.stdout.strip() \
            if cur_branch.returncode == 0 else ""
        if not branch or cur_branch == branch:
            clear_lock(root)
            return "", ""
    detached = sh(root, "symbolic-ref", "-q", "HEAD")
    if detached.returncode == 0:
        # On a branch that is not the locked one: the user moved on.
        clear_lock(root)
        return ("leftover lock cleared without restoring the checkout "
                "(the checkout is on another branch)", "")
    dirty = sh(root, "status", "--porcelain")
    if dirty.returncode != 0:
        return "", "git status failed"
    if dirty.stdout.strip():
        return "", ("the checkout is dirty; the owner restores it "
                    "(for example `git checkout <branch>` and "
                    "`git reset --hard <head>`)")
    if branch:
        if sh(root, "checkout", branch).returncode != 0:
            return "", f"checkout of {branch} failed"
        cur2 = sh(root, "rev-parse", "HEAD")
        if cur2.returncode == 0 and cur2.stdout.strip() != head:
            if sh(root, "reset", "--hard", head).returncode != 0:
                return "", f"reset to {head[:8]} failed"
    else:
        if sh(root, "checkout", "--detach", head).returncode != 0:
            return "", f"checkout of {head[:8]} failed"
    clear_lock(root)
    return "restored leftover run from a killed process", ""


def latest_fail_cmd(root, rid):
    try:
        data = json.loads((Path(root) / "ledger" / "REQUIREMENTS.json").read_text(
            encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    rows = data.get("items") if isinstance(data, dict) else None
    ref = ""
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("id") == rid:
                ref = row.get("test_ref", "")
                break
    ref = ref if isinstance(ref, str) else ""
    path_part, _, node = ref.partition("::")
    path_part, node = path_part.strip(), node.strip()
    try:
        lines = (Path(root) / "ledger" / "history" / "log.jsonl").read_text(
            encoding="utf-8").splitlines()
    except OSError:
        return None
    cmd = None
    for line in lines:
        if not line.strip():
            continue
        try:
            op = json.loads(line)
        except ValueError:
            continue
        if isinstance(op, dict) and op.get("op") == "check-fail" \
                and op.get("id") == rid and isinstance(op.get("cmd"), str):
            if path_part and node and isinstance(op.get("output"), str) \
                    and not _names_test(op["output"], path_part, node):
                continue  # failed for another reason: not a counting run (M5)
            cmd = op["cmd"]
    return cmd


def main(argv=None):
    ap = argparse.ArgumentParser(prog="prove-on-merge.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--commit", required=True)
    ap.add_argument("--ids", required=True)
    ap.add_argument("--onto", default=None)
    ap.add_argument("--in-place", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    ids = [s.strip() for s in args.ids.split(",") if s.strip()]
    if not ids:
        return fail("prove-on-merge needs --ids ID[,ID...]")
    kit = Path(__file__).resolve().parent / "ledger-amend.py"
    left = read_lock(root)
    if left is not None:
        note, problem = restore_leftover(root, left)
        if problem:
            return fail(f"cannot restore the leftover run: {problem}")
        if note:
            print(note, file=sys.stderr)
    if not import_runs(root, kit):
        return fail("the runs left in .bak/prove-ledger could not be imported; "
                    "the owner deletes the copy "
                    "(for example `rm -rf .bak/prove-ledger`) and re-runs")
    dirty = sh(root, "status", "--porcelain")
    if dirty.returncode != 0:
        return fail("cannot run: git status failed")
    if dirty.stdout.strip():
        return fail("refusing to run on a dirty tree")
    head0 = sh(root, "rev-parse", "HEAD")
    if head0.returncode != 0:
        return fail("cannot run: git rev-parse HEAD failed")
    head0 = head0.stdout.strip()
    branch0 = sh(root, "branch", "--show-current")
    branch0 = branch0.stdout.strip() if branch0.returncode == 0 else ""
    onto = args.onto or head0
    rev = sh(root, "rev-parse", "--verify", "--quiet", f"{args.commit}^{{commit}}")
    if rev.returncode != 0 or not rev.stdout.strip():
        return fail(f"unknown commit {args.commit}")
    commit = rev.stdout.strip()
    rev2 = sh(root, "rev-parse", "--verify", "--quiet", f"{onto}^{{commit}}")
    if rev2.returncode != 0 or not rev2.stdout.strip():
        return fail(f"unknown onto ref {onto}")
    onto_sha = rev2.stdout.strip()
    cmds = {}
    for rid in ids:
        cmd = latest_fail_cmd(root, rid)
        if not cmd:
            return fail(f"{rid}: prove-on-merge needs a recorded check-fail cmd to replay")
        cmds[rid] = cmd
    if args.in_place:
        write_lock(root, {"mode": "in-place", "head": head0, "branch": branch0,
                          "commit": commit, "onto": onto_sha, "pid": os.getpid()})
        rc = 1
        try:
            # PB-R5: restoring the checkout resets its ledger/, so the runs go to
            # a copy under .bak/ (git-ignored) and import-runs appends them after.
            # The copy is built in a temp dir and moved into place, so a kill
            # cannot leave a half-written copy behind (M2).
            staged = Path(tempfile.mkdtemp(prefix="prove-ledger-",
                                           dir=str(Path(root) / ".bak")))
            try:
                shutil.copytree(root / "ledger", staged / "ledger")
                if proof_copy(root).exists():
                    _rmtree(proof_copy(root))
                os.replace(staged, proof_copy(root))
            finally:
                if staged.exists():
                    try:
                        _rmtree(staged)
                    except OSError:
                        pass
            # Freeze the recorder before the checkout moves: the proven commit
            # must not supply the code that records its own proof (I2).
            snap = Path(tempfile.mkdtemp(prefix="prove-kit-",
                                         dir=str(Path(root) / ".bak")))
            try:
                snap_kit = snap / "ledger-amend.py"
                shutil.copyfile(kit, snap_kit)
                for extra in ("phase-gate.py",):
                    src = Path(kit).parent / extra
                    if src.is_file():
                        shutil.copyfile(src, snap / extra)
                if sh(root, "checkout", "--detach", onto_sha).returncode != 0:
                    return fail("checkout of --onto failed")
                mg = sh(root, "merge", "--no-edit", commit, timeout=120)
                if mg.returncode != 0:
                    sh(root, "merge", "--abort")
                    return fail(f"merge of {commit[:8]} failed")
                rc = 0
                for rid in ids:
                    p = subprocess.run(
                        [sys.executable, str(snap_kit),
                         "--root", str(proof_copy(root)),
                         "record-run", "--id", rid, "--cmd", cmds[rid],
                         "--cwd", str(root)],
                        capture_output=True, text=True, timeout=600)
                    if p.returncode != 0:
                        print(p.stderr, file=sys.stderr)
                        rc = 1
            finally:
                try:
                    _rmtree(snap)
                except OSError:
                    pass
        finally:
            try:
                # I1: the detach itself moves the ref, so compare branches.
                cur_branch = sh(root, "branch", "--show-current")
                cur_branch = cur_branch.stdout.strip() \
                    if cur_branch.returncode == 0 else ""
                if cur_branch != branch0:
                    if branch0:
                        sh(root, "checkout", "-f", branch0)
                    else:
                        sh(root, "checkout", "--detach", head0)
                cur = sh(root, "rev-parse", "HEAD")
                if branch0 and cur.returncode == 0 \
                        and cur.stdout.strip() != head0:
                    sh(root, "reset", "--hard", head0)
            finally:
                # Import only onto the starting commit; otherwise the lock stays,
                # and the next start restores the ref and imports.
                if sh(root, "rev-parse", "HEAD").stdout.strip() == head0 \
                        and import_runs(root, kit):
                    clear_lock(root)
                else:
                    rc = 1
        return rc
    tmp = tempfile.mkdtemp(prefix="prove-merge-")
    write_lock(root, {"mode": "worktree", "head": head0, "branch": branch0,
                      "commit": commit, "onto": onto_sha, "pid": os.getpid(),
                      "worktree": tmp})
    try:
        _rmtree(tmp)
        add = subprocess.run(["git", "-C", str(root), "worktree", "add",
                              "--detach", tmp, onto_sha],
                             capture_output=True, text=True, timeout=120)
        if add.returncode != 0:
            return fail(f"worktree add failed: {add.stderr.strip()}")
        mg = subprocess.run(["git", "-C", tmp, "merge", "--no-edit", commit],
                            capture_output=True, text=True, timeout=120)
        if mg.returncode != 0:
            subprocess.run(["git", "-C", tmp, "merge", "--abort"],
                           capture_output=True, timeout=60)
            return fail(f"merge of {commit[:8]} failed")
        rc = 0
        for rid in ids:
            p = subprocess.run(
                [sys.executable, str(kit), "--root", str(root),
                 "record-run", "--id", rid, "--cmd", cmds[rid],
                 "--cwd", tmp],
                capture_output=True, text=True, timeout=600)
            if p.returncode != 0:
                print(p.stderr, file=sys.stderr)
                rc = 1
        return rc
    finally:
        try:
            subprocess.run(["git", "-C", str(root), "worktree", "remove",
                            "--force", tmp],
                           capture_output=True, timeout=60)
        except Exception:
            pass
        try:
            _rmtree(tmp)
        except OSError:
            pass
        clear_lock(root)


if __name__ == "__main__":
    raise SystemExit(main())

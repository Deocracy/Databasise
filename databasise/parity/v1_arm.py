"""The harness-side driver for the original (pre-decomposition) LightRAG arm (03-07-PLAN.md Task 1).

Launches ``databasise/parity/v1_driver_script.py`` as a subprocess **under v1's own pinned
interpreter** (``v1/.venv/bin/python``, 03-02-PLAN.md), never imports it — the driver script lives
under ``databasise/parity/`` but runs in v1's own Python environment, and
``databasise/tools/check_import_boundary.py`` forbids any import of ``v1``/``lightrag`` under
``databasise/`` regardless (D-14).

This module instruments the arm **from the outside**: wall-clock duration, subprocess exit status,
and captured stderr on failure — nothing more. It does not construct a RIG §TR.1-shaped run record
and does not fabricate a per-node trace for this arm: D-05 states the two arms' traces are
asymmetric (the decomposed arm produces a full run record; this one does not), and
:class:`V1ArmResult` carries an explicit ``instrumentation`` field naming itself
``"harness-external"`` so that asymmetry travels with the data itself, not only in prose wherever
this arm's numbers are later read.

A missing parity env file is a ``MissingParityEnvError`` (``clients.builder.load_env_file``), raised
before the interpreter check and before anything launches. IN-01's "read a missing file as empty" is
reversed here only; the corpus adapter (``foreign/v1_corpus_adapter.py``) keeps its behaviour
(LRAG-06). The arm needs a source checkout with ``v1/.venv`` (D-01). ``main`` is estimate-only
without ``--spend`` and prints named refusals as one line through ``databasise.cli.refuse`` (D-03).

A non-zero subprocess exit is a refusal (:class:`V1ArmSubprocessError`, carrying the captured
stderr) — never an empty result. A missing v1 interpreter raises :class:`MissingV1InterpreterError`
naming the expected path and pointing at ``v1/README-PARITY.md``'s recreate commands.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from databasise import cli
from databasise.clients.builder import load_env_file

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_V1_INTERPRETER = _REPO_ROOT / "v1" / ".venv" / "bin" / "python"
DEFAULT_V1_DRIVER_SCRIPT = Path(__file__).resolve().parent / "v1_driver_script.py"
DEFAULT_V1_ENV_PARITY = _REPO_ROOT / "v1" / ".env.parity"
DEFAULT_V1_WORKING_DIR = _REPO_ROOT / "v1" / ".parity_working_dir"

# D-05: no RIG §TR.1-shaped run record exists for this arm — this string is the marker that
# carries that asymmetry in the data itself, not only in prose.
_INSTRUMENTATION_MARKER = "harness-external"


class MissingV1InterpreterError(RuntimeError):
    """Raised when the pinned ``v1/`` interpreter does not exist — named rather than a bare
    ``FileNotFoundError``, per this codebase's refusals-over-silent-fallbacks house style.
    """

    def __init__(self, path: Path):
        self.path = path
        super().__init__(
            f"v1/ interpreter not found at {path} — see v1/README-PARITY.md's "
            "'Recreating the environment' section to recreate it"
        )


class V1ArmSubprocessError(RuntimeError):
    """A non-zero exit from the v1 driver subprocess — carries the captured stderr rather than
    returning an empty result (this module's own refusal-over-silent-empty-result rule).
    """

    def __init__(self, returncode: int, stderr: str):
        self.returncode = returncode
        self.stderr = stderr  # the full capture; the message names only the failure line
        super().__init__(f"v1 driver subprocess exited {returncode}: {_failure_line(stderr)}")


def _failure_line(stderr: str) -> str:
    """The driver prints its named failure (or a traceback's exception) last, after v1's INFO log
    lines, so the message is the last line that is not a v1 log line."""
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    if not lines:
        return "(no stderr)"
    for line in reversed(lines):
        if not line.startswith(("INFO:", "WARNING:", "DEBUG:")):
            return line
    return lines[-1]


@dataclass(frozen=True)
class V1ArmResult:
    """The original arm's result. ``instrumentation`` is always ``"harness-external"`` — see
    module docstring's D-05 note.
    """

    chunk_ids: tuple[str, ...]
    entity_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]
    answer: str
    hl_keywords_used: tuple[str, ...] | None
    ll_keywords_used: tuple[str, ...] | None
    wall_clock_seconds: float
    instrumentation: str = _INSTRUMENTATION_MARKER

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_ids": list(self.chunk_ids),
            "entity_ids": list(self.entity_ids),
            "relation_ids": list(self.relation_ids),
            "answer": self.answer,
            "hl_keywords_used": None if self.hl_keywords_used is None else list(self.hl_keywords_used),
            "ll_keywords_used": None if self.ll_keywords_used is None else list(self.ll_keywords_used),
            "wall_clock_seconds": self.wall_clock_seconds,
            "instrumentation": self.instrumentation,
        }


def run_v1_arm(
    mode: str,
    query: str,
    *,
    hl_keywords: list[str] | None = None,
    ll_keywords: list[str] | None = None,
    interpreter: Path | None = None,
    driver_script: Path | None = None,
    env_path: Path | None = None,
    working_dir: Path | None = None,
    timeout: float | None = None,
) -> V1ArmResult:
    """Launch the driver script under v1's pinned interpreter with one job JSON on stdin, and
    parse its stdout JSON result. Blocking (uses ``subprocess.run``) — a caller on an event loop
    should run this via ``asyncio.to_thread``.

    ``interpreter``/``driver_script``/``env_path``/``working_dir`` are override points for tests.
    """
    # First: a missing parity env file is MissingParityEnvError before the interpreter check and
    # before anything launches, never an empty env that lets v1 fall back to v1/.env (D-08).
    parity_env = load_env_file(env_path or DEFAULT_V1_ENV_PARITY)
    interpreter = interpreter or DEFAULT_V1_INTERPRETER
    if not interpreter.exists():
        raise MissingV1InterpreterError(interpreter)
    driver_script = driver_script or DEFAULT_V1_DRIVER_SCRIPT

    env = dict(os.environ)
    env.update(parity_env)
    env.setdefault("ENABLE_LLM_CACHE", "false")

    job = {
        "mode": mode,
        "query": query,
        "hl_keywords": list(hl_keywords or []),
        "ll_keywords": list(ll_keywords or []),
        "working_dir": str(working_dir or DEFAULT_V1_WORKING_DIR),
    }

    start = time.monotonic()
    proc = subprocess.run(
        [str(interpreter), str(driver_script)],
        input=json.dumps(job),
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT / "v1"),
        env=env,
        timeout=timeout,
    )
    wall_clock = time.monotonic() - start

    if proc.returncode != 0:
        raise V1ArmSubprocessError(proc.returncode, proc.stderr)

    payload = json.loads(proc.stdout)
    return V1ArmResult(
        chunk_ids=tuple(payload["chunk_ids"]),
        entity_ids=tuple(payload["entity_ids"]),
        relation_ids=tuple(payload["relation_ids"]),
        answer=payload["answer"],
        hl_keywords_used=None if payload["hl_keywords_used"] is None else tuple(payload["hl_keywords_used"]),
        ll_keywords_used=None if payload["ll_keywords_used"] is None else tuple(payload["ll_keywords_used"]),
        wall_clock_seconds=wall_clock,
    )


def main(argv: list[str] | None = None) -> int:
    """``uv run python -m databasise.parity.v1_arm --mode naive --query "..."`` — prints the
    result as JSON, following the committed-and-re-runnable evidence style
    ``databasise/evidence/falsifier2.py`` establishes.
    """
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", required=True, choices=["naive", "bypass", "hybrid", "local", "global", "mix"]
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--hl-keyword", action="append", default=[])
    parser.add_argument("--ll-keyword", action="append", default=[])
    parser.add_argument("--spend", action="store_true", default=False)
    args = parser.parse_args(argv)

    if not args.spend:  # estimate-only: no env file read, nothing launched (D-04)
        print(f"v1 mode: {args.mode}")
        print(f"query: {args.query}")
        print("one v1 subprocess run")
        print("mode: estimate-only")
        return cli.EXIT_OK

    try:
        result = run_v1_arm(
            args.mode, args.query, hl_keywords=args.hl_keyword, ll_keywords=args.ll_keyword
        )
    except cli.offline_refusals(V1ArmSubprocessError, MissingV1InterpreterError) as exc:
        return cli.refuse(exc)

    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

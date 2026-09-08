"""``databasise.foreign`` — CONTRACT §17's foreign-part adapter layer: process lifecycle, the RPC
channel (JSON over stdin/stdout), health (a non-zero exit is a refusal). This is not
``databasise/parity/``: parity is Phase 3's read-only comparison harness between the decomposed and
original LightRAG arms; ``databasise/foreign/`` is the machine-side launcher for v1's own corpus-
side write operations (ingest today, delete/status in 05-03/05-04), and is shared by whichever
opaque Part needs to reach a foreign interpreter — a second engine (05-06) reuses this same launch
shape rather than a copy under ``parity/``.

``run_corpus_op`` mirrors ``databasise/parity/v1_arm.py``'s ``run_v1_arm`` launch shape exactly:
resolve the interpreter, build the job dict, ``subprocess.run(..., timeout=timeout)``, non-zero
exit is a hard refusal (never a partial/empty success), parse stdout JSON on success. All
caller-controlled data travels in the JSON job on stdin — nothing caller-controlled is ever
interpolated into argv or into a shell string.

Blocking (``subprocess.run``) — a caller on an event loop runs this via ``asyncio.to_thread``
(mirrors ``run_v1_arm``'s own docstring note).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_V1_INTERPRETER = _REPO_ROOT / "v1" / ".venv" / "bin" / "python"
DEFAULT_V1_DRIVER_SCRIPT = Path(__file__).resolve().parent / "v1_corpus_driver_script.py"
DEFAULT_V1_ENV_PARITY = _REPO_ROOT / "v1" / ".env.parity"
DEFAULT_V1_WORKING_DIR = _REPO_ROOT / "v1" / ".corpus_working_dir"

# 05-04-PLAN.md Task 1: a status read builds v1's facade and reads its doc-status store — it
# performs no extraction and calls no model, unlike an ingest (which may reach the LLM/embedder)
# or a delete (which may reach the LLM on a partial-rebuild path). This is why the seam's status
# methods (get_job_status/health/corpus_status/document_counts) are per-call, never polled in a
# tight loop: each call still pays a full facade construction against v1's own doc-status/graph
# storage backends, which is not free even though it makes no network call.
STATUS_WALL_CLOCK_CEILING_SECONDS = 60.0


class MissingV1InterpreterError(RuntimeError):
    """Raised when the pinned ``v1/`` interpreter does not exist — named rather than a bare
    ``FileNotFoundError``, per this codebase's refusals-over-silent-fallbacks house style. Re-
    exported by ``databasise.foreign`` (matches ``databasise.parity.v1_arm``'s own name).
    """

    def __init__(self, path: Path):
        self.path = path
        super().__init__(
            f"v1/ interpreter not found at {path} — see v1/README-PARITY.md's "
            "'Recreating the environment' section to recreate it"
        )


class CorpusOpSubprocessError(RuntimeError):
    """A non-zero exit from the v1 corpus driver subprocess — carries the captured stderr rather
    than returning an empty result (this module's own refusal-over-silent-empty-result rule)."""

    def __init__(self, returncode: int, stderr: str):
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"v1 corpus driver subprocess exited {returncode}: {stderr.strip()[:2000] or '(no stderr)'}"
        )


class CorpusOpTimeoutError(RuntimeError):
    """§8 condition 4's wall-clock-ceiling refusal: the corpus driver subprocess did not complete
    within ``timeout`` seconds — carries both the attempted ``op`` and the declared ``timeout``
    on named attributes."""

    def __init__(self, op: str, timeout: float):
        self.op = op
        self.timeout = timeout
        super().__init__(f"corpus op {op!r} exceeded its wall-clock ceiling of {timeout}s")


def _load_env_file(path: Path) -> dict[str, str]:
    """A minimal ``KEY=VALUE`` parser for the flat ``.env.parity`` shape — duplicated from
    ``databasise/parity/v1_arm.py``'s own ``_load_env_file``, not imported, per that module's own
    documented duplication rule (each caller's own dependency surface stays obvious rather than
    reaching into a sibling module's private helper for a ~15-line stdlib parser). Returns ``{}``
    for an absent file rather than raising.
    """
    if not path.exists():
        return {}
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        env[key.strip()] = value
    return env


def run_corpus_op(
    op: str,
    payload: dict[str, Any],
    *,
    timeout: float,
    interpreter: Path | None = None,
    driver_script: Path | None = None,
    env_path: Path | None = None,
    working_dir: Path | None = None,
) -> dict[str, Any]:
    """Launch ``databasise/foreign/v1_corpus_driver_script.py`` under v1's pinned interpreter with
    one job JSON on stdin (``{"op": op, "working_dir": ..., **payload}``), and parse its stdout
    JSON result. ``timeout`` is required, not optional — every call site declares §8 condition 4's
    wall-clock ceiling explicitly.

    ``interpreter``/``driver_script``/``env_path``/``working_dir`` are override points for tests.
    """
    interpreter = interpreter or DEFAULT_V1_INTERPRETER
    if not interpreter.exists():
        raise MissingV1InterpreterError(interpreter)
    driver_script = driver_script or DEFAULT_V1_DRIVER_SCRIPT

    env = dict(os.environ)
    env.update(_load_env_file(env_path or DEFAULT_V1_ENV_PARITY))
    env.setdefault("ENABLE_LLM_CACHE", "false")

    job: dict[str, Any] = {
        "op": op,
        "working_dir": str(working_dir or DEFAULT_V1_WORKING_DIR),
        **payload,
    }

    try:
        proc = subprocess.run(
            [str(interpreter), str(driver_script)],
            input=json.dumps(job),
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT / "v1"),
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise CorpusOpTimeoutError(op, timeout) from exc

    if proc.returncode != 0:
        raise CorpusOpSubprocessError(proc.returncode, proc.stderr)

    return json.loads(proc.stdout)


__all__ = [
    "run_corpus_op",
    "CorpusOpTimeoutError",
    "CorpusOpSubprocessError",
    "MissingV1InterpreterError",
    "DEFAULT_V1_INTERPRETER",
    "DEFAULT_V1_DRIVER_SCRIPT",
    "DEFAULT_V1_ENV_PARITY",
    "DEFAULT_V1_WORKING_DIR",
    "STATUS_WALL_CLOCK_CEILING_SECONDS",
]

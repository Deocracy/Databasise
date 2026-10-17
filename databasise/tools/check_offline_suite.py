"""RUN-12's phase gate: the offline suite is green under both pytest invocation styles.

Run from anywhere::

    databasise/.venv/bin/python databasise/tools/check_offline_suite.py

It runs ``pytest -q -rs`` and then ``python -m pytest -q -rs`` from ``databasise/``, one after the
other (never in parallel: both styles use the same v1 working directory and stub files). The
script passes no marker expression of its own; the default run's ``addopts`` already deselects the
tests marked as needing a real endpoint, and the gate only checks that the summary says so.

Exit codes: 0 when both styles exit 0, neither skips a test with a reason that contradicts the
environment (``found=False``, or "the 'mcp' extra is not installed", while ``mcp`` is installed),
and the default run reports deselected tests; 1 otherwise.
"""

from __future__ import annotations

import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_NOT_INSTALLED_MARKERS = (
    "found=False",
    "'mcp' extra is not installed",
    "`mcp` extra is not installed",
)


def parse_skip_lines(output: str) -> list[str]:
    """Lines of ``pytest -rs`` output that start with ``SKIPPED ``."""
    return [line for line in output.splitlines() if line.startswith("SKIPPED ")]


def contradictory_skips(skip_lines: list[str], mcp_installed: bool) -> list[str]:
    """Skip lines whose reason says ``mcp`` is missing while it is installed."""
    if not mcp_installed:
        return []
    return [line for line in skip_lines if any(m in line for m in _NOT_INSTALLED_MARKERS)]


def summary_line(output: str) -> str:
    """The final ``N passed ...`` line of a pytest run, or ``""`` when there is none."""
    for line in reversed(output.splitlines()):
        if " passed" in line or " failed" in line or " error" in line:
            return line.strip()
    return ""


def has_deselected(summary: str) -> bool:
    return "deselected" in summary


def mcp_is_installed() -> bool:
    try:
        version("mcp")
    except PackageNotFoundError:
        return False
    return True


def run_style(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout + result.stderr


def main() -> int:
    project = Path(__file__).resolve().parents[1]
    venv = project / ".venv" / "bin"
    styles = (
        [str(venv / "pytest"), "-q", "-rs"],
        [str(venv / "python"), "-m", "pytest", "-q", "-rs"],
    )
    labels = ("pytest -q -rs", "python -m pytest -q -rs")
    mcp_installed = mcp_is_installed()
    ok = True
    for index, cmd in enumerate(styles):
        code, output = run_style(cmd, project)
        summary = summary_line(output)
        print(f"{labels[index]}: {summary}")
        contradictions = contradictory_skips(parse_skip_lines(output), mcp_installed)
        for line in contradictions:
            print(f"  contradictory skip: {line}")
        if code != 0 or contradictions:
            ok = False
        if index == 0 and not has_deselected(summary):
            print("  the default run reports no deselected tests")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

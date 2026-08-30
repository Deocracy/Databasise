"""Shared pytest fixtures for the databasise/ test harness.

Every test written in every later plan of this phase depends on these three fixtures:

- ``store_root``: a per-test directory every store adapter writes under, so D-07's
  one-directory-per-namespace layout is inspectable after a test runs.
- ``rig_trace_schema``: the parsed RIG run-record schema, loaded once per test.
- ``assert_valid_trace``: validates a run-record dict against that schema, raising
  with the full JSON-Schema error path on failure.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest
from jsonschema import Draft7Validator


def _repository_root() -> Path:
    """Walk up from this file to find the repository root (the dir containing docs/)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "docs" / "system-model").is_dir():
            return parent
    raise RuntimeError(
        "could not locate repository root (docs/system-model/) walking up from "
        f"{__file__}"
    )


@pytest.fixture
def store_root(tmp_path: Path) -> Path:
    """A tmp_path-derived directory every store adapter writes under during a test."""
    root = tmp_path / "store_root"
    root.mkdir()
    return root


@pytest.fixture(scope="session")
def rig_trace_schema() -> dict[str, Any]:
    """Load and return the parsed RIG run-record (trace) schema."""
    schema_path = _repository_root() / "docs" / "system-model" / "rig-trace.schema.json"
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def assert_valid_trace(
    rig_trace_schema: dict[str, Any],
) -> Callable[[dict[str, Any]], None]:
    """Return a callable that validates a run-record dict against rig_trace_schema."""

    def _assert_valid_trace(record: dict[str, Any]) -> None:
        validator = Draft7Validator(rig_trace_schema)
        errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
        if errors:
            messages = "\n".join(
                f"  - {'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
                for e in errors
            )
            raise AssertionError(
                f"run-record failed rig-trace.schema.json validation:\n{messages}"
            )

    return _assert_valid_trace

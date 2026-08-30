"""Smoke tests for the three shared fixtures in conftest.py.

Exists for two reasons: (1) conftest.py has real logic (repo-root walk, JSON-Schema
validation, error-path formatting) that deserves a runnable check; (2) a completely
empty ``tests/`` collects zero items, and pytest's own exit code for "no tests
collected" is 5, not 0 — which would fail this plan's own `--collect-only` verify
step. One real test satisfies both.
"""

from __future__ import annotations

from pathlib import Path


def test_store_root_is_an_existing_directory(store_root: Path) -> None:
    assert store_root.is_dir()


def test_rig_trace_schema_loads_expected_shape(rig_trace_schema: dict) -> None:
    assert rig_trace_schema["title"] == "RIG-02 run trace record"
    assert "nodes" in rig_trace_schema["required"]


def test_assert_valid_trace_raises_with_error_path_on_invalid_record(
    assert_valid_trace,
) -> None:
    try:
        assert_valid_trace({})
    except AssertionError as exc:
        assert "run_id" in str(exc)
    else:
        raise AssertionError("expected assert_valid_trace to raise on an empty record")

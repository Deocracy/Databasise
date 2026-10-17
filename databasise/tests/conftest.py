"""Shared pytest fixtures for the databasise/ test harness.

Every test written in every later plan of this phase depends on these three fixtures:

- ``store_root``: a per-test directory every store adapter writes under, so D-07's
  one-directory-per-namespace layout is inspectable after a test runs.
- ``rig_trace_schema``: the parsed RIG run-record schema, loaded once per test.
- ``assert_valid_trace``: validates a run-record dict against that schema, raising
  with the full JSON-Schema error path on failure.
"""

from __future__ import annotations

import ipaddress
import json
import socket
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


class NonLoopbackConnectionError(RuntimeError):
    """A test not marked ``live`` tried to connect to a non-loopback address (RUN-12)."""

    def __init__(self, address: Any, nodeid: str) -> None:
        self.address = address
        self.nodeid = nodeid
        super().__init__(
            f"{nodeid}: a non-live test tried to reach non-loopback address {address!r}; "
            "mark it live (owner-run, spends tokens) or give it a stub"
        )


def _is_local_host(host: Any) -> bool:
    if not isinstance(host, str):
        return False
    if host in ("", "localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return False
    ip = getattr(ip, "ipv4_mapped", None) or ip
    return ip.is_loopback or ip.is_unspecified


@pytest.fixture(autouse=True)
def _offline_unless_live(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make "offline" a checked claim: refuse non-loopback connects from tests not marked live.

    AF_UNIX and loopback/unspecified AF_INET/AF_INET6 addresses pass. Only this interpreter is
    guarded; subprocesses a test starts are separate interpreters and are not affected.
    """
    if request.node.get_closest_marker("live"):
        return
    nodeid = request.node.nodeid

    def _guarded(original: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self: socket.socket, address: Any) -> Any:
            if self.family in (socket.AF_INET, socket.AF_INET6) and not _is_local_host(
                address[0]
            ):
                raise NonLoopbackConnectionError(address, nodeid)
            return original(self, address)

        return wrapper

    monkeypatch.setattr(socket.socket, "connect", _guarded(socket.socket.connect))
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded(socket.socket.connect_ex))

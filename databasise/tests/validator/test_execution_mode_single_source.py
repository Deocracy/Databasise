"""WIRE-07 row tests: execution placement has one source, ``validator/execution_mode.py``, and the
validator carries no dead or stale item (D-18).

Every test imports only names that exist at the phase base and captures exceptions, so a failure
at the base is a plain ``AssertionError`` (Phase 13 fail-first rule).
"""

from __future__ import annotations

import inspect
import re

import pytest
from databasise.validator import blast_radius, depth, execution_mode, parse
from databasise.validator.execution_mode import (
    UnimplementedPlacementError,
    derive_execution_mode,
    host,
)


def test_depth_defines_no_placement_function():
    assert not hasattr(depth, "derive_execution_mode")


def test_parse_defines_no_unraised_validation_error():
    assert not hasattr(parse, "WiringValidationError")


@pytest.mark.parametrize("effect", ["calls_llm", "calls_embedding", "calls_rerank"])
def test_machine_client_callers_are_in_process(effect):
    assert derive_execution_mode([effect], "stage") == "in-process"
    assert derive_execution_mode([effect, "fs"], "stage") == "confined-unit"
    assert derive_execution_mode(["fs", effect], "stage") == "confined-unit"


def test_an_empty_effect_list_derives_in_process():
    assert derive_execution_mode([], "stage") == "in-process"


def _host_message(placement):
    try:
        host(placement)
    except Exception as exc:  # noqa: BLE001 - the test asserts on the message
        return str(exc)
    return ""


def test_no_placement_text_names_phase_1():
    texts = {
        "execution_mode.__doc__": execution_mode.__doc__ or "",
        "UnimplementedPlacementError.__doc__": UnimplementedPlacementError.__doc__ or "",
    }
    for placement in ("subprocess", "confined-unit", "long-lived-service"):
        texts[f"host({placement!r})"] = _host_message(placement)

    assert all(texts.values()), texts
    assert [name for name, text in texts.items() if "Phase 1" in text] == []


def test_parsed_wiring_docstring_does_not_claim_read_only():
    doc = parse.ParsedWiring.__doc__ or ""

    assert "read-only" not in doc
    assert "mutable" in doc


def test_blast_radius_reads_artifact_scope_directly():
    source = inspect.getsource(blast_radius)

    assert re.search(r"getattr\([^)]*artifact_scope", source) is None

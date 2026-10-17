"""09-09-PLAN.md Task 2 (SEAM-16, docstring and behaviour half; 09-10 adds the dead-code and
``python -O`` checks): the seam's docstrings say what the code does. Each source file is read as
UTF-8 text and checked with exact substrings, so a stale phrase cannot hide behind a different
encoding; phrases that wrap across a source line are checked on whitespace-collapsed text.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

import databasise.mcp.tools as tools_module
import databasise.seam.corpus as corpus_module
import databasise.seam.redact as redact_module
import databasise.seam.refusals as refusals_module
import databasise.seam.rest as rest_module
import databasise.seam.tokens as tokens_module
from databasise.seam.rest import PromoteRequest, create_app
from databasise.tests.seam.test_rest_transport import _seed_trace
from fastapi.testclient import TestClient


def _source(module) -> str:
    """The module source as UTF-8 text with whitespace collapsed to single spaces."""
    return " ".join(Path(module.__file__).read_text(encoding="utf-8").split())


def _doc(obj) -> str:
    return " ".join((obj.__doc__ or "").split())


# --------------------------------------------------------------------------------------------- #
# Behaviour: the verb contract the docstrings describe.
# --------------------------------------------------------------------------------------------- #


def _promote_body(store_root, verb):
    return {
        "alias": "doc-consistency-alias",
        "trace_ids": [_seed_trace(store_root, "naive")],
        "change_origin": "human_edit",
        "verb": verb,
    }


def test_promote_with_a_null_verb_is_a_fastapi_validation_error(store_root):
    client = TestClient(create_app(store_root=store_root, workspace="doc-consistency-null"))
    response = client.post("/promote", json=_promote_body(store_root, None))
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert "refusal_type" not in body


def test_promote_with_a_non_member_string_verb_is_an_unrecognised_verb_refusal(store_root):
    client = TestClient(create_app(store_root=store_root, workspace="doc-consistency-nope"))
    response = client.post("/promote", json=_promote_body(store_root, "nope"))
    assert response.status_code == 422
    assert response.json()["refusal_type"] == "UnrecognisedPromotionVerbError"


# --------------------------------------------------------------------------------------------- #
# Docstrings: stale phrases are gone, the corrected statements are present.
# --------------------------------------------------------------------------------------------- #


def test_rest_module_docstring_describes_the_single_handler_matched_through_the_mro():
    doc = _doc(rest_module)
    assert "enumerated at runtime" not in _source(rest_module)
    assert "MRO" in doc
    assert "non-string" in _doc(PromoteRequest)


def test_refusals_docstrings_match_the_verb_contract_and_the_unreachable_mutable_store_refusal():
    assert "a JSON body can deliver" not in _source(refusals_module)
    assert "non-string" in _doc(refusals_module.UnrecognisedPromotionVerbError)
    assert "unreachable" in _doc(refusals_module.MutableStoreComparisonExcludedError)


def test_mcp_promote_tool_args_docstring_matches_the_verb_contract():
    assert "_refusal_mapped" not in _source(tools_module)
    assert "non-string" in _doc(tools_module.PromoteToolArgs)


def test_tokens_docstring_names_the_three_opaque_parts():
    source = _source(tokens_module)
    for part in ("lightrag/full-ingest", "lightrag/full-delete", "codebase-memory-mcp"):
        assert part in source, part
    assert "no opaque node is registered" not in source


def test_corpus_module_no_longer_claims_server_minted_only_ids():
    assert "built only from the server-minted" not in _source(corpus_module)


# --------------------------------------------------------------------------------------------- #
# 09-10 (SEAM-16): the identity-leak gate is not switched off by `python -O`.
# --------------------------------------------------------------------------------------------- #


def _run_dash_o(code: str, tmp_path):
    """Run ``code`` under ``python -O`` in the project interpreter, in an empty cwd."""
    return subprocess.run(
        [sys.executable, "-O", "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_key_check_fires_under_python_dash_o(tmp_path):
    result = _run_dash_o(
        "from databasise.seam.redact import assert_no_forbidden_keys\n"
        "assert_no_forbidden_keys({'node-x': 1}, {'node-x'})\n",
        tmp_path,
    )
    assert result.returncode != 0
    assert "AssertionError" in result.stderr


def test_value_check_fires_under_python_dash_o(tmp_path):
    result = _run_dash_o(
        "from databasise.seam.redact import assert_no_forbidden_values\n"
        "assert_no_forbidden_values({'component': 'node-x'}, {'node-x'})\n",
        tmp_path,
    )
    assert result.returncode != 0
    assert "AssertionError" in result.stderr


def test_clean_envelope_with_an_empty_forbidden_set_passes_both_checks_under_python_dash_o(tmp_path):
    result = _run_dash_o(
        "from databasise.seam.redact import assert_no_forbidden_keys, assert_no_forbidden_values\n"
        "env = {'answer': 'node-x', 'evidence': []}\n"
        "assert_no_forbidden_keys(env, set())\n"
        "assert_no_forbidden_values(env, set())\n",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


def test_redact_docstring_says_it_is_a_test_time_gate():
    assert "test-time gate" in _doc(redact_module)

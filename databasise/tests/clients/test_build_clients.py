"""08-05-PLAN.md Task 3 (RUN-05, D-08): the shared client builder with optional rerank wiring.

Every phase-created name is imported inside the test that uses it, never at module top, so the file
collects on the pre-phase tree and each case fails inside its body (plan 08-10's fail-first run).
Constructing the clients makes no network call.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

REQUIRED = {
    "LLM_BINDING_HOST": "http://llm.stub-host-marker",
    "LLM_MODEL": "stub-llm-model-marker",
    "LLM_BINDING_API_KEY": "stub-llm-key-marker",
    "EMBEDDING_BINDING_HOST": "http://embed.stub-host-marker",
    "EMBEDDING_MODEL": "stub-embed-model-marker",
    "EMBEDDING_BINDING_API_KEY": "stub-embed-key-marker",
}
RERANK = {
    "RERANK_BINDING": "cohere",
    "RERANK_BINDING_HOST": "http://rerank.stub-host-marker/v2/rerank",
    "RERANK_MODEL": "stub-rerank-model-marker",
    "RERANK_BINDING_API_KEY": "stub-rerank-key-marker",
}


def test_six_keys_build_exactly_llm_and_embedding():
    from databasise.clients.builder import build_clients

    assert set(build_clients(dict(REQUIRED))) == {"llm", "embedding"}


def test_two_missing_keys_are_both_named():
    from databasise.clients.builder import MissingParityEnvKeyError, build_clients

    env = {k: v for k, v in REQUIRED.items() if k not in ("LLM_MODEL", "EMBEDDING_MODEL")}

    with pytest.raises(MissingParityEnvKeyError) as exc_info:
        build_clients(env)

    assert exc_info.value.missing_keys == ["LLM_MODEL", "EMBEDDING_MODEL"]


def test_run_arm_uses_the_shared_builder_not_a_private_copy():
    from databasise.clients import builder
    from databasise.parity import run_arm

    assert run_arm._build_clients is builder.build_clients
    assert inspect.getsourcefile(run_arm._build_clients).endswith("clients/builder.py")


async def test_live_rerank_with_builder_clients_raises_client_not_wired_naming_rerank():
    from databasise.clients import CapabilityScopedClients, ClientNotWiredError
    from databasise.clients.builder import build_clients
    from databasise.parts.schema import NodeContext
    from databasise.parts_core.lightrag.rerank import _rerank_body
    from databasise.runner.scheduler import _ScopedClientsView

    effects = ["calls_rerank"]
    view = _ScopedClientsView(CapabilityScopedClients(build_clients(dict(REQUIRED)), effects), effects)
    ctx = NodeContext(
        node_id="rerank",
        config={"live_rerank": True, "query": "q"},
        inputs={"heading-backfill": {"items": [{"content": "a"}]}},
        stores={},
        clients=view,
    )

    with pytest.raises(ClientNotWiredError) as exc_info:
        await _rerank_body(ctx)

    assert exc_info.value.client_key == "rerank"


@pytest.mark.parametrize("binding", ["cohere", "jina", "aliyun"])
def test_a_complete_rerank_set_adds_a_rerank_client(binding):
    from databasise.clients.builder import build_clients
    from databasise.clients.rerank import HttpRerankClient

    clients = build_clients({**REQUIRED, **RERANK, "RERANK_BINDING": binding})

    assert set(clients) == {"llm", "embedding", "rerank"}
    assert isinstance(clients["rerank"], HttpRerankClient)
    assert clients["rerank"]._binding == binding
    assert clients["rerank"]._url == RERANK["RERANK_BINDING_HOST"]


@pytest.mark.parametrize(
    "present",
    [
        ["RERANK_BINDING"],
        ["RERANK_BINDING_HOST"],
        ["RERANK_BINDING", "RERANK_BINDING_HOST"],
        ["RERANK_BINDING_HOST", "RERANK_MODEL", "RERANK_BINDING_API_KEY"],
    ],
)
def test_a_partial_rerank_set_names_exactly_the_missing_rerank_keys(present):
    from databasise.clients.builder import MissingParityEnvKeyError, build_clients

    env = {**REQUIRED, **{k: RERANK[k] for k in present}}

    with pytest.raises(MissingParityEnvKeyError) as exc_info:
        build_clients(env)

    assert exc_info.value.missing_keys == [k for k in RERANK if k not in present]


def test_empty_and_null_rerank_values_count_as_absent():
    from databasise.clients.builder import build_clients

    env = {**REQUIRED, "RERANK_BINDING": "null", "RERANK_BINDING_HOST": "", "RERANK_MODEL": "", "RERANK_BINDING_API_KEY": ""}

    assert set(build_clients(env)) == {"llm", "embedding"}
    assert set(build_clients({**REQUIRED, "RERANK_BINDING": "null"})) == {"llm", "embedding"}


def test_required_and_rerank_gaps_are_named_together():
    from databasise.clients.builder import MissingParityEnvKeyError, build_clients

    env = {k: v for k, v in REQUIRED.items() if k != "LLM_MODEL"}
    env["RERANK_BINDING"] = "cohere"

    with pytest.raises(MissingParityEnvKeyError) as exc_info:
        build_clients(env)

    assert exc_info.value.missing_keys == [
        "LLM_MODEL",
        "RERANK_BINDING_HOST",
        "RERANK_MODEL",
        "RERANK_BINDING_API_KEY",
    ]


def test_an_unsupported_rerank_binding_is_refused_naming_the_key_not_the_value():
    from databasise.clients.builder import build_clients
    from databasise.clients.rerank import UnsupportedRerankBindingError

    with pytest.raises(UnsupportedRerankBindingError) as exc_info:
        build_clients({**REQUIRED, **RERANK, "RERANK_BINDING": "tei-binding-marker"})

    assert "RERANK_BINDING" in str(exc_info.value)
    assert "tei-binding-marker" not in str(exc_info.value)


def test_env_file_parser_strips_quotes_and_skips_comments(tmp_path: Path):
    from databasise.clients.builder import load_env_file

    path = tmp_path / "env"
    path.write_text(
        "# a comment\n\nPLAIN=value\nDOUBLE=\"quoted value\"\nSINGLE='single'\nMISMATCH=\"open\nEMPTY=\n",
        encoding="utf-8",
    )

    assert load_env_file(path) == {
        "PLAIN": "value",
        "DOUBLE": "quoted value",
        "SINGLE": "single",
        "MISMATCH": '"open',
        "EMPTY": "",
    }


def test_builder_errors_name_keys_never_values(tmp_path: Path):
    from databasise.clients.builder import (
        MissingParityEnvError,
        MissingParityEnvKeyError,
        UnparseableProviderRoutingError,
        build_clients,
        load_env_file,
    )
    from databasise.clients.rerank import UnsupportedRerankBindingError

    with pytest.raises(MissingParityEnvError) as missing_file:
        load_env_file(tmp_path / "absent.env")
    with pytest.raises(MissingParityEnvKeyError) as missing_key:
        build_clients({k: v for k, v in REQUIRED.items() if k != "LLM_MODEL"})
    with pytest.raises(UnparseableProviderRoutingError) as bad_routing:
        build_clients({**REQUIRED, "OPENAI_LLM_EXTRA_BODY": "{stub-route-marker"})
    with pytest.raises(UnsupportedRerankBindingError) as bad_binding:
        build_clients({**REQUIRED, **RERANK, "RERANK_BINDING": "stub-binding-marker"})

    assert "OPENAI_LLM_EXTRA_BODY" in str(bad_routing.value)
    assert "stub-route-marker" in bad_routing.value.raw_value
    # RERANK_BINDING's own value is a public shape name, listed in the refusal text on purpose.
    secrets = [
        *REQUIRED.values(),
        *(v for k, v in RERANK.items() if k != "RERANK_BINDING"),
        "stub-route-marker",
        "stub-binding-marker",
    ]
    for error in (missing_file.value, missing_key.value, bad_routing.value, bad_binding.value):
        for secret in secrets:
            assert secret not in str(error)

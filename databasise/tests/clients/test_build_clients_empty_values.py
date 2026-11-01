"""Sweep finding (phase 08): an empty required env-file value must be refused like an absent key.

``load_env_file`` yields ``""`` for ``KEY=``; ``build_clients`` used to check presence only, so a
blank host built a client with ``base_url ''`` and a blank key raised ``openai.OpenAIError``, which
no launcher refusal tuple caught. Constructing the clients makes no network call.
"""

from __future__ import annotations

import pytest

from databasise.tests.clients.test_build_clients import REQUIRED


@pytest.mark.parametrize("key", ["LLM_BINDING_HOST", "LLM_BINDING_API_KEY"])
def test_an_empty_required_value_is_refused_by_name(key):
    from databasise.clients.builder import MissingParityEnvKeyError, build_clients

    with pytest.raises(MissingParityEnvKeyError) as exc_info:
        build_clients({**REQUIRED, key: ""})

    assert exc_info.value.missing_keys == [key]


def test_an_empty_host_and_an_empty_key_are_named_together():
    from databasise.clients.builder import MissingParityEnvKeyError, build_clients

    with pytest.raises(MissingParityEnvKeyError) as exc_info:
        build_clients({**REQUIRED, "LLM_BINDING_HOST": "", "EMBEDDING_BINDING_API_KEY": ""})

    assert exc_info.value.missing_keys == ["LLM_BINDING_HOST", "EMBEDDING_BINDING_API_KEY"]


def test_client_construction_errors_are_builder_refusals():
    import openai

    from databasise.clients.builder import BUILDER_REFUSALS
    from databasise.launcher import LAUNCH_REFUSALS

    assert openai.OpenAIError in BUILDER_REFUSALS
    assert openai.OpenAIError in LAUNCH_REFUSALS

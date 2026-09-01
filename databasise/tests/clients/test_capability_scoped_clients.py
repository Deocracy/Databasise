"""Behavior tests for ``CapabilityScopedClients`` — deny-by-default scoping mirroring
``CapabilityScopedStores`` (see ``tests/parts/test_reference_parts.py``'s tests 6/7, the analog
this file's shape mirrors)."""

from __future__ import annotations

import pytest

from databasise.clients import CapabilityScopedClients, ClientNotWiredError
from databasise.parts_core import UndeclaredEffectError


def test_1_a_declared_effect_returns_the_wired_client_handle():
    llm_handle = object()
    scoped = CapabilityScopedClients({"llm": llm_handle}, ["calls_llm"])

    assert scoped.require("calls_llm") is llm_handle


def test_2_an_undeclared_effect_is_refused_naming_the_requested_effect_and_declared_list():
    scoped = CapabilityScopedClients({"llm": object()}, ["calls_llm"])

    with pytest.raises(UndeclaredEffectError) as exc_info:
        scoped.require("calls_embedding")

    assert exc_info.value.effect == "calls_embedding"
    assert exc_info.value.declared == ["calls_llm"]


def test_3_a_declared_effect_with_no_wired_client_is_a_named_refusal_not_none():
    """The effect IS declared, but the run's ``clients`` dict simply has no entry for the
    backing client key — must raise :class:`ClientNotWiredError` naming both ``calls_llm`` and
    the missing key ``llm``, never fall through to a silent ``None``.
    """
    scoped = CapabilityScopedClients({}, ["calls_llm"])

    with pytest.raises(ClientNotWiredError) as exc_info:
        scoped.require("calls_llm")

    assert exc_info.value.effect == "calls_llm"
    assert exc_info.value.client_key == "llm"


def test_4_each_of_the_three_client_effects_maps_to_its_own_key():
    scoped = CapabilityScopedClients(
        {"llm": "llm-handle", "embedding": "embedding-handle", "rerank": "rerank-handle"},
        ["calls_llm", "calls_embedding", "calls_rerank"],
    )

    assert scoped.require("calls_llm") == "llm-handle"
    assert scoped.require("calls_embedding") == "embedding-handle"
    assert scoped.require("calls_rerank") == "rerank-handle"


def test_5_a_declared_non_client_effect_is_refused_like_an_undeclared_one():
    """A declared effect with no client-shaped mapping (e.g. a store effect) cannot be fulfilled
    through the clients view at all — refused rather than leaking a raw ``KeyError``."""
    scoped = CapabilityScopedClients({}, ["calls_llm", "reads_kv"])

    with pytest.raises(UndeclaredEffectError):
        scoped.require("reads_kv")

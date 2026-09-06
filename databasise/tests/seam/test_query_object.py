"""04-01-PLAN.md Task 2: the empty-query and unconsumable-member refusals (D-14, §18.1)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from databasise.parts.registry import default_registry
from databasise.seam import Databasise, QueryObject
from databasise.seam.query import check_consumable
from databasise.seam.refusals import EmptyQueryObjectError, UnconsumableQueryMemberError
from databasise.wirings.resolve import resolve_arm

_UNCONSUMABLE_MEMBERS = [
    ("embedding", [1.0, 0.0, 0.0]),
    ("predicates", {"field": "value"}),
    ("profile_ref", "profile:abc"),
    ("formal_query", "SELECT * FROM x"),
]


def test_an_empty_query_object_is_refused_before_any_wiring_is_resolved():
    registry = default_registry()
    with pytest.raises(EmptyQueryObjectError):
        check_consumable(QueryObject(), registry)


@pytest.mark.parametrize("member_name,value", _UNCONSUMABLE_MEMBERS)
def test_each_currently_unconsumable_member_is_refused_by_name(member_name, value):
    registry = default_registry()
    query_object = QueryObject(**{member_name: value})

    with pytest.raises(UnconsumableQueryMemberError) as exc_info:
        check_consumable(query_object, registry)

    assert exc_info.value.member_name == member_name


def test_text_plus_an_unconsumable_member_raises_rather_than_answering_from_text_alone():
    registry = default_registry()
    query_object = QueryObject(text="hello", embedding=[1.0, 0.0, 0.0])

    with pytest.raises(UnconsumableQueryMemberError) as exc_info:
        check_consumable(query_object, registry)

    assert exc_info.value.member_name == "embedding"


async def test_resolve_arm_is_never_called_when_the_query_object_is_empty(tmp_path):
    engine = Databasise(store_root=tmp_path, workspace="empty-query-test")

    with patch("databasise.seam.selectors.resolve_arm") as mock_resolve_arm:
        with pytest.raises(EmptyQueryObjectError):
            await engine.query(QueryObject())

    mock_resolve_arm.assert_not_called()


def test_no_seam_refusal_message_enumerates_the_resolved_wirings_node_ids():
    node_ids = set(resolve_arm("naive").get("nodes", {}).keys())
    registry = default_registry()

    for member_name, value in _UNCONSUMABLE_MEMBERS:
        with pytest.raises(UnconsumableQueryMemberError) as exc_info:
            check_consumable(QueryObject(**{member_name: value}), registry)
        message = str(exc_info.value)
        for node_id in node_ids:
            assert node_id not in message

    with pytest.raises(EmptyQueryObjectError) as exc_info:
        check_consumable(QueryObject(), registry)
    empty_message = str(exc_info.value)
    for node_id in node_ids:
        assert node_id not in empty_message


async def test_non_ascii_text_round_trips_unchanged_through_the_seam(synthetic_naive_store):
    from databasise.clients.base import ChatResult, EmbeddingResult
    from databasise.runner.trace import TokenAccounting

    class _EchoLLMClient:
        async def chat(self, messages, **kwargs):
            return ChatResult(
                text=messages[0]["content"],
                tokens=TokenAccounting(counted_by="echo"),
                resolved_model_identity="echo-model",
            )

    class _StubEmbeddingClient:
        def __init__(self, vector: list[float]):
            self.vector = vector

        async def embed(self, texts, **kwargs):
            return EmbeddingResult(
                vectors=[self.vector for _ in texts],
                tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
                resolved_model_identity="stub-embed-model",
            )

    query_text = "你好 émoji \U0001f389 test"  # non-Latin script + emoji, §18.1's edge case

    engine = Databasise(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients={
            "embedding": _StubEmbeddingClient(vector=synthetic_naive_store["query_vector"]),
            "llm": _EchoLLMClient(),
        },
    )

    envelope = await engine.query(QueryObject(text=query_text))

    # The echo client returns the exact prompt it was handed; the query text must reach it
    # byte-for-byte unchanged and survive back out into the envelope's answer field.
    assert query_text in envelope.answer

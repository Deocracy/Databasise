"""04-03-PLAN.md Task 2: the alias selector's read path against a real ``Ledger`` (D-12, FA-06).

The "populated" cases below append a real ``LedgerRecord`` through ``Ledger.append`` and then
resolve it — this is the test's own setup standing in for Phase 7's promote path, since Phase 7's
real promote path does not exist yet. It is not evidence that promotion exists; it proves the read
contract ``databasise/seam/selectors.py``'s module docstring names for Phase 7 to write to.
"""

from __future__ import annotations

import sqlite3

import pytest

from databasise.clients.base import ChatResult
from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.runner.trace import TokenAccounting
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.seam.refusals import UnsatisfiableSelectorError
from databasise.seam.selectors import Selector, _resolve_alias
from databasise.wirings.resolve import resolve_arm

_PROMOTED_ALIAS = "prod-lightrag"


def _record(**overrides) -> LedgerRecord:
    base = {
        "mutation_id": "naive",
        "mutation_class": "retrieval-side",
        "parent": None,
        "arm_instance_hashes": [],
        "effect_size": None,
        "verdict": "promote",
        "evidence_pointer": None,
        "proposer_id": "test-fixture",
        "depth_label": "stage",
        "tier_of_decision": None,
        "decomposition_ratio": None,
        "opaque_ttl_renewals": [],
        "parity_records": [],
        "promotion_provenance": "operator_asserted",
        "promotion_trace_ids": [],
        "change_origin": "human_edit",
        "record_kind": "promotion",
        "alias": _PROMOTED_ALIAS,
    }
    base.update(overrides)
    return LedgerRecord(**base)


class _StubLLMClient:
    def __init__(self, text: str):
        self.text = text

    async def chat(self, messages, **kwargs):
        return ChatResult(
            text=self.text,
            tokens=TokenAccounting(prompt_tokens=1, completion_tokens=1, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


def test_an_empty_registry_refuses_the_alias_by_exception_type(store_root):
    Ledger(store_root)  # stands up the (empty) ledger table

    with pytest.raises(UnsatisfiableSelectorError) as exc_info:
        _resolve_alias("no-such-alias", store_root=store_root)

    assert exc_info.value.selector_kind == "alias"


def test_the_refusal_message_names_the_consumers_alias_and_no_other_mutation_id(store_root):
    ledger = Ledger(store_root)
    ledger.append(_record(mutation_id="some-other-mutation", alias="some-other-alias"))

    with pytest.raises(UnsatisfiableSelectorError) as exc_info:
        _resolve_alias("missing-alias", store_root=store_root)

    message = str(exc_info.value)
    assert "missing-alias" in message
    assert "some-other-mutation" not in message
    assert "some-other-alias" not in message


def test_an_alias_absent_from_a_non_empty_registry_raises_the_identical_refusal_type(store_root):
    ledger = Ledger(store_root)
    ledger.append(_record())

    with pytest.raises(UnsatisfiableSelectorError):
        _resolve_alias("not-the-promoted-alias", store_root=store_root)


def test_a_promoted_alias_resolves_via_the_mutation_id_field_named_at_the_checkpoint(store_root):
    ledger = Ledger(store_root)
    ledger.append(_record(mutation_id="naive", alias=_PROMOTED_ALIAS))

    resolved = _resolve_alias(_PROMOTED_ALIAS, store_root=store_root)

    assert resolved == resolve_arm("naive")


def test_the_most_recent_row_for_an_alias_wins_exactly_like_active_pointer(store_root):
    ledger = Ledger(store_root)
    ledger.append(_record(mutation_id="naive", alias=_PROMOTED_ALIAS, verdict="inconclusive"))
    ledger.append(_record(mutation_id="bypass", alias=_PROMOTED_ALIAS, verdict="promote"))

    resolved = _resolve_alias(_PROMOTED_ALIAS, store_root=store_root)

    assert resolved == resolve_arm("bypass")


def test_alias_resolution_performs_no_ledger_append(store_root):
    ledger = Ledger(store_root)
    ledger.append(_record(mutation_id="naive", alias=_PROMOTED_ALIAS))
    before = ledger._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]

    _resolve_alias(_PROMOTED_ALIAS, store_root=store_root)

    after = ledger._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    assert after == before


async def test_a_full_query_through_the_alias_selector_performs_no_ledger_append(store_root):
    ledger = Ledger(store_root)
    ledger.append(_record(mutation_id="bypass", alias=_PROMOTED_ALIAS))
    before = ledger._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]

    engine = Databasise(
        store_root=store_root,
        workspace="alias-test",
        clients={"llm": _StubLLMClient("stub completion for the alias selector test")},
    )
    envelope = await engine.query(QueryObject(text="irrelevant, bypass ignores context"), Selector(alias=_PROMOTED_ALIAS))

    after = ledger._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    assert after == before
    assert envelope.answer == "stub completion for the alias selector test"


def test_the_ledgers_own_update_and_delete_triggers_still_refuse_after_the_alias_column_lands(store_root):
    """Regression guard: the additive ``alias`` column must not have disturbed the append-only
    triggers ``databasise/tests/ledger/test_ledger.py`` already proves against the pre-alias
    schema.
    """
    ledger = Ledger(store_root)
    ledger.append(_record(mutation_id="naive"))

    with pytest.raises(sqlite3.IntegrityError):
        ledger._conn.execute("UPDATE ledger SET alias = 'x' WHERE mutation_id = 'naive'")

"""04-03-PLAN.md: the §18.4 selectors — the capability branch (Task 1), the alias branch
(Task 2), the harness branch and the default selector's opaque exclusion, plus the §18.5
falsifier check (Task 3).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pydantic
import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.parts.registry import default_registry
from databasise.parts.schema import Part
from databasise.runner import scheduler
from databasise.runner.trace import TokenAccounting
from databasise.seam import selectors
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.seam.refusals import UnsatisfiableSelectorError
from databasise.seam.selectors import Selector
from databasise.stores.kv import SqliteKVStore
from databasise.validator.parse import ParsedWiring, parse_wiring
from databasise.wirings.resolve import resolve_arm

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load_harness_fixture() -> dict:
    return json.loads((_FIXTURES_DIR / "wiring-harness.json").read_text(encoding="utf-8"))

_ARM_NAMES: tuple[str, ...] = ("naive", "bypass", "hybrid", "local", "global")
_ALL_NODE_IDS: set[str] = set().union(
    *(set(resolve_arm(name).get("nodes", {}).keys()) for name in _ARM_NAMES)
)


class _StubLLMClient:
    def __init__(self, text: str):
        self.text = text

    async def chat(self, messages, **kwargs):
        return ChatResult(
            text=self.text,
            tokens=TokenAccounting(prompt_tokens=1, completion_tokens=1, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


# --------------------------------------------------------------------------------------------- #
# Task 1: the capability selector
# --------------------------------------------------------------------------------------------- #

_BYPASS_COMPLETION = "This is the bypass arm's own stub completion for the capability selector test."


async def test_a_capability_selector_resolves_to_a_wiring_and_returns_a_real_envelope(tmp_path):
    engine = Databasise(
        store_root=tmp_path,
        workspace="capability-test",
        clients={"llm": _StubLLMClient(_BYPASS_COMPLETION)},
    )

    envelope = await engine.query(
        QueryObject(text="does not matter, bypass ignores context"),
        Selector(capability=["calls_llm"]),
    )

    # Real value, never shape alone: the stub client's own configured completion text, proving
    # the capability selector actually reached (and ran) the bypass arm, the smallest of the
    # arms whose registered parts declare calls_llm.
    assert envelope.answer == _BYPASS_COMPLETION


def test_an_unsatisfiable_capability_selector_raises_and_never_falls_through_to_the_default():
    registry = default_registry()

    with patch.object(selectors, "_resolve_default") as spy_default:
        with pytest.raises(UnsatisfiableSelectorError) as exc_info:
            selectors.resolve_selector(Selector(capability=["fs"]), registry=registry)

    spy_default.assert_not_called()
    assert exc_info.value.selector_kind == "capability"


def test_the_unsatisfiable_capability_refusal_discloses_no_candidate_wiring_or_node_id():
    registry = default_registry()
    all_wiring_ids = {resolve_arm(name).get("wiring_id", name) for name in _ARM_NAMES}

    with pytest.raises(UnsatisfiableSelectorError) as exc_info:
        selectors.resolve_selector(Selector(capability=["fs"]), registry=registry)

    message = str(exc_info.value)
    for node_id in _ALL_NODE_IDS:
        assert node_id not in message
    for wiring_id in all_wiring_ids:
        assert wiring_id not in message


@pytest.mark.parametrize(
    "kwargs",
    [
        {"alias": "a" * 64},
        {"alias": "sha256:" + "b" * 64},
        {"harness": "c" * 64},
        {"capability": ["d" * 64]},
    ],
)
def test_an_instance_hash_shaped_selector_value_raises_validation_error(kwargs):
    with pytest.raises(pydantic.ValidationError):
        Selector(**kwargs)


def test_selectors_reads_provides_and_harnesses_off_the_raw_resolved_dict_never_parsed_wiring():
    resolved = resolve_arm("bypass")
    registry = default_registry()
    parsed = parse_wiring(resolved, registry)

    # The raw dict carries these fields...
    assert "provides" in resolved
    assert "harnesses" in resolved
    # ...but ParsedWiring never does — a future refactor toward the validator's own snapshot
    # would fail loudly here rather than silently losing these fields (Pitfall 1).
    assert not hasattr(parsed, "provides")
    assert not hasattr(parsed, "harnesses")
    assert set(ParsedWiring.__dataclass_fields__) == {"nodes", "parts", "deps", "node_order", "report"}


# --------------------------------------------------------------------------------------------- #
# Task 3: the harness selector (D-13, FA-05)
# --------------------------------------------------------------------------------------------- #


def test_wiring_harness_fixture_declares_exactly_two_entries_in_a_declared_order():
    """No production wiring in this repository declares a harness (every one of the five arms'
    own ``harnesses`` array is empty) — this fixture is the harness selector's only real subject,
    named plainly as such in its own ``title`` field (FA-05).
    """
    fixture = _load_harness_fixture()
    assert fixture["harnesses"] == ["first-stage-harness", "second-stage-harness"]


def test_the_harness_selector_resolves_the_fixture_and_preserves_declared_order():
    fixture = _load_harness_fixture()

    resolved = selectors._resolve_harness(
        "first-stage-harness",
        registry=default_registry(),
        candidates=[("harness-fixture", fixture)],
    )

    assert resolved["harnesses"] == fixture["harnesses"]


def test_an_unknown_harness_name_raises_the_named_refusal_by_exception_type():
    fixture = _load_harness_fixture()

    with pytest.raises(UnsatisfiableSelectorError) as exc_info:
        selectors._resolve_harness(
            "no-such-harness",
            registry=default_registry(),
            candidates=[("harness-fixture", fixture)],
        )

    assert exc_info.value.selector_kind == "harness"


def test_no_production_arm_declares_a_harness_so_the_production_branch_always_refuses():
    """FA-05's own declared limitation, proven directly: the production candidate pool (the five
    Phase 3 arms) never satisfies any harness name, since every arm's own ``harnesses`` array is
    empty.
    """
    with pytest.raises(UnsatisfiableSelectorError):
        selectors._resolve_harness("first-stage-harness", registry=default_registry())


async def test_the_harness_fixture_dispatches_a_real_run_end_to_end(store_root):
    fixture = _load_harness_fixture()
    registry = default_registry()
    parsed = parse_wiring(fixture, registry)
    assert parsed.report.ok, [v.code for v in parsed.report.violations]

    kv_store = SqliteKVStore(namespace="harness-fixture", workspace="harness-test", store_root=store_root)
    try:
        result = await scheduler.run_wiring(
            parsed,
            registry,
            stores={"kv": kv_store},
            determinism_setting="cache-bypassed",
            concurrency_setting="sequential",
            clients={},
        )
    finally:
        await kv_store.finalize()

    assert result["partial"] is False
    assert result["results"]["call"]["completion"]


# --------------------------------------------------------------------------------------------- #
# Task 3: the default selector's opaque exclusion (D-13, §8 condition 7)
# --------------------------------------------------------------------------------------------- #


async def _opaque_test_fixture_body(ctx):
    return {"node_id": ctx.node_id}


_OPAQUE_TEST_PART = Part(
    name_at_version="test-fixture/opaque-node@1.0.0",
    kind="opaque-test-fixture",
    structural_depth="opaque",
    effects=["reads_blob"],
    upstream_ref=None,
    body=_opaque_test_fixture_body,
)

_OPAQUE_WIRING: dict = {
    "wiring_id": "opaque-fixture",
    "wiring_version": "1",
    "nodes": {
        "opaque-node": {
            "component": "test-fixture/opaque-node@1.0.0",
            "kind": "opaque-test-fixture",
            "effects": ["reads_blob"],
            "deps": [],
        }
    },
    "recipe": {},
    "harnesses": ["opaque-harness"],
    "provides": ["opaque-node"],
}


def _registry_with_opaque_fixture():
    registry = default_registry()
    registry.register(_OPAQUE_TEST_PART)
    return registry


def test_a_wiring_whose_provides_node_is_opaque_is_excluded_from_the_default_candidate_set():
    registry = _registry_with_opaque_fixture()

    assert selectors._is_default_eligible(_OPAQUE_WIRING, registry) is False
    with pytest.raises(UnsatisfiableSelectorError):
        selectors._resolve_default(
            registry=registry, candidates=[("opaque-fixture", _OPAQUE_WIRING)]
        )


def test_the_same_opaque_wiring_remains_reachable_by_capability():
    registry = _registry_with_opaque_fixture()

    resolved = selectors._resolve_capability(
        ["reads_blob"], registry=registry, candidates=[("opaque-fixture", _OPAQUE_WIRING)]
    )

    assert resolved == _OPAQUE_WIRING


def test_the_same_opaque_wiring_remains_reachable_by_harness():
    registry = _registry_with_opaque_fixture()

    resolved = selectors._resolve_harness(
        "opaque-harness", registry=registry, candidates=[("opaque-fixture", _OPAQUE_WIRING)]
    )

    assert resolved == _OPAQUE_WIRING


def test_naive_remains_the_default_because_its_own_provides_node_is_never_opaque():
    """Regression guard: ``naive`` itself contains an unrelated opaque node (``embedder-index``,
    dep-free, per ``test_arm_conformance.py``'s own conformance proof), but its own ``provides``
    node (``generate``) is always ``stage`` — the default selector must still resolve ``naive``,
    unchanged from 04-01/04-02's already-established behaviour.
    """
    resolved = selectors._resolve_default(registry=default_registry())

    assert resolved == resolve_arm("naive")


# --------------------------------------------------------------------------------------------- #
# Task 3: the §18.5 falsifier — all four selector forms reach a real run, no wiring named
# --------------------------------------------------------------------------------------------- #


class _StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self.vector = vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


def _falsifier_ledger_record(*, mutation_id: str, alias: str) -> LedgerRecord:
    return LedgerRecord(
        mutation_id=mutation_id,
        mutation_class="retrieval-side",
        parent=None,
        arm_instance_hashes=[],
        effect_size=None,
        verdict="promote",
        evidence_pointer=None,
        proposer_id="falsifier-fixture",
        depth_label="stage",
        tier_of_decision=None,
        decomposition_ratio=None,
        opaque_ttl_renewals=[],
        parity_records=[],
        promotion_provenance="operator_asserted",
        promotion_trace_ids=[],
        alias=alias,
    )


async def test_falsifier_default_selector_reaches_naive_with_no_wiring_named(synthetic_naive_store):
    engine = Databasise(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients={
            "embedding": _StubEmbeddingClient(vector=synthetic_naive_store["query_vector"]),
            "llm": _StubLLMClient("falsifier default completion"),
        },
    )

    envelope = await engine.query(QueryObject(text="Which films did Ed Wood direct?"))

    assert envelope.answer == "falsifier default completion"


async def test_falsifier_alias_selector_reaches_bypass_with_no_wiring_named(store_root):
    alias = "falsifier-alias"
    assert alias not in _ARM_NAMES
    assert alias not in _ALL_NODE_IDS

    ledger = Ledger(store_root)
    ledger.append(_falsifier_ledger_record(mutation_id="bypass", alias=alias))

    engine = Databasise(
        store_root=store_root,
        workspace="falsifier-alias",
        clients={"llm": _StubLLMClient("falsifier alias completion")},
    )
    envelope = await engine.query(QueryObject(text="irrelevant"), Selector(alias=alias))

    assert envelope.answer == "falsifier alias completion"


async def test_falsifier_capability_selector_reaches_bypass_with_no_wiring_named(tmp_path):
    requested = ["calls_llm"]
    assert not (set(requested) & set(_ARM_NAMES))
    assert not (set(requested) & _ALL_NODE_IDS)

    engine = Databasise(
        store_root=tmp_path,
        workspace="falsifier-capability",
        clients={"llm": _StubLLMClient("falsifier capability completion")},
    )
    envelope = await engine.query(QueryObject(text="irrelevant"), Selector(capability=requested))

    assert envelope.answer == "falsifier capability completion"


async def test_falsifier_harness_selector_reaches_the_fixture_with_no_wiring_named(store_root):
    """FA-05's own documented exception: the harness form reaches the fixture, not one of the
    five Phase 3 arms — no production wiring declares a harness at all (see the fixture's own
    ``title`` and this module's harness-selector tests above)."""
    harness_name = "first-stage-harness"
    assert harness_name not in _ARM_NAMES
    assert harness_name not in _ALL_NODE_IDS

    fixture = _load_harness_fixture()
    registry = default_registry()
    resolved = selectors._resolve_harness(
        harness_name, registry=registry, candidates=[("harness-fixture", fixture)]
    )
    parsed = parse_wiring(resolved, registry)
    assert parsed.report.ok

    kv_store = SqliteKVStore(
        namespace="falsifier-harness", workspace="falsifier-harness", store_root=store_root
    )
    try:
        result = await scheduler.run_wiring(
            parsed,
            registry,
            stores={"kv": kv_store},
            determinism_setting="cache-bypassed",
            concurrency_setting="sequential",
            clients={},
        )
    finally:
        await kv_store.finalize()

    assert result["results"]["call"]["completion"]

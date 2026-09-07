"""04-04-PLAN.md Task 3: the two-tier leak gate (D-05, 04-RESEARCH.md Pitfall 8) over a complete
real envelope — evidence, a multi-``counted_by`` token breakdown, a trace reference, and a MACH-11
seam event, all populated by one real run.

**Why this test does not call ``Databasise.query()``.** No selector this phase implements can
route a caller to a custom wiring: the four §18.4 selectors resolve only one of the five committed
LightRAG arms (default/capability), a ledger-registered alias pointing at one of those same five
arms (D-12), or the harness fixture only through a direct unit-test call to
``databasise.seam.selectors._resolve_harness`` with an injected candidate pool (04-03) — never
through the public ``Selector`` a consumer actually passes. None of the five arms declares a
``mutates_store`` node. To get evidence, real multi-``counted_by`` tokens, a trace reference AND a
seam event out of one real run, this test replicates ``Databasise.query()``'s own internal
assembly (see ``databasise/seam/engine.py``) directly over the naive arm's resolved wiring plus one
spliced-in out-of-``deps`` mutating fixture node — reusing the exact same production functions
``query()`` calls, never a re-implementation of them.

**The corpus.** The single synthetic document this test's store holds is
``databasise/tests/seam/conftest.py``'s own ``_CONTENT`` ("Ed Wood directed several low-budget
films.") — already the shared fixture every other test in this directory drives the naive arm
against. It is reused here, rather than authoring a second corpus, specifically because it
contains none of this run's own node ids/wiring id (no "generate", "keywords", "embedder",
"chunk", "rerank", "assemble", "backfill", "mutator", "seam", or "lightrag" appears in it) — a
precondition this test asserts explicitly rather than assumes.
"""

from __future__ import annotations

import hashlib
import json
import uuid

import pytest

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.identity.canon import canonicalise
from databasise.parts.registry import Part, default_registry
from databasise.parts.schema import NodeContext
from databasise.parts_core import CapabilityScopedStores
from databasise.runner.scheduler import _ScopedStoresView, run_wiring
from databasise.runner.trace import RunRecord, TokenAccounting
from databasise.seam.engine import (
    _CONCURRENCY_SETTING,
    _DEFAULT_TOKEN_ALLOWANCE,
    _DETERMINISM_SETTING,
    _EVIDENCE_RETRIEVAL_NODE_ID,
    _EXECUTOR_VERSION,
    _build_stores,
    _inject_query,
    _inject_token_allowance,
    _mach11_events,
)
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.evidence import CHUNKS_NAMESPACE, mint_evidence_refs
from databasise.seam.redact import assert_no_forbidden_keys, forbidden_identities
from databasise.seam.tokens import assemble_token_breakdown
from databasise.seam.trace_store import TraceStore
from databasise.tests.seam.conftest import _CONTENT
from databasise.validator.parse import parse_wiring
from databasise.wirings.resolve import resolve_arm

_QUERY_TEXT = "Which films did Ed Wood direct?"
_OUT_OF_DEPS_MUTATOR_NAME = "test/leak-out-of-deps-mutator@1.0.0"
_MUTATOR_EFFECTS = ["mutates_store", "writes_kv"]


class _StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self.vector = vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    async def chat(self, messages, **kwargs):
        return ChatResult(
            text="This is a stub completion for the leak-gate test.",
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


async def _mutator_body(ctx: NodeContext) -> dict[str, object]:
    """Never actually dispatched (D-08: mutates_store -> confined-unit -> unhosted in Phase 1) —
    see databasise/tests/seam/test_mach11_event.py's own module docstring for the full note."""
    store = ctx.stores["kv"]
    await store.upsert({ctx.node_id: {"mutated": True}})
    return {"node_id": ctx.node_id}


async def _drive_one_real_run_with_a_complete_envelope(
    synthetic_naive_store,
) -> tuple[ResponseEnvelope, RunRecord]:
    """The naive arm's own resolved wiring plus one spliced-in out-of-``deps`` mutating fixture
    node, run for real, assembled into a real ``ResponseEnvelope`` via the exact functions
    ``Databasise.query()`` itself calls (see this module's own docstring for why ``query()``
    itself cannot be used directly).
    """
    resolved = resolve_arm("naive")
    resolved = _inject_query(resolved, _QUERY_TEXT)
    resolved = _inject_token_allowance(resolved, _DEFAULT_TOKEN_ALLOWANCE)
    # The extra node's dep (embedder-query, effects=["calls_embedding"]) accounts for no store
    # key at all — an out-of-deps mutation the instant this node touches "kv" (FA-08's rule).
    resolved["nodes"]["out-of-deps-mutator"] = {
        "component": _OUT_OF_DEPS_MUTATOR_NAME,
        "kind": "mutator",
        "effects": _MUTATOR_EFFECTS,
        "deps": ["embedder-query"],
    }

    registry = default_registry()
    registry.register(
        Part(
            name_at_version=_OUT_OF_DEPS_MUTATOR_NAME,
            kind="mutator",
            structural_depth="stage",
            effects=list(_MUTATOR_EFFECTS),
            upstream_ref=None,
            body=_mutator_body,
        )
    )
    parsed = parse_wiring(resolved, registry)
    assert parsed.report.ok, [v.code for v in parsed.report.violations]

    stores = _build_stores(synthetic_naive_store["store_root"], synthetic_naive_store["workspace"])
    touches: list[tuple[str, str, str]] = []

    def recorder(node_id: str, kind: str, key: str) -> None:
        touches.append((node_id, kind, key))

    try:
        scheduled = await run_wiring(
            parsed,
            registry,
            stores,
            determinism_setting=_DETERMINISM_SETTING,
            concurrency_setting=_CONCURRENCY_SETTING,
            clients={
                "embedding": _StubEmbeddingClient(vector=synthetic_naive_store["query_vector"]),
                "llm": _StubLLMClient(),
            },
            recorder=recorder,
        )
        # D-08 (see test_mach11_event.py): the mutator node cannot complete real dispatch, so its
        # own touch is produced via the scheduler's own production touch-recording class directly.
        view = _ScopedStoresView(
            CapabilityScopedStores(stores, _MUTATOR_EFFECTS),
            _MUTATOR_EFFECTS,
            "out-of-deps-mutator",
            recorder,
        )
        view["kv"]
    finally:
        for store in stores.values():
            await store.finalize()

    wiring_bytes = canonicalise(resolved)
    wiring_instance_hash = f"sha256:{hashlib.sha256(wiring_bytes).hexdigest()}"
    wiring_id = resolved.get("wiring_id") or f"wiring:{hashlib.sha256(wiring_bytes).hexdigest()[:16]}"

    record = RunRecord(
        run_id=str(uuid.uuid4()),
        wiring_id=wiring_id,
        wiring_instance_hash=wiring_instance_hash,
        arm_id="seam",
        arm_execution_order=0,
        executor_version=_EXECUTOR_VERSION,
        concurrency_setting=_CONCURRENCY_SETTING,
        determinism_setting=_DETERMINISM_SETTING,
        nodes=scheduled["nodes"],
        partial=scheduled["partial"],
        degraded=scheduled["degraded"],
        stop_reason=scheduled["stop_reason"],
        degradation_reason=scheduled["degradation_reason"],
    )

    provides = resolved.get("provides") or []
    provided = {node_id: scheduled["results"].get(node_id) for node_id in provides}
    answer = ""
    depth_label = "stage"
    for node in record.nodes:
        if node.node_id not in provides:
            continue
        depth_label = node.effective_depth
        output = provided.get(node.node_id)
        if isinstance(output, dict) and "completion" in output:
            answer = str(output["completion"])

    retrieval_output = scheduled["results"].get(_EVIDENCE_RETRIEVAL_NODE_ID)
    retrieval_items = retrieval_output["items"] if isinstance(retrieval_output, dict) else []
    evidence = mint_evidence_refs(retrieval_items, namespace=CHUNKS_NAMESPACE)

    token_accounting = assemble_token_breakdown(record.nodes)

    node_by_id = {node.node_id: node for node in record.nodes}
    seam_events = _mach11_events(parsed, touches, node_by_id)

    trace_store = TraceStore(synthetic_naive_store["store_root"])
    trace_token = trace_store.persist(record.to_dict())

    envelope = ResponseEnvelope(
        answer=answer,
        evidence=evidence,
        trace_token=trace_token,
        depth_label=depth_label,
        partial=record.partial,
        degraded=record.degraded,
        stop_reason=record.stop_reason,
        degradation_reason=record.degradation_reason,
        token_accounting=token_accounting,
        seam_events=seam_events,
    )

    return envelope, record


@pytest.fixture
async def complete_run(synthetic_naive_store):
    return await _drive_one_real_run_with_a_complete_envelope(synthetic_naive_store)


async def test_the_envelope_carries_every_field_this_phase_populates_before_the_leak_gate_runs(
    complete_run,
):
    """Asserted first, before either leak check: an accidentally-empty envelope must not be able
    to pass the leak gate vacuously."""
    envelope, _record = complete_run

    assert envelope.evidence
    assert len({entry.counted_by for entry in envelope.token_accounting}) > 1
    assert envelope.trace_token
    assert envelope.seam_events


async def test_no_high_entropy_identity_appears_anywhere_in_the_serialized_envelope(complete_run):
    envelope, record = complete_run
    high_entropy, _low_entropy = forbidden_identities(record.to_dict())
    serialized = envelope.model_dump_json()

    for value in high_entropy:
        assert value not in serialized, f"high-entropy identity {value!r} leaked into the envelope"


async def test_no_forbidden_key_appears_at_any_nesting_depth_in_the_parsed_envelope(complete_run):
    envelope, record = complete_run
    _high_entropy, low_entropy = forbidden_identities(record.to_dict())
    parsed_envelope = json.loads(envelope.model_dump_json())

    assert_no_forbidden_keys(parsed_envelope, low_entropy)


async def test_the_forbidden_set_is_built_from_the_run_record_and_contains_a_64_char_hex_value(
    complete_run,
):
    _envelope, record = complete_run
    high_entropy, low_entropy = forbidden_identities(record.to_dict())

    assert high_entropy
    assert low_entropy
    assert any(len(value) == 64 and all(c in "0123456789abcdef" for c in value) for value in high_entropy)


async def test_the_chosen_corpus_contains_none_of_the_runs_low_entropy_identity_strings(complete_run):
    """Explicit precondition (Pitfall 8): a corpus that happened to contain a node id as an
    ordinary word would make the *structural* check meaningless as a demonstration, even though
    the structural check itself never inspects string content — see this module's own docstring."""
    _envelope, record = complete_run
    _high_entropy, low_entropy = forbidden_identities(record.to_dict())

    for value in low_entropy:
        assert value not in _CONTENT, f"corpus content contains the low-entropy value {value!r}"


# --------------------------------------------------------------------------------------------- #
# Negative controls: both tiers are proven to fail on a planted violation.
# --------------------------------------------------------------------------------------------- #


def test_the_structural_check_fails_on_a_hand_built_forbidden_key_at_nesting_depth_three():
    forbidden = {"generate"}
    hostile = {"a": {"b": {"generate": "a leaked value"}}}

    with pytest.raises(AssertionError):
        assert_no_forbidden_keys(hostile, forbidden)


async def test_the_high_entropy_check_fails_on_a_string_containing_a_real_instance_hash(complete_run):
    _envelope, record = complete_run
    high_entropy, _low_entropy = forbidden_identities(record.to_dict())
    real_instance_hash = next(iter(high_entropy))
    hostile_text = json.dumps({"leaked": real_instance_hash})

    with pytest.raises(AssertionError):
        assert real_instance_hash not in hostile_text

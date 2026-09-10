"""06-09-PLAN.md Task 2: §14.4 point 3's explicit refusal, in the comparison path —
``Databasise.compare()`` refuses a comparison whose selectors resolve a ``mutates_store``-
declaring wiring, before any arm executes.

Drives the real, committed ``codebase-memory-mcp@0.1.0`` wiring (``databasise/wirings/
codebase-memory-mcp.json``, the real registered ``Part`` in ``default_registry()``) through a
real ``Databasise.compare()`` call. As of this plan's own F-07 record (Method and limits), that
wiring is not resolvable through any of §18.4's four production selectors today —
``databasise/wirings/resolve.py``'s ``WIRING_NAMES`` names only ``("lightrag", "hipporag")``, and
even adding a third name there would not resolve it: ``load_wiring()`` reads
``<name>/base.json`` (a per-modality subdirectory, matching ``lightrag/`` and ``hipporag/``),
while the committed file lives flat at ``databasise/wirings/codebase-memory-mcp.json`` — a
different, deliberately non-modality layout (this wiring is not a query-answering modality; see
``PARTS.md ## §X``'s own "no arm family" verdict). The ``cbm_reachable`` fixture below reads that
real, committed file directly and appends it to the capability selector's own candidate pool for
the duration of one test only, via ``monkeypatch`` over ``selectors.py``'s own
``_capability_candidates`` — never a production code change — so this module drives the *real*
wiring file's own JSON content and the *real* registered Part's own declared effects through the
*real* selector-resolution and refusal-check code path, rather than a hand-built stand-in
candidate.

``engine._execute`` is replaced with a call-recording spy rather than seeded with real store
data: since every store write a comparison could make happens strictly inside ``_execute()``, a
spy with zero recorded calls is a direct, sufficient proof that no arm ran and therefore no store
was written — stronger than asserting on the raised exception alone (this plan's own instruction:
"assert on the absence of any store write, not only on the raised exception, so a refusal that
fires after an arm already ran would still fail").
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from databasise.seam import Databasise, QueryObject
from databasise.seam import selectors as selectors_module
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.refusals import MutableStoreComparisonExcludedError
from databasise.seam.selectors import Selector

_QUERY_TEXT = "does this component mutate its own backing store?"

# databasise/tests/seam/test_mutable_store_exclusion.py -> databasise/wirings/
_CBM_WIRING_PATH = (
    Path(__file__).resolve().parent.parent.parent / "wirings" / "codebase-memory-mcp.json"
)

# codebase-memory-mcp@0.1.0's own declared effects (databasise/parts_core/declared_only.py) are
# the only registered Part set declaring "mutates_store" that also satisfies this exact singleton
# request — no LightRAG arm or the HippoRAG base wiring declares it.
_MUTATES_STORE_CAPABILITY = ["mutates_store"]
# The naive arm's own smallest-satisfying capability (mirrors test_compare.py's own choice).
_LIGHTRAG_CAPABILITY = ["reads_vector"]
_HIPPORAG_CAPABILITY = ["reads_graph", "reads_kv"]

_CBM_NAME_AT_VERSION = "codebase-memory-mcp@0.1.0"


@pytest.fixture
def cbm_reachable(monkeypatch):
    """Makes the real, committed ``codebase-memory-mcp`` wiring resolvable through the capability
    selector for the duration of one test, by reading its real committed JSON file directly and
    appending it to :func:`~databasise.seam.selectors._capability_candidates`'s own candidate
    pool — mirrors the reachability this plan's own read_first material assumed already existed.
    Reverted automatically by ``monkeypatch`` at test teardown; never mutates the module for any
    other test in this suite, and never edits ``WIRING_NAMES``/``load_wiring`` (which assume a
    per-modality ``<name>/base.json`` layout this wiring does not use)."""
    cbm_resolved = json.loads(_CBM_WIRING_PATH.read_text(encoding="utf-8"))
    original_candidates = selectors_module._capability_candidates

    def _with_cbm() -> list[tuple[str, dict]]:
        return [*original_candidates(), ("codebase-memory-mcp", cbm_resolved)]

    monkeypatch.setattr(selectors_module, "_capability_candidates", _with_cbm)


def _make_engine(tmp_path) -> Databasise:
    return Databasise(store_root=tmp_path, workspace="mutable-store-exclusion-test", clients={})


class _ExecuteSpy:
    """Records every ``(query_object, selector)`` pair it is awaited with, in order, and returns
    a fixed, minimal envelope — standing in for ``Databasise._execute`` so a test can prove
    whether an arm ran at all without seeding real store data for a wiring this test suite exists
    to prove never executes."""

    def __init__(self) -> None:
        self.calls: list[Selector] = []

    async def __call__(self, query_object: QueryObject, selector: Selector) -> ResponseEnvelope:
        del query_object
        self.calls.append(selector)
        return ResponseEnvelope(answer="", depth_label="stage", partial=False, degraded=False)


async def test_comparison_resolving_mutates_store_wiring_is_refused(cbm_reachable, tmp_path):
    engine = _make_engine(tmp_path)
    spy = _ExecuteSpy()
    engine._execute = spy

    with pytest.raises(MutableStoreComparisonExcludedError) as exc_info:
        await engine.compare(
            QueryObject(text=_QUERY_TEXT),
            [Selector(capability=_LIGHTRAG_CAPABILITY), Selector(capability=_MUTATES_STORE_CAPABILITY)],
        )

    message = str(exc_info.value)
    assert "MutableStoreComparisonExcludedError" in message
    assert _CBM_NAME_AT_VERSION in message
    assert exc_info.value.component == _CBM_NAME_AT_VERSION


async def test_refusal_fires_before_any_arm_executes_no_store_write_possible(cbm_reachable, tmp_path):
    """Ordered the other way (the mutates_store selector first) — proves the check runs over
    every selector before any execution starts, not lazily per-arm as ``compare_arms`` would
    otherwise process them."""
    engine = _make_engine(tmp_path)
    spy = _ExecuteSpy()
    engine._execute = spy

    with pytest.raises(MutableStoreComparisonExcludedError):
        await engine.compare(
            QueryObject(text=_QUERY_TEXT),
            [Selector(capability=_MUTATES_STORE_CAPABILITY), Selector(capability=_LIGHTRAG_CAPABILITY)],
        )

    # No store write is possible unless _execute is called — zero calls is the direct proof, not
    # merely the absence of a raised-late exception.
    assert spy.calls == []


async def test_single_selector_resolving_the_same_wiring_is_a_run_not_refused(cbm_reachable, tmp_path):
    """RIG §RUN.3's degenerate-width rule: one selector is a run, never a comparison — §14.4
    point 3 excludes the component from parity/determinism *comparisons*, not from execution."""
    engine = _make_engine(tmp_path)
    spy = _ExecuteSpy()
    engine._execute = spy

    result = await engine.compare(
        QueryObject(text=_QUERY_TEXT), [Selector(capability=_MUTATES_STORE_CAPABILITY)]
    )

    assert isinstance(result, ResponseEnvelope)
    assert len(spy.calls) == 1


async def test_comparison_between_two_non_mutable_wirings_is_unaffected(tmp_path):
    """No ``cbm_reachable`` fixture here — codebase-memory-mcp stays unreachable, as in
    production, and neither LightRAG's naive arm nor the HippoRAG base wiring declares
    mutates_store, so this comparison must proceed exactly as it did before this plan."""
    engine = _make_engine(tmp_path)
    spy = _ExecuteSpy()
    engine._execute = spy

    result = await engine.compare(
        QueryObject(text=_QUERY_TEXT),
        [Selector(capability=_LIGHTRAG_CAPABILITY), Selector(capability=_HIPPORAG_CAPABILITY)],
    )

    assert isinstance(result, dict)
    assert len(spy.calls) == 2


async def test_refusal_names_only_the_excluded_component(cbm_reachable, tmp_path):
    engine = _make_engine(tmp_path)
    engine._execute = _ExecuteSpy()

    with pytest.raises(MutableStoreComparisonExcludedError) as exc_info:
        await engine.compare(
            QueryObject(text=_QUERY_TEXT),
            [Selector(capability=_LIGHTRAG_CAPABILITY), Selector(capability=_MUTATES_STORE_CAPABILITY)],
        )

    message = str(exc_info.value)
    # The excluded component's own name is present exactly once; no other candidate wiring, arm
    # name or node id is named anywhere in the message.
    assert message.count(_CBM_NAME_AT_VERSION) == 1
    for forbidden in ("naive", "hipporag/base", "lightrag/base", "cbm"):
        assert forbidden not in message

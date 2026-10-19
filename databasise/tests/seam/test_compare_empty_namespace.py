"""11 REVIEW B-WR-02: ``compare`` runs the D-15 empty-namespace pre-check for every selected arm
before any arm executes, so a later arm on a never-populated namespace refuses the comparison
before an earlier arm spends a model call and has its envelope discarded.
"""

from __future__ import annotations

import pytest
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.seam.refusals import EmptyNamespaceError, ForeignEngineRefusalError
from databasise.seam.selectors import Selector
from databasise.tests.seam._probes import counting_clients, trace_row_count
from databasise.tests.seam.test_promote import _seed_trace


async def test_a_later_arm_on_a_never_populated_namespace_refuses_before_any_arm_runs(
    synthetic_naive_store,
):
    store_root, workspace = synthetic_naive_store["store_root"], synthetic_naive_store["workspace"]
    promoter = Databasise(store_root=store_root, workspace=workspace)
    for alias, arm in (("cmp-naive", "naive"), ("cmp-hybrid", "hybrid")):
        await promoter.promote(alias, [_seed_trace(store_root, arm)], "human_edit")
    rows_before = trace_row_count(store_root)
    clients = counting_clients(synthetic_naive_store["query_vector"])
    engine = Databasise(store_root=store_root, workspace=workspace, clients=clients)

    # Only chunks is populated: naive could run, hybrid reads the missing entities namespace.
    with pytest.raises(EmptyNamespaceError):
        await engine.compare(
            QueryObject(text="Which films did Ed Wood direct?"),
            [Selector(alias="cmp-naive"), Selector(alias="cmp-hybrid")],
        )

    assert clients["llm"].calls == 0
    assert clients["embedding"].calls == 0
    assert trace_row_count(store_root) == rows_before


async def test_a_half_written_pair_on_a_later_arm_is_store_corrupted_before_any_arm_runs(
    synthetic_naive_store,
):
    """11 REVIEW B3-WR-01: a half-written pair (STOR-08) is corruption, not never populated."""
    store_root, workspace = synthetic_naive_store["store_root"], synthetic_naive_store["workspace"]
    promoter = Databasise(store_root=store_root, workspace=workspace)
    for alias, arm in (("cmp-naive", "naive"), ("cmp-hybrid", "hybrid")):
        await promoter.promote(alias, [_seed_trace(store_root, arm)], "human_edit")
    entities = store_root / workspace / "entities"
    entities.mkdir(parents=True)
    (entities / "vector.meta.json").write_text("{}", encoding="utf-8")
    clients = counting_clients(synthetic_naive_store["query_vector"])
    engine = Databasise(store_root=store_root, workspace=workspace, clients=clients)

    with pytest.raises(ForeignEngineRefusalError) as caught:
        await engine.compare(
            QueryObject(text="Which films did Ed Wood direct?"),
            [Selector(alias="cmp-naive"), Selector(alias="cmp-hybrid")],
        )

    assert caught.value.failure_class == "StoreCorrupted"
    assert clients["llm"].calls == 0
    assert clients["embedding"].calls == 0

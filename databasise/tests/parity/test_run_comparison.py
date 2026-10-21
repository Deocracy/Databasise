"""TOOL-06: ``parity.run_comparison`` reports what happened (15-11).

Every fake below is file-local on purpose: this file is copied alone into a worktree of the pre-fix
commit (fail-first evidence), so it imports only names that exist at the phase base and resolves
anything the phase adds with ``getattr``. No node reaches a provider, ``v1/.venv`` or an env file
other than a stub under ``tmp_path`` (D-24); ``_RESULTS_DIR`` always points into ``tmp_path``
(``parity/.comparison_results/*.json`` are live files).
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from databasise.parity import import_index, run_arm
from databasise.parity import run_comparison as rc
from databasise.parity.import_index import VerificationResult
from databasise.parity.run_comparison import KeywordsResult
from databasise.parity.v1_arm import V1ArmResult


class _Store:
    async def finalize(self) -> None:
        return None


def _scheduled(**overrides):
    base = {
        "nodes": [],
        "results": {"rerank": {"items": [{"id": "c1"}]}, "generate": {}},
        "partial": False,
        "degraded": False,
        "stop_reason": None,
        "degradation_reason": None,
    }
    base.update(overrides)
    return base


@pytest.fixture
def rig(tmp_path, monkeypatch):
    env = tmp_path / "stub.env"
    env.write_text("LLM_MODEL=stub-llm\nEMBEDDING_MODEL=stub-embed\n", encoding="utf-8")
    state = SimpleNamespace(
        scheduled=_scheduled(),
        env=env,
        store_root=tmp_path / "store",
        results_dir=tmp_path / "results",
        v1_calls=[],
        kw_calls=0,
        verify_calls=[],
        build_calls=[],
    )

    async def _verify(**kwargs):
        state.verify_calls.append(kwargs)
        return VerificationResult(status="verified")

    async def _keywords(query, clients, registry):
        state.kw_calls += 1
        return KeywordsResult(high_level_keywords=("h",), low_level_keywords=("l",), cache_served=False)

    async def _run_wiring(parsed, registry, stores, **kwargs):
        return state.scheduled

    def _build_stores(store_root, workspace, resolved=None, *, into=None):
        state.build_calls.append(resolved)
        stores = into if into is not None else {}
        stores["kv"] = _Store()
        return stores

    def _run_v1(mode, query, **kwargs):
        state.v1_calls.append(kwargs)
        return V1ArmResult(
            chunk_ids=("c1",),
            entity_ids=(),
            relation_ids=(),
            answer="a",
            hl_keywords_used=(),
            ll_keywords_used=(),
            wall_clock_seconds=0.0,
        )

    state.verify = _verify
    monkeypatch.setattr(rc, "_RESULTS_DIR", state.results_dir)
    monkeypatch.setattr(rc, "DEFAULT_V1_ENV_PARITY", env)
    monkeypatch.setattr(run_arm, "DEFAULT_V1_ENV_PARITY", env)
    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", state.store_root)
    monkeypatch.setattr(rc, "_run_keywords_live", _keywords)
    monkeypatch.setattr(rc._scheduler, "run_wiring", _run_wiring)
    monkeypatch.setattr(rc, "_build_stores", _build_stores)
    monkeypatch.setattr(rc, "run_v1_arm", _run_v1)
    return state


async def _compare(rig, arm="naive", **overrides):
    kwargs = dict(
        corpus_hash="h",
        store_root=rig.store_root,
        workspace="ws",
        clients={},
        env_path=rig.env,
        verify_fn=rig.verify,
    )
    kwargs.update(overrides)
    return await rc.compare_arm_on_query(arm, "q1", "what is it", **kwargs)


async def _captured(awaitable):
    try:
        return await awaitable
    except BaseException as caught:  # noqa: BLE001 - the fail-first file asserts on the outcome
        return caught


def _main(argv):
    try:
        return rc.main(argv)
    except BaseException as caught:  # noqa: BLE001 - argparse raises SystemExit
        return caught


# --------------------------------------------------------------------------------------------- #
# Task 1: an incomplete decomposed run is inconclusive (D-07) and the CLI exits 3 (D-03)
# --------------------------------------------------------------------------------------------- #


async def test_a_partial_decomposed_run_is_inconclusive_with_no_diff(rig):
    rig.scheduled = _scheduled(partial=True, stop_reason="budget halted", degradation_reason="ran out of tokens")

    record = await _compare(rig)

    assert record.status == "inconclusive"
    assert (record.inconclusive_reason or "").startswith("partial:")
    assert (record.chunk_diff, record.entity_diff, record.relation_diff) == (None, None, None)
    assert record.keyword_variance_band is None
    assert record.decomposed_run_record is not None
    assert record.run_count == 1
    assert rig.v1_calls == []


@pytest.mark.parametrize(
    ("scheduled", "prefix"),
    [
        (_scheduled(degraded=True, stop_reason="reranker down", degradation_reason="reranker down"), "degraded:"),
        ({"cycle": [["a", "b"]]}, "cycle:"),
    ],
    ids=["degraded", "cycle"],
)
async def test_degraded_and_cyclic_runs_are_inconclusive_too(rig, scheduled, prefix):
    rig.scheduled = scheduled

    record = await _compare(rig)

    assert record.status == "inconclusive"
    assert (record.inconclusive_reason or "").startswith(prefix)
    assert (record.chunk_diff, record.entity_diff, record.relation_diff) == (None, None, None)
    assert rig.v1_calls == []


async def test_an_inconclusive_keyword_arm_makes_no_band_calls(rig):
    rig.scheduled = _scheduled(partial=True, stop_reason="budget halted", degradation_reason="ran out of tokens")

    record = await _compare(rig, arm="hybrid")

    assert record.status == "inconclusive"
    assert record.keyword_variance_band is None
    assert rig.kw_calls == 1  # the one pinning call only
    assert rig.v1_calls == []


def test_an_inconclusive_record_exits_three(rig, monkeypatch):
    record = rc._inconclusive_record("naive", "q1", "what is it", "h", "partial: budget halted")

    async def _run_cli(arm_name, query_ids):
        return [record], False

    monkeypatch.setattr(rc, "_run_cli", _run_cli)

    assert _main(["--arm", "naive", "--spend"]) == 3


# --------------------------------------------------------------------------------------------- #
# Task 2: the preflight checks the v1 arm's own index, the guard runs first, run_count is true
# --------------------------------------------------------------------------------------------- #


async def test_the_preflight_sees_the_v1_working_dir_override(rig, tmp_path):
    v1_dir = tmp_path / "v1dir"

    await _compare(rig, v1_working_dir=v1_dir)

    assert [call.get("v1_working_dir") for call in rig.verify_calls] == [v1_dir]
    assert [call.get("working_dir") for call in rig.v1_calls] == [v1_dir]


@pytest.mark.parametrize("runs", [0, 1])
async def test_a_single_variance_run_is_refused_before_any_llm_call(rig, runs):
    outcome = await _captured(_compare(rig, arm="hybrid", keyword_variance_runs=runs))

    assert type(outcome).__name__ == "InsufficientVarianceRunsError"
    assert rig.kw_calls == 0
    assert rig.verify_calls == []
    assert rig.v1_calls == []


@pytest.mark.parametrize("arm", ["naive", "bypass"])
async def test_a_completed_naive_or_bypass_record_has_a_non_zero_run_count(rig, arm):
    record = await _compare(rig, arm=arm)

    assert record.status == "completed"
    assert record.run_count == 2  # the decomposed run and the v1 run


async def test_decomposed_stores_are_built_from_the_resolved_wiring(rig):
    await _compare(rig)

    assert len(rig.build_calls) == 1
    resolved = rig.build_calls[0]
    assert isinstance(resolved, dict)
    assert "nodes" in resolved

"""06-08-PLAN.md Task 2: RIG.md ``## §RUN.1``/``## §RUN.2``'s per-modality isolation properties,
extended from 06-01-PLAN.md's own synthetic proof (``tests/seam/test_store_isolation.py``) to the
real corpus-built indexes.

**Deferred reality (06-08-SUMMARY.md, owner decision `defer-and-record-blocked`).** No real
HippoRAG index has been built against the Phase 3 parity corpus in this environment — Task 1's own
``build_hipporag_index.py`` was written but never invoked (one real invocation requires live
``v1/.env.parity`` credentials and was not authorized during this plan's execution). The tests
below that assert against the real built indexes are guarded by ``_real_hipporag_index_present()``
and skip cleanly on every machine where that build has not run — currently every machine,
including this one — mirroring ``databasise/tests/parity/conftest.py``'s own skip-if-absent
discipline (``v2_parity_store_dir`` etc.) rather than failing collection. The guard check itself
touches only a file's existence — it never constructs a store (which would create an empty
directory as a side effect), so merely collecting this module never mutates the real parity store.

The tests that follow exercise the identical isolation logic
(``preflight``'s directory-disjointness check, ``artifacts_overlap``, the cross-read negative
control) against synthetic, hand-seeded stores instead — no real corpus, no network, no spend —
the sanctioned half of this plan's owner-authorized deviation: testing the harness's own logic
against stubbed/fake data is correct and expected; fabricating evidence of a real run is not.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

import numpy as np
import pytest
from databasise.namespaces import artifacts_overlap
from databasise.parity import import_index
from databasise.parity import run_cross_modality as cross_modality
from databasise.parity.run_cross_modality import (
    _HIPPORAG_VECTOR_NAMESPACES,
    _LIGHTRAG_VECTOR_NAMESPACES,
    _index_recipe_hash,
    _resolved_store_dirs,
    preflight,
)
from databasise.seam.engine import _build_stores
from databasise.stores.vector import FaissVectorStore
from databasise.wirings.resolve import load_wiring, resolve_arm

_WORKSPACE = "cross-modality-isolation-test"


def _real_hipporag_index_present() -> bool:
    """A pure path-existence check — never constructs a store, so collecting this module never
    creates a directory under the real parity store root as a side effect."""
    try:
        workspace = import_index._import_workspace()
    except Exception:
        return False
    index_file = Path(import_index.DEFAULT_STORE_ROOT) / workspace / "hipporag-chunks" / "vector.faiss"
    return index_file.exists()


_skip_without_real_index = pytest.mark.skipif(
    not _real_hipporag_index_present(),
    reason=(
        "no real HippoRAG index built at the parity store root — run "
        "databasise.parity.build_hipporag_index first (06-08-PLAN.md Task 1, deferred per "
        "06-08-SUMMARY.md's owner decision `defer-and-record-blocked`)"
    ),
)


# --------------------------------------------------------------------------------------------- #
# Against the real built indexes — currently always skipped (deferred reality, see module docstring)
# --------------------------------------------------------------------------------------------- #


@_skip_without_real_index
def test_no_store_root_directory_is_written_by_both_arms_against_the_real_built_indexes():
    store_root = import_index.DEFAULT_STORE_ROOT
    workspace = import_index._import_workspace()
    result = preflight(store_root=store_root, workspace=workspace)
    assert result.directories_disjoint


@_skip_without_real_index
def test_artifacts_overlap_is_false_against_the_real_built_indexes():
    store_root = import_index.DEFAULT_STORE_ROOT
    workspace = import_index._import_workspace()
    result = preflight(store_root=store_root, workspace=workspace)
    assert result.artifacts_overlap is False


# --------------------------------------------------------------------------------------------- #
# Synthetic-store tests: the harness's own isolation logic — no real corpus, no spend, no network
# --------------------------------------------------------------------------------------------- #


def test_directories_disjoint_check_against_synthetic_seeded_stores(store_root):
    """Every identifier LightRAG's arm retrieves resolves in a LightRAG namespace and in no
    HippoRAG namespace, and the converse — proven at the directory level, mirroring
    ``test_store_isolation.py``'s own regression pin but exercised through this harness's own
    ``_resolved_store_dirs`` helper rather than a hand-written literal comparison."""
    lightrag_resolved = resolve_arm("naive")
    hipporag_resolved = load_wiring("hipporag")

    lightrag_dirs = _resolved_store_dirs(
        store_root, _WORKSPACE, lightrag_resolved, _LIGHTRAG_VECTOR_NAMESPACES
    )
    hipporag_dirs = _resolved_store_dirs(
        store_root, _WORKSPACE, hipporag_resolved, _HIPPORAG_VECTOR_NAMESPACES
    )

    assert not (lightrag_dirs & hipporag_dirs)


def test_artifacts_overlap_is_false_for_the_two_structurally_different_recipes():
    """RIG.md ## §RUN.2's iff rule, exercised against the two real resolved wirings this plan
    compares — two structurally different recipes sharing no resolved input, so zero overlap is
    the expected, observed result."""
    lightrag_hash = _index_recipe_hash(resolve_arm("naive"))
    hipporag_hash = _index_recipe_hash(load_wiring("hipporag"))

    assert lightrag_hash != hipporag_hash
    assert artifacts_overlap(lightrag_hash, hipporag_hash) is False


def test_artifacts_overlap_is_true_for_two_identical_recipe_hashes():
    """Regression pin: artifacts_overlap is a genuine iff, not a function that always returns
    False — proves the False result above is not vacuous."""
    one_hash = _index_recipe_hash(load_wiring("hipporag"))
    assert artifacts_overlap(one_hash, one_hash) is True


async def test_cross_read_negative_control_against_synthetic_seeded_stores(store_root):
    """Mirrors ``test_store_isolation.py``'s own cross-read refusal proof: seeding one modality's
    graph namespace leaves the other's empty, so the isolation assertions above are not passing
    vacuously on two empty stores (this plan's own acceptance criterion)."""
    lightrag_stores = _build_stores(store_root, _WORKSPACE, resolve_arm("naive"))
    hipporag_stores = _build_stores(store_root, _WORKSPACE, load_wiring("hipporag"))

    await hipporag_stores["graph"].upsert_node("entity:seeded-only-in-hipporag", {})
    await hipporag_stores["graph"].index_done_callback()

    assert await hipporag_stores["graph"].get_all_labels() == ["entity:seeded-only-in-hipporag"]
    assert await lightrag_stores["graph"].get_all_labels() == []

    await lightrag_stores["graph"].upsert_node("lightrag-only-node", {})
    await lightrag_stores["graph"].index_done_callback()

    assert await lightrag_stores["graph"].get_all_labels() == ["lightrag-only-node"]
    # The reverse direction: LightRAG's own write did not leak into HippoRAG's namespace either.
    assert await hipporag_stores["graph"].get_all_labels() == ["entity:seeded-only-in-hipporag"]

    for store in (*lightrag_stores.values(), *hipporag_stores.values()):
        await store.finalize()


# --------------------------------------------------------------------------------------------- #
# TOOL-09 (15-14): the run names the arms it compares, refuses an unusable workspace without
# touching it, keeps a refused run's records, records its queries, and is estimate-only by default.
# Names this plan adds are resolved with getattr so the file collects and fails by assertion on
# the phase base.
# --------------------------------------------------------------------------------------------- #

class _ClientsBuilt(RuntimeError):
    """Sentinel: the run got as far as building provider clients."""


async def _aoutcome(awaitable) -> BaseException | None:
    try:
        await awaitable
    except BaseException as caught:  # noqa: BLE001
        return caught
    return None


async def test_tool09_a_selector_resolving_to_another_arm_is_refused_before_clients(tmp_path, monkeypatch):
    from databasise.seam import selectors
    from databasise.wirings.resolve import wiring_for_name

    real = selectors.resolve_selector
    other_arm = wiring_for_name("local")
    hipporag_capability = list(cross_modality._HIPPORAG_CAPABILITY)

    def fake(selector, *, registry, store_root=None):
        if selector is not None and selector.capability == hipporag_capability:
            return other_arm
        return real(selector, registry=registry, store_root=store_root)

    calls: list[str] = []

    def build_clients(env):
        calls.append("clients")
        raise _ClientsBuilt("clients were built")

    def fake_preflight(**kwargs):
        calls.append("preflight")

    env_file = tmp_path / "env"
    env_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(selectors, "resolve_selector", fake)
    monkeypatch.setattr(cross_modality, "_build_clients", build_clients)
    monkeypatch.setattr(cross_modality, "preflight", fake_preflight)
    monkeypatch.setattr(cross_modality, "_load_env_file", lambda path: {})

    caught = await _aoutcome(
        cross_modality.run_cross_modality(store_root=tmp_path / "store", workspace="w", env_path=env_file)
    )

    assert type(caught).__name__ == "ArmSelectorMismatchError", f"run raised {caught!r}"
    assert calls == [], f"the run went on to {calls} before refusing the mismatched selector"


async def _seed_namespace(store_root: Path, workspace: str, namespace: str) -> None:
    store = FaissVectorStore(namespace=namespace, workspace=workspace, store_root=store_root)
    await store.upsert(["a", "b"], np.eye(2, 4, dtype="float32"), [{"n": 1}, {"n": 2}])
    await store.index_done_callback()
    await store.finalize()


def _listing(root: Path) -> list[tuple[str, int]]:
    return sorted(
        (str(p.relative_to(root)), p.stat().st_size if p.is_file() else -1) for p in root.rglob("*")
    )


async def test_tool09_a_hipporag_only_workspace_is_refused_naming_lightrag_chunks(store_root):
    await _seed_namespace(store_root, _WORKSPACE, "hipporag-chunks")

    try:
        result = cross_modality.preflight(store_root=store_root, workspace=_WORKSPACE)
    except BaseException as caught:  # noqa: BLE001
        assert type(caught).__name__ == "MissingArmIndexError", f"preflight raised {caught!r}"
        # The HippoRAG namespace name also contains "chunks"; the message must name the LightRAG one.
        assert str(caught).replace("hipporag-chunks", "").count("chunks") >= 1, (
            f"the refusal does not name the LightRAG chunks namespace: {caught}"
        )
    else:
        raise AssertionError(f"a HippoRAG-only workspace passed preflight: {result!r}")


async def test_tool09_preflight_leaves_the_store_root_listing_unchanged(store_root):
    # Empty workspace: the refusal must not create the workspace or a namespace directory.
    before = _listing(store_root)
    with contextlib.suppress(BaseException):  # only the listing is under test
        cross_modality.preflight(store_root=store_root, workspace=_WORKSPACE)
    assert _listing(store_root) == before, "preflight changed an empty store root"

    for namespace in ("chunks", "hipporag-chunks"):
        await _seed_namespace(store_root, _WORKSPACE, namespace)
    before = _listing(store_root)
    cross_modality.preflight(store_root=store_root, workspace=_WORKSPACE)
    assert _listing(store_root) == before, "preflight changed a seeded store root"


class _FakeEnvelope:
    """The five attributes and the ``model_dump`` the record reads from a §18.2 envelope."""

    def __init__(self, *, degraded: bool = False):
        self.partial = False
        self.degraded = degraded
        self.stop_reason = None
        self.degradation_reason = "stub degradation" if degraded else None

    def model_dump(self):
        return {"evidence": [{"id": "e1"}], "token_accounting": []}


class _FakeEngine:
    """Stands in for ``Databasise``: query ``degraded_at`` (1-based) degrades the second arm."""

    calls = 0
    degraded_at: int | None = None

    def __init__(self, **kwargs):
        pass

    async def compare(self, query_object, selectors):
        type(self).calls += 1
        degraded = type(self).calls == type(self).degraded_at
        return {"reads_vector": _FakeEnvelope(), "reads_graph+reads_kv": _FakeEnvelope(degraded=degraded)}


def _stub_run(monkeypatch, tmp_path, *, degraded_at: int | None):
    """Point every default the run reaches at a temp path and stub the engine, preflight and clients."""
    env_file = tmp_path / "env"
    env_file.write_text("", encoding="utf-8")
    engine = type("Engine", (_FakeEngine,), {"calls": 0, "degraded_at": degraded_at})
    monkeypatch.setattr(cross_modality, "DEFAULT_V1_ENV_PARITY", env_file)
    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", tmp_path / "store")
    monkeypatch.setattr(import_index, "_import_workspace", lambda: "w")
    monkeypatch.setattr(cross_modality, "_RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(cross_modality, "_load_env_file", lambda path: {})
    monkeypatch.setattr(cross_modality, "_build_clients", lambda env: {})
    monkeypatch.setattr(
        cross_modality,
        "preflight",
        lambda **kwargs: cross_modality.PreflightResult(True, "sha256:a", "sha256:b", False),
    )
    monkeypatch.setattr(cross_modality, "Databasise", engine)
    return env_file


def test_tool09_a_degraded_second_query_leaves_the_first_record_on_disk(tmp_path, monkeypatch, capsys):
    from databasise.parity.corpus import load_snapshot

    _stub_run(monkeypatch, tmp_path, degraded_at=2)
    query_ids = [query.id for query in load_snapshot().queries]

    caught = None
    try:
        code = cross_modality.main(["--spend"])
    except BaseException as exc:  # noqa: BLE001
        caught, code = exc, None
    err = capsys.readouterr().err

    assert caught is None, f"main raised {caught!r}"
    assert code == 1
    assert query_ids[1] in err and "reads_graph+reads_kv" in err, f"the refusal names no query and arm: {err!r}"
    result_path = tmp_path / "results" / "cross_modality.json"
    assert result_path.exists(), "a refused run left no cross_modality.json"
    saved = json.loads(result_path.read_text(encoding="utf-8"))
    assert saved.get("status") == "refused"
    assert [record["query_id"] for record in saved["queries"]] == query_ids[:2]


async def test_tool09_custom_queries_change_the_corpus_hash(tmp_path, monkeypatch):
    from databasise.parity.corpus import CorpusQuery

    env_file = _stub_run(monkeypatch, tmp_path, degraded_at=None)
    run = {"store_root": tmp_path / "store", "workspace": "w", "clients": {}, "env_path": env_file}

    default_record = await cross_modality.run_cross_modality(**run)
    custom = [CorpusQuery(id="custom-1", question="Who?", answer="Them", gold_document_ids=("d1",))]
    custom_record = await cross_modality.run_cross_modality(queries=custom, **run)

    assert custom_record.corpus_hash != default_record.corpus_hash, "custom queries recorded the default corpus_hash"
    assert getattr(custom_record, "queries_hash", None), "the record carries no queries_hash"
    assert getattr(default_record, "queries_hash", None) is None


def test_without_spend_the_cli_is_estimate_only(tmp_path, monkeypatch, capsys):
    _stub_run(monkeypatch, tmp_path, degraded_at=None)

    def forbidden(*args, **kwargs):
        raise AssertionError("work started without --spend")

    for name in ("store_lock", "_build_clients", "run_cross_modality"):
        monkeypatch.setattr(cross_modality, name, forbidden)

    caught = None
    try:
        code = cross_modality.main([])
    except BaseException as exc:  # noqa: BLE001
        caught, code = exc, None
    out = capsys.readouterr().out

    assert caught is None, f"main raised {caught!r}"
    assert code == 0
    assert "mode: estimate-only" in out
    assert not (tmp_path / "results").exists() and not (tmp_path / "store").exists()

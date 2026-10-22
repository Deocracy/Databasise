"""Phase 15 review-fix checks for the eval and floor-store code (15-REVIEW.md, lane B findings)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from databasise.eval import aa_run


class _Judge:
    def __init__(self, text: str) -> None:
        self._text = text

    async def chat(self, messages):
        return SimpleNamespace(text=self._text)


def _score(text: str) -> float:
    return asyncio.run(
        aa_run.score_answer_level(
            llm_client=_Judge(text),
            prompt_template="{question} {gold_answer} {candidate_answer}",
            question_text="q",
            gold_answer="g",
            candidate_answer="c",
        )
    )


@pytest.mark.parametrize(
    ("text", "score"),
    [
        ("CORRECT", 1.0),
        ("CORRECT.", 1.0),
        ("**CORRECT**", 1.0),
        ("Verdict: CORRECT", 1.0),
        ("**Verdict:** PARTIAL", 0.5),
        ("INCORRECT - the candidate names the wrong year.", 0.0),
        ("CORRECT. The candidate is correct on every point.", 1.0),
    ],
)
def test_judge_verdict_parses_a_leading_verdict(text, score):
    """B-CR-01: the TOOL-12 forms still parse."""
    assert _score(text) == score


@pytest.mark.parametrize(
    "text",
    [
        "not correct",
        "Partially correct",
        "The answer is not CORRECT; verdict: INCORRECT",
        "- CORRECT — matches\n- PARTIAL — some\n- INCORRECT — wrong\nVerdict: INCORRECT",
        "CORRECT? No, INCORRECT.",
    ],
)
def test_judge_verdict_refuses_a_negated_or_echoed_verdict(text):
    """B-CR-01: a negation, a partial word or an echoed option list never scores as a verdict."""
    with pytest.raises(aa_run.UnparseableJudgeVerdictError):
        _score(text)


def _stub_spend_path(monkeypatch, tmp_path):
    """Patch every client, engine and store constructor on aa_run's --spend path to a stub."""
    monkeypatch.setattr(aa_run, "_EVAL_INGEST_STORE_ROOT", tmp_path / "eval-store")
    monkeypatch.setattr(aa_run, "_load_env_file", lambda path: {})
    monkeypatch.setattr(aa_run, "_build_clients", lambda env: {})
    monkeypatch.setattr(aa_run, "Databasise", lambda **kwargs: SimpleNamespace(store_root=tmp_path))
    monkeypatch.setattr(aa_run, "MultiNamespaceVectorStore", lambda **kwargs: None)


def test_a_repeated_family_is_estimated_and_run_once(monkeypatch, tmp_path, capsys):
    """B-WR-01: `--family X --family X` runs X once, matching the estimate."""
    _stub_spend_path(monkeypatch, tmp_path)
    seen: list[tuple[str, ...]] = []

    async def record_families(*, families, **kwargs):
        seen.append(tuple(families))
        raise aa_run.NoMintedBundleError("stop after recording the families")

    monkeypatch.setattr(aa_run, "_calibrate_all", record_families)
    assert aa_run.main(["--family", "answer_level", "--family", "answer_level", "--spend"]) == 1
    assert seen == [("answer_level",)]


def _floor_row(**overrides):
    from databasise.seam.floors_store import FloorRow

    fields = dict(
        wiring_instance_hash="h1",
        bundle_at_v="bundle@v1",
        tier="T1",
        metric="gold_passage_recall",
        determinism_setting="d",
        concurrency_setting="c",
        floor=0.1,
        n_questions=3,
        n_resamples=10,
        seed=1,
        created_at="2026-10-21T00:00:00+00:00",
    )
    return FloorRow(**{**fields, **overrides})


def test_floor_store_reads_create_no_side_files(tmp_path):
    """B-WR-02: any_floor and lookup on a WAL floors.db leave only floors.db behind."""
    from databasise.seam.floors_store import FloorStore

    store = FloorStore(tmp_path)
    store.record(_floor_row())
    assert sorted(p.name for p in tmp_path.iterdir()) == ["floors.db"]
    assert store.any_floor() is True
    assert store.lookup("h1") == [_floor_row()]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["floors.db"]


def test_floor_store_reads_a_floor_in_a_read_only_directory(tmp_path):
    """B-WR-02: an open failure is never read as "no floor"; a read-only root still reads its floor."""
    from databasise.seam.floors_store import FloorStore

    store = FloorStore(tmp_path)
    store.record(_floor_row())
    tmp_path.chmod(0o555)
    try:
        assert store.any_floor() is True
        assert len(store.lookup("h1")) == 1
    finally:
        tmp_path.chmod(0o755)


def test_floor_store_refuses_a_wal_without_its_shm(tmp_path):
    """B-WR-02: a fault other than a missing table propagates instead of returning "no floor"."""
    import sqlite3

    from databasise.seam.floors_store import FloorStore

    store = FloorStore(tmp_path)
    store.record(_floor_row())
    (tmp_path / "floors.db-wal").write_bytes(b"\0" * 64)
    with pytest.raises(sqlite3.OperationalError):
        store.any_floor()
    with pytest.raises(sqlite3.OperationalError):
        store.lookup("h1")


def _calibration_result(metric: str, *, wiring_instance_hash: str | None = "h1"):
    from databasise.eval.calibration import CalibrationResult, NullIdentity

    identity = NullIdentity(
        bundle_at_v="bundle@v1", tier="T1", metric=metric, determinism_setting="d", concurrency_setting="c"
    )
    return CalibrationResult(
        identity=identity, floor=0.1, n_questions=3, n_resamples=10, seed=1, wiring_instance_hash=wiring_instance_hash
    )


def test_floor_store_record_many_writes_all_rows_or_none(tmp_path):
    """B-WR-03: a failing row rolls back the rows before it."""
    from databasise.seam.floors_store import FloorStore

    store = FloorStore(tmp_path)
    with pytest.raises(Exception):
        store.record_many([_floor_row(), _floor_row(metric="m2", floor=object())])
    assert store.lookup("h1") == []


@pytest.mark.parametrize("unkeyable", [False, True])
def test_aa_run_prints_its_result_before_a_persist_refusal(unkeyable, monkeypatch, tmp_path, capsys):
    """B-WR-03: a refusal while persisting floors still prints the spent run's result, one stderr line, exit 1."""
    import json
    import sqlite3

    from databasise.seam.floors_store import FloorStore

    _stub_spend_path(monkeypatch, tmp_path)
    results = {
        "gold_passage": _calibration_result("gold_passage_recall"),
        "answer_level": _calibration_result("answer_level_correctness", wiring_instance_hash=None if unkeyable else "h1"),
    }

    async def calibrated(**kwargs):
        return results

    def failing_write(self, rows):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(aa_run, "_calibrate_all", calibrated)
    monkeypatch.setattr(FloorStore, "record_many", failing_write)
    assert aa_run.main(["--spend"]) == 1
    captured = capsys.readouterr()
    printed = json.loads(captured.out[captured.out.rindex('{\n  "bundle_version"') :])
    assert set(printed["results_by_family"]) == set(results)
    err_lines = captured.err.strip().splitlines()
    assert len(err_lines) == 1
    expected = "UnkeyableFloorError: " if unkeyable else "FloorPersistError: "
    assert err_lines[0].startswith(expected)


class _CountingEngine:
    def __init__(self, store_root):
        self.store_root = store_root
        self.queries = 0

    async def query(self, query_object, selector=None):
        self.queries += 1
        return SimpleNamespace(partial=False, degraded=False, trace_token="t", evidence=[], answer="a")


class _CountingJudge:
    calls = 0

    async def chat(self, messages):
        self.calls += 1
        return SimpleNamespace(text="CORRECT")


@pytest.mark.parametrize("cache_hit", [None, True])
def test_calibration_stops_at_the_first_question_a_bypass_check_refuses(cache_hit, monkeypatch, tmp_path):
    """B-WR-04: a node without a verified cache bypass refuses before any judge call or second query."""
    from databasise.eval.bundle import load_bundle
    from databasise.eval.calibration import UnusableFloorError

    class _Traces:
        def __init__(self, root):
            pass

        def resolve(self, token):
            return {"nodes": [{"node_id": "n1", "cache_hit": cache_hit}], "wiring_instance_hash": "h1"}

    monkeypatch.setattr(aa_run, "TraceStore", _Traces)
    bundle = load_bundle(aa_run._COMMITTED_BUNDLE_ROOT, aa_run._default_bundle_version(aa_run._COMMITTED_BUNDLE_ROOT))
    engine, judge = _CountingEngine(tmp_path), _CountingJudge()
    with pytest.raises(UnusableFloorError, match="run_a node 'n1'"):
        asyncio.run(
            aa_run.calibrate_family(
                engine=engine, bundle=bundle, split_name="dev", family_name="answer_level", llm_client=judge
            )
        )
    assert (engine.queries, judge.calls) == (1, 0)


def _copied_bundle_root(tmp_path):
    import shutil

    root = tmp_path / "eval-bundles"
    shutil.copytree(aa_run._COMMITTED_BUNDLE_ROOT, root)
    return root


def test_a_truncated_usage_line_is_a_named_refusal(monkeypatch, tmp_path, capsys):
    """B-WR-06: a cut-short usage.jsonl append refuses by name, and aa_run's estimate exits 1 with one line."""
    from databasise.eval.bundle import CorruptUsageLogError, load_bundle

    root = _copied_bundle_root(tmp_path)
    version = aa_run._default_bundle_version(root)
    with (root / version / "usage.jsonl").open("a", encoding="utf-8") as f:
        f.write('{"kind": "holdout_re')
    with pytest.raises(CorruptUsageLogError, match="is not JSON"):
        load_bundle(root, version)

    monkeypatch.setattr(aa_run, "_COMMITTED_BUNDLE_ROOT", root)
    assert aa_run.main([]) == 1
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert err_lines[0].startswith("CorruptUsageLogError: ")

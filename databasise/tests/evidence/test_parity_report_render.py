"""15-08 (TOOL-14): ``evidence/parity_report.py`` renders only the states it reads from
``parity_results``, refuses malformed inputs by name, shows who recorded each cause, and cites
planning paths that exist.

Every case builds synthetic ``parity_results`` and ``human_findings.json`` in ``tmp_path`` and
retargets ``RESULTS_DIR`` / ``HUMAN_FINDINGS_PATH`` with ``monkeypatch.setattr`` (the same route
``tests/parity/test_parity_evidence.py`` uses). Nothing here touches a provider or a secret.

Names this plan adds are resolved with ``getattr`` and exceptions are captured and asserted on, so
the file collects and fails by ``AssertionError`` against the pre-change module.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from databasise.evidence import parity_report

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARMS = ("naive", "bypass", "hybrid", "local", "global")
_GRAPH_ARMS = ("hybrid", "local", "global")


def _diff(*ids: str) -> dict:
    return {
        "decomposed_ids": [],
        "original_ids": list(ids),
        "symmetric_difference": list(ids),
        "ranking_agreement": 1.0,
        "first_disagreement_position": 0 if ids else None,
    }


def _record(arm: str, query_id: str) -> dict:
    """A completed, non-degraded record with an empty diff on every field its arm measures."""
    record: dict = {
        "status": "completed",
        "arm": arm,
        "query_id": query_id,
        "query": "a question",
        "corpus_hash": "abc123",
        "determinism_setting": "cache-bypassed",
        "concurrency_setting": "sequential",
        "run_count": 1,
        "resolved_model_identities": {
            "decomposed_generate": "m",
            "original_arm_llm_model": "m",
            "original_arm_embedding_model": "e",
        },
        "inconclusive_reason": None,
        "chunk_diff": None,
        "entity_diff": None,
        "relation_diff": None,
        "keyword_variance_band": None,
        "decomposed_run_record": {
            "degraded": False,
            "degradation_reason": None,
            "stop_reason": None,
            "nodes": [],
        },
        "original_arm_result": {"answer": "an answer"},
        "original_arm_instrumentation": "harness-external",
    }
    if arm == "bypass":
        record["retrieval_note"] = "no retrieval to compare"
    elif arm == "naive":
        record["chunk_diff"] = _diff()
    else:
        record["chunk_diff"] = _diff()
        record["entity_diff"] = _diff()
        record["relation_diff"] = _diff()
    return record


def _inconclusive(arm: str, query_id: str) -> dict:
    record = _record(arm, query_id)
    for key in ("chunk_diff", "entity_diff", "relation_diff", "keyword_variance_band"):
        record[key] = None
    record.pop("retrieval_note", None)
    record.update(
        status="inconclusive",
        resolved_model_identities={},
        inconclusive_reason="v1/.env.parity is absent",
    )
    return record


def _audit(arm: str, status: str = "completed") -> dict:
    return {
        "arm": arm,
        "command": "x",
        "exit_code": 0 if status == "completed" else 1,
        "status": status,
        "outcome": "clean" if status == "completed" else "environment_precondition_failed",
        "reason": "synthetic",
        "matched_count": 1,
        "no_touch_count": 0,
        "over_declared_count": 0,
        "rows": [],
    }


def _build(tmp_path, monkeypatch, *, queries=("q1", "q2"), tweak=None, causes=(), spotchecks=()):
    """Write a five-arm synthetic result set, apply ``tweak(arm, records)`` per arm, point the
    module at it, and return ``(results_dir, findings_path)``."""
    results = tmp_path / "results"
    results.mkdir()
    for arm in _ARMS:
        records = [_record(arm, query_id) for query_id in queries]
        if tweak is not None:
            tweak(arm, records)
        (results / f"{arm}-comparison.json").write_text(json.dumps(records), encoding="utf-8")
        status = "completed" if all(r["status"] == "completed" for r in records) else "inconclusive"
        (results / f"{arm}-storage-audit.json").write_text(
            json.dumps(_audit(arm, status)), encoding="utf-8"
        )
    findings = tmp_path / "human_findings.json"
    findings.write_text(
        json.dumps({"declared_causes": list(causes), "answer_spotchecks": list(spotchecks)}),
        encoding="utf-8",
    )
    monkeypatch.setattr(parity_report, "RESULTS_DIR", results)
    monkeypatch.setattr(parity_report, "HUMAN_FINDINGS_PATH", findings)
    return results, findings


def _naive_chunk_excursion(arm, records):
    if arm == "naive":
        records[0]["chunk_diff"] = _diff("a-chunk")


def _cause(recorded_by: str, cause: str = "v1 keeps a longer tail than the top_k cutoff") -> dict:
    return {
        "arm": "naive",
        "query_id": "q1",
        "field": "chunk_diff",
        "symmetric_difference": ["a-chunk"],
        "cause": cause,
        "recorded_by": recorded_by,
        "recorded_at": "2026-10-21",
    }


def _document() -> str:
    return parity_report.render_deviations_document(parity_report._collect_deviations())


# --------------------------------------------------------------------------------------------- #
# Task 1 (tracer): the deviations record
# --------------------------------------------------------------------------------------------- #


def test_all_uncaused_excursions_never_render_zero_declared_deviations(tmp_path, monkeypatch):
    _build(tmp_path, monkeypatch, tweak=_naive_chunk_excursion)

    text = _document()

    assert "Zero declared deviations" not in text
    assert "naive" in text and "q1" in text and "chunk_diff" in text


def test_an_ai_recorded_cause_shows_recorded_by(tmp_path, monkeypatch):
    _build(
        tmp_path,
        monkeypatch,
        tweak=_naive_chunk_excursion,
        causes=[_cause("claude-agent")],
    )

    text = _document()

    assert "claude-agent" in text


# --------------------------------------------------------------------------------------------- #
# Task 2: run state, verdict, counts, spot-checks, escaping and the named input refusal
# --------------------------------------------------------------------------------------------- #


def _only_naive_completed(arm, records):
    if arm != "naive":
        records[:] = [_inconclusive(arm, r["query_id"]) for r in records]


def test_the_mixed_state_has_its_own_text(tmp_path, monkeypatch):
    _build(tmp_path, monkeypatch, tweak=_only_naive_completed)

    text = parity_report.render_markdown()

    assert parity_report._run_state() == "mixed"
    assert "Every one of the five arms" not in text
    assert "mixed" in text.lower()


def test_a_degraded_naive_arm_never_reads_all_five_completed(tmp_path, monkeypatch):
    def degrade_naive(arm, records):
        if arm == "naive":
            for record in records:
                record["decomposed_run_record"]["degraded"] = True
                record["decomposed_run_record"]["degradation_reason"] = "crashed"

    _build(tmp_path, monkeypatch, tweak=degrade_naive)

    guidance = parity_report._render_spotcheck_arm_guidance()
    verdict = parity_report._render_verdict()

    assert "All five arms completed" not in guidance
    assert "All five arms completed" not in verdict
    assert "naive" in guidance and "naive" in verdict


def test_one_query_with_empty_ids_never_claims_non_empty_on_every_query(tmp_path, monkeypatch):
    def one_query_differs(arm, records):
        if arm in _GRAPH_ARMS:
            records[0]["entity_diff"] = _diff("e1")

    _build(tmp_path, monkeypatch, tweak=one_query_differs)

    text = parity_report.render_deviations_markdown([])

    assert "non-empty on every query" not in text
    assert "3 of 6" in text


def test_the_corpus_size_comes_from_the_results(tmp_path, monkeypatch):
    _build(tmp_path, monkeypatch, queries=("q1", "q2", "q3"))

    text = parity_report.render_markdown()

    assert "3 queries" in text
    assert "2 queries" not in text
    assert "### `q3`" in text


def test_two_spot_checks_for_one_query_with_different_arms_both_appear(tmp_path, monkeypatch):
    def spot(arm, judgment, notes):
        return {
            "query_id": "q1",
            "arm": arm,
            "judgment": judgment,
            "notes": notes,
            "recorded_by": "owner",
            "recorded_at": "2026-10-21",
        }

    _build(
        tmp_path,
        monkeypatch,
        spotchecks=[spot("hybrid", "match", "NOTE-HYBRID"), spot("local", "no-match", "NOTE-LOCAL")],
    )

    text = parity_report._render_answer_spotcheck()

    assert "NOTE-HYBRID" in text
    assert "NOTE-LOCAL" in text


def test_an_exact_duplicate_spot_check_is_refused_by_name(tmp_path, monkeypatch):
    entry = {
        "query_id": "q1",
        "arm": "hybrid",
        "judgment": "match",
        "notes": "n",
        "recorded_by": "owner",
        "recorded_at": "2026-10-21",
    }
    _build(tmp_path, monkeypatch, spotchecks=[entry, dict(entry, notes="again")])

    caught = None
    try:
        parity_report._render_answer_spotcheck()
    except BaseException as exc:  # noqa: BLE001 - the type is the assertion
        caught = exc

    assert type(caught).__name__ == "DuplicateSpotCheckError"


def _capture(fn):
    try:
        fn()
    except BaseException as exc:  # noqa: BLE001 - the type is the assertion
        return exc
    return None


def test_malformed_json_and_a_missing_field_raise_the_named_refusal(tmp_path, monkeypatch):
    results, findings = _build(tmp_path, monkeypatch)
    entry_without_field = {
        "arm": "naive",
        "query_id": "q1",
        "symmetric_difference": ["a-chunk"],
        "cause": "a named cause",
    }
    wrong = []

    def expect(label, fn, needle):
        caught = _capture(fn)
        if type(caught).__name__ != "ParityRecordFormatError" or needle not in str(caught):
            wrong.append((label, type(caught).__name__, str(caught)[:120]))

    # (a) a truncated comparison file
    good = (results / "naive-comparison.json").read_text(encoding="utf-8")
    (results / "naive-comparison.json").write_text(good[: len(good) // 2], encoding="utf-8")
    expect("check_results/truncated", parity_report.check_results, "naive-comparison.json")
    expect("collect/truncated", parity_report._collect_deviations, "naive-comparison.json")
    (results / "naive-comparison.json").write_text(good, encoding="utf-8")

    # (b) a declared_causes entry without 'field'
    findings.write_text(
        json.dumps({"declared_causes": [entry_without_field], "answer_spotchecks": []}),
        encoding="utf-8",
    )
    expect("check_results/no-field", parity_report.check_results, "field")
    expect("collect/no-field", parity_report._collect_deviations, "field")

    # (c) a malformed human_findings.json
    findings.write_text('{"declared_causes": [', encoding="utf-8")
    expect("check_results/bad-findings", parity_report.check_results, "human_findings.json")
    expect("collect/bad-findings", parity_report._collect_deviations, "human_findings.json")

    assert wrong == []


def test_a_cause_with_a_pipe_and_a_newline_keeps_the_row_count(tmp_path, monkeypatch):
    _build(
        tmp_path,
        monkeypatch,
        tweak=_naive_chunk_excursion,
        causes=[_cause("claude-agent", cause="first | second\nthird")],
    )

    text = _document()

    rows = [line for line in text.splitlines() if line.startswith("| naive | q1 |")]
    assert len(rows) == 1
    assert "third" in rows[0]
    # six columns -> seven unescaped pipes -> eight parts
    assert len(re.split(r"(?<!\\)\|", rows[0])) == 8


def test_recorded_by_appears_in_the_verdict(tmp_path, monkeypatch):
    _build(
        tmp_path,
        monkeypatch,
        tweak=_naive_chunk_excursion,
        causes=[_cause("claude-agent")],
    )

    verdict = parity_report._render_verdict()

    assert "claude-agent" in verdict


def test_main_check_results_refuses_a_malformed_file_with_one_line_and_exit_1(
    tmp_path, monkeypatch, capsys
):
    results, _findings = _build(tmp_path, monkeypatch)
    (results / "naive-comparison.json").write_text('[{"status": ', encoding="utf-8")

    code = parity_report.main(["--check-results"])

    err = capsys.readouterr().err.strip().splitlines()
    assert code == 1
    assert len(err) == 1 and err[0].startswith("ParityRecordFormatError:")


# --------------------------------------------------------------------------------------------- #
# Task 3: every rendered and committed .planning path resolves
# --------------------------------------------------------------------------------------------- #


def test_every_planning_path_resolves():
    evidence = _REPO_ROOT / "databasise" / "evidence"
    files = [
        evidence / "parity_report.py",
        evidence / "DECLARED-DEVIATIONS.md",
        evidence / "PARITY-EVIDENCE.md",
        evidence / "FALSIFIER-5-EVIDENCE.md",
    ]
    checked = 0
    missing = []
    for file in files:
        for match in re.findall(r"\.planning/[A-Za-z0-9_./-]*", file.read_text(encoding="utf-8")):
            path = match.rstrip(".,;:")
            checked += 1
            if not (_REPO_ROOT / path).exists():
                missing.append(f"{file.name}: {path}")

    assert checked >= 10
    assert sorted(set(missing)) == []

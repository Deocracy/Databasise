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

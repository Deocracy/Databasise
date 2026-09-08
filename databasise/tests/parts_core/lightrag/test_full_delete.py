"""05-03-PLAN.md Task 1: the delete port — a second registration, not a second operation on the
first. Proves ``lightrag/full-delete@0.1.0`` is a real, separately-admitted opaque Part
(CONTRACT §19.6's separate-port rule) and that the driver script's ``delete``/``entities``
branches speak the protocol Task 1's own action text specifies — against the stub driver for the
bulk of the suite, plus one real-interpreter smoke test guarded by ``pytest.mark.skipif``,
mirroring ``test_full_ingest.py``'s own shape exactly.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

from databasise.foreign import run_corpus_op
from databasise.parts.registry import PartRegistry, UnadmittedOpaquePartError
from databasise.parts_core.declared_only import LIGHTRAG_FULL_DELETE_PART, LIGHTRAG_FULL_INGEST_PART
from databasise.validator.execution_mode import derive_execution_mode, host

_STUB_DRIVER = Path(__file__).resolve().parents[2] / "fixtures" / "v1_corpus_driver_stub.py"
_V1_VENV_PYTHON = Path(__file__).resolve().parents[4] / "v1" / ".venv" / "bin" / "python"
_V1_CORPUS_DRIVER_SCRIPT = (
    Path(__file__).resolve().parents[4] / "databasise" / "foreign" / "v1_corpus_driver_script.py"
)
_V1_ENV_PARITY = Path(__file__).resolve().parents[4] / "v1" / ".env.parity"


def test_the_delete_part_declares_mutates_store_and_the_ingest_part_declares_writes_artifact():
    assert "mutates_store" in LIGHTRAG_FULL_DELETE_PART.effects
    assert "writes_artifact" not in LIGHTRAG_FULL_DELETE_PART.effects
    assert "writes_artifact" in LIGHTRAG_FULL_INGEST_PART.effects
    assert "mutates_store" not in LIGHTRAG_FULL_INGEST_PART.effects
    assert LIGHTRAG_FULL_DELETE_PART.name_at_version != LIGHTRAG_FULL_INGEST_PART.name_at_version


def test_the_delete_part_registers_no_artifact_scope():
    assert LIGHTRAG_FULL_DELETE_PART.artifact_scope is None


def test_derive_execution_mode_returns_subprocess_and_host_accepts_the_declared_ceiling():
    mode = derive_execution_mode(LIGHTRAG_FULL_DELETE_PART.effects, LIGHTRAG_FULL_DELETE_PART.kind)
    assert mode == "subprocess"
    host(
        mode,
        wall_clock_ceiling_seconds=LIGHTRAG_FULL_DELETE_PART.admission.wall_clock_ceiling_seconds,
    )


def test_registering_the_delete_part_with_no_admission_record_raises_unadmitted_opaque_part_error():
    unadmitted = dataclasses.replace(LIGHTRAG_FULL_DELETE_PART, admission=None)
    registry = PartRegistry(seed_tracer_parts=False)
    with pytest.raises(UnadmittedOpaquePartError):
        registry.register(unadmitted)


def test_the_delete_admission_record_carries_its_own_eleven_verdicts_not_the_ingest_records():
    assert len(LIGHTRAG_FULL_DELETE_PART.admission.verdicts) == 11
    assert LIGHTRAG_FULL_DELETE_PART.admission is not LIGHTRAG_FULL_INGEST_PART.admission
    assert LIGHTRAG_FULL_DELETE_PART.admission.part_name_at_version == "lightrag/full-delete@0.1.0"


def test_the_stub_drivers_delete_branch_echoes_the_configured_status(tmp_path):
    result = run_corpus_op(
        "delete",
        {"doc_id": "deadbeef", "_stub_status": "not_found"},
        timeout=5.0,
        interpreter=Path(sys.executable),
        driver_script=_STUB_DRIVER,
        working_dir=tmp_path,
    )
    assert result["status"] == "not_found"
    assert result["doc_id"] == "deadbeef"


def test_the_stub_drivers_delete_branch_defaults_to_success(tmp_path):
    result = run_corpus_op(
        "delete",
        {"doc_id": "deadbeef"},
        timeout=5.0,
        interpreter=Path(sys.executable),
        driver_script=_STUB_DRIVER,
        working_dir=tmp_path,
    )
    assert result["status"] == "success"


def test_the_stub_drivers_entities_branch_echoes_the_configured_entity_map(tmp_path):
    entity_map = {"Ed Wood": ["chunk-1", "chunk-2"]}
    result = run_corpus_op(
        "entities",
        {"doc_id": "ed_wood", "_stub_entities": entity_map},
        timeout=5.0,
        interpreter=Path(sys.executable),
        driver_script=_STUB_DRIVER,
        working_dir=tmp_path,
    )
    assert result["entities"] == entity_map


@pytest.mark.skipif(not _V1_VENV_PYTHON.exists(), reason="v1/.venv/bin/python not built")
def test_the_real_driver_scripts_delete_branch_returns_not_found_for_an_unknown_doc_id(tmp_path):
    """Proves the real leaf script's ``delete`` branch speaks the stdin/stdout protocol against a
    fresh, empty working dir — an unknown ``doc_id`` yields v1's own ``not_found`` status rather
    than a non-zero exit, without paying for a real LLM call (a doc-status miss short-circuits
    before any extraction/rebuild is attempted)."""
    result = run_corpus_op(
        "delete",
        {"doc_id": "no-such-document-ever-ingested"},
        timeout=120.0,
        interpreter=_V1_VENV_PYTHON,
        driver_script=_V1_CORPUS_DRIVER_SCRIPT,
        env_path=_V1_ENV_PARITY,
        working_dir=tmp_path / "corpus_working_dir",
    )
    assert result["status"] == "not_found"

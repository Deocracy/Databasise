"""05-01-PLAN.md Task 2: the enforcement half of §8 admission — a record that lies is refused
rather than filed. One test per ``<behavior>`` bullet; every refusal test asserts on the raised
exception's own named attribute, never on message text.
"""

from __future__ import annotations

import dataclasses

import pydantic
import pytest
from databasise.parts.admission import (
    MANIFEST_SOURCE_CODE_INSPECTED,
    AdmissionConditionMissingError,
    AdmissionRecord,
    ConditionVerdict,
    ForbiddenSharedScopeError,
    SelfReportedManifestError,
    cross_check_conditions,
    validate_admission,
)
from databasise.parts.registry import PartRegistry, UnadmittedOpaquePartError, default_registry
from databasise.parts.schema import Part
from databasise.parts_core.declared_only import (
    CODEBASE_MEMORY_MCP_PART,
    LIGHTRAG_FULL_INGEST_PART,
)
from databasise.seam.query import QueryObject
from databasise.seam.selectors import _is_default_eligible
from databasise.wirings.resolve import resolve_arm

_VALID_VERDICTS = tuple(
    ConditionVerdict(condition=i, verdict="satisfied", evidence=f"evidence for condition {i}")
    for i in range(1, 12)
)


def _valid_admission_record(**overrides) -> AdmissionRecord:
    defaults = dict(
        part_name_at_version="test/opaque-part@1.0.0",
        entry_path="subprocess",
        storage="machine",
        wall_clock_ceiling_seconds=60.0,
        wall_clock_ceiling_basis="test fixture",
        feed_tier="document",
        ttl_days=1,
        network_namespace="denied-by-construction",
        environment_hash="sha256:" + "a" * 64,
        manifest_source=MANIFEST_SOURCE_CODE_INSPECTED,
        verdicts=_VALID_VERDICTS,
    )
    defaults.update(overrides)
    return AdmissionRecord(**defaults)


def _opaque_part(**overrides) -> Part:
    defaults = dict(
        name_at_version="test/opaque-part@1.0.0",
        kind="opaque",
        structural_depth="opaque",
        effects=[],
        upstream_ref=None,
        body=lambda ctx: None,
        artifact_scope="quarantined",
    )
    defaults.update(overrides)
    return Part(**defaults)


def test_registering_an_unadmitted_executable_opaque_part_raises_naming_the_part():
    part = _opaque_part(admission=None)
    with pytest.raises(UnadmittedOpaquePartError) as exc_info:
        PartRegistry(seed_tracer_parts=False).register(part)
    assert exc_info.value.name_at_version == "test/opaque-part@1.0.0"


def test_registering_the_same_opaque_part_with_a_valid_record_registers_cleanly():
    part = _opaque_part(admission=_valid_admission_record())
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(part)
    assert registry.get("test/opaque-part@1.0.0") is part


def test_registering_a_declaration_only_opaque_part_still_succeeds():
    """``CODEBASE_MEMORY_MCP_PART`` (body=None, no admission) must keep loading in
    ``default_registry()`` until plan 05-06 admits it."""
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(CODEBASE_MEMORY_MCP_PART)
    assert registry.get(CODEBASE_MEMORY_MCP_PART.name_at_version) is CODEBASE_MEMORY_MCP_PART


def test_validate_admission_raises_forbidden_shared_scope_for_shared_and_accepts_quarantined():
    shared_part = _opaque_part(artifact_scope="shared")
    record = _valid_admission_record()
    with pytest.raises(ForbiddenSharedScopeError) as exc_info:
        validate_admission(shared_part, record)
    assert exc_info.value.artifact_scope == "shared"

    quarantined_part = _opaque_part(artifact_scope="quarantined")
    validate_admission(quarantined_part, record)  # does not raise


def test_validate_admission_raises_self_reported_manifest_error_for_any_non_code_inspected_source():
    part = _opaque_part()
    record = _valid_admission_record(manifest_source="engine-self-report")
    with pytest.raises(SelfReportedManifestError) as exc_info:
        validate_admission(part, record)
    assert exc_info.value.manifest_source == "engine-self-report"


def test_validate_admission_raises_condition_missing_for_ten_verdicts_duplicate_and_blank_evidence():
    part = _opaque_part()

    ten_verdicts = _valid_admission_record(verdicts=_VALID_VERDICTS[:10])
    with pytest.raises(AdmissionConditionMissingError):
        validate_admission(part, ten_verdicts)

    duplicated = _valid_admission_record(
        verdicts=_VALID_VERDICTS[:10] + (_VALID_VERDICTS[9],)
    )
    with pytest.raises(AdmissionConditionMissingError):
        validate_admission(part, duplicated)

    blank_evidence = _valid_admission_record(
        verdicts=_VALID_VERDICTS[:10]
        + (ConditionVerdict(condition=11, verdict="satisfied", evidence="   "),)
    )
    with pytest.raises(AdmissionConditionMissingError):
        validate_admission(part, blank_evidence)


def test_is_default_eligible_returns_false_for_corpus_ingest_and_true_for_the_naive_arm():
    """§8 condition 7: resolves the real ``corpus-ingest.json`` wiring and the real ``naive`` arm
    through the same ``_is_default_eligible`` call this module's own condition-7 admission check
    uses — fails if a later change makes the opaque ingest node default-eligible."""
    registry = default_registry()

    import json
    from pathlib import Path

    corpus_ingest_path = (
        Path(__file__).resolve().parents[2] / "wirings" / "lightrag" / "corpus-ingest.json"
    )
    corpus_ingest = json.loads(corpus_ingest_path.read_text(encoding="utf-8"))

    assert _is_default_eligible(corpus_ingest, registry) is False
    assert _is_default_eligible(resolve_arm("naive"), registry) is True


def test_cross_check_conditions_raises_when_the_opaque_provides_node_is_default_eligible():
    """Condition 7 via ``cross_check_conditions`` itself, not just the raw selector call above —
    proves the wrapper actually enforces what it claims to."""
    registry = default_registry()
    import json
    from pathlib import Path

    corpus_ingest_path = (
        Path(__file__).resolve().parents[2] / "wirings" / "lightrag" / "corpus-ingest.json"
    )
    corpus_ingest = json.loads(corpus_ingest_path.read_text(encoding="utf-8"))

    # The real corpus-ingest wiring is correctly excluded — this must NOT raise.
    cross_check_conditions(
        LIGHTRAG_FULL_INGEST_PART,
        LIGHTRAG_FULL_INGEST_PART.admission,
        registry=registry,
        resolved_wiring=corpus_ingest,
    )

    # A wiring whose provides node is NOT opaque-depth (the naive arm) must raise condition 7.
    with pytest.raises(AdmissionConditionMissingError):
        cross_check_conditions(
            LIGHTRAG_FULL_INGEST_PART,
            LIGHTRAG_FULL_INGEST_PART.admission,
            registry=registry,
            resolved_wiring=resolve_arm("naive"),
        )


def test_cross_check_conditions_raises_condition_10_for_a_shared_scope_part():
    registry = default_registry()
    shared_part = dataclasses.replace(LIGHTRAG_FULL_INGEST_PART, artifact_scope="shared")
    import json
    from pathlib import Path

    corpus_ingest_path = (
        Path(__file__).resolve().parents[2] / "wirings" / "lightrag" / "corpus-ingest.json"
    )
    corpus_ingest = json.loads(corpus_ingest_path.read_text(encoding="utf-8"))

    with pytest.raises(AdmissionConditionMissingError):
        cross_check_conditions(
            shared_part,
            LIGHTRAG_FULL_INGEST_PART.admission,
            registry=registry,
            resolved_wiring=corpus_ingest,
        )


def test_query_object_has_no_as_of_member_and_rejects_one_at_construction():
    """§8 condition 11, satisfied structurally: ``QueryObject`` declares no ``as_of`` member (so
    ``cross_check_conditions`` reads ``QueryObject.model_fields`` rather than a hardcoded member
    list) and a caller attempting to construct one with ``as_of`` set is refused by pydantic's own
    ``extra="forbid"`` validation."""
    assert "as_of" not in QueryObject.model_fields
    with pytest.raises(pydantic.ValidationError):
        QueryObject(as_of="2026-01-01")


def test_no_registered_part_declares_a_temporal_capability():
    """The second half of condition 11: structurally impossible, since ``as_of`` is not a member
    of the 17-member ``Effect`` vocabulary at all."""
    registry = default_registry()
    for name_at_version in registry.keys():
        assert "as_of" not in registry.get(name_at_version).effects

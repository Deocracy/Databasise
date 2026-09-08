"""CONTRACT.md §8's admission record: the eleven-condition verdict table an opaque node must carry
before it can be dispatched for real. ``AdmissionRecord`` is the machine-side artifact that makes
§8's conditions checkable rather than merely narrated — ``validate_admission`` is what the registry
(``databasise/parts/registry.py``, plan 05-01 Task 2) calls at registration time so a record that
lies is refused before it is ever filed, never merely at run time.

These are wire-time machine refusals, not consumer-facing seam refusals — none of them subclasses
``databasise.seam.refusals.SeamRefusalError``; a caller of ``Databasise.ingest()`` never sees one of
these directly (a run-time subprocess failure is instead wrapped as
``databasise.seam.refusals.ForeignEngineRefusalError``). Every refusal here follows this codebase's
house style: name exactly what was wrong, store the offending value on a named attribute.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from databasise.parts.schema import Part

# §8 condition 1: the manifest a node's admission record carries MUST be code-inspected, never the
# engine's own self-report — an opaque node's self-description is not trusted at face value.
MANIFEST_SOURCE_CODE_INSPECTED = "code-inspected"

# §8 names exactly eleven conditions, numbered 1-11.
ADMISSION_CONDITION_IDS: tuple[int, ...] = tuple(range(1, 12))


@dataclass(frozen=True)
class ConditionVerdict:
    """One §8 condition's own verdict: which condition, what was found, and the concrete evidence
    it rests on. ``evidence`` is prose citing a real source (a file, a line range, a mechanism
    already built) — never left blank, which is exactly what ``AdmissionConditionMissingError``
    refuses.
    """

    condition: int
    verdict: str
    evidence: str


@dataclass(frozen=True)
class AdmissionRecord:
    """The full §8 admission record for one opaque part. ``verdicts`` MUST carry exactly the
    eleven condition ids with no duplicate and no blank evidence — enforced by
    :func:`validate_admission`, not by this dataclass's own constructor (a plain dataclass has no
    validation hook without becoming a pydantic model, and this record is deliberately a frozen
    dataclass to match ``Part``'s own shape, not a pydantic model).
    """

    part_name_at_version: str
    entry_path: str
    storage: str
    wall_clock_ceiling_seconds: float
    wall_clock_ceiling_basis: str
    feed_tier: str
    ttl_days: int
    network_namespace: str
    environment_hash: str
    manifest_source: str
    verdicts: tuple[ConditionVerdict, ...]


class AdmissionConditionMissingError(RuntimeError):
    """The record's ``verdicts`` set is not exactly conditions 1-11 with no duplicate, or some
    verdict's ``evidence`` is blank."""

    def __init__(self, part_name_at_version: str, reason: str):
        self.part_name_at_version = part_name_at_version
        self.reason = reason
        super().__init__(
            f"admission record for {part_name_at_version!r} is missing a required §8 condition "
            f"verdict: {reason}"
        )


class SelfReportedManifestError(RuntimeError):
    """§8 condition 1: ``manifest_source`` is not ``MANIFEST_SOURCE_CODE_INSPECTED`` — the engine's
    own self-report is never trusted as the manifest source."""

    def __init__(self, part_name_at_version: str, manifest_source: str):
        self.part_name_at_version = part_name_at_version
        self.manifest_source = manifest_source
        super().__init__(
            f"admission record for {part_name_at_version!r} carries manifest_source "
            f"{manifest_source!r}; §8 condition 1 requires "
            f"{MANIFEST_SOURCE_CODE_INSPECTED!r} (never the engine's own self-report)"
        )


class MissingWallClockCeilingError(RuntimeError):
    """§8 condition 4: ``wall_clock_ceiling_seconds`` is absent or not greater than zero. Raised
    both by :func:`validate_admission` (with the offending part named) and by
    ``databasise.validator.execution_mode.host`` for a ``subprocess`` placement dispatched with no
    ceiling — ``host()`` operates on a bare placement string with no part identity in scope, so
    ``part_name_at_version`` is optional and omitted at that call site.
    """

    def __init__(self, wall_clock_ceiling_seconds: Any, *, part_name_at_version: str | None = None):
        self.part_name_at_version = part_name_at_version
        self.wall_clock_ceiling_seconds = wall_clock_ceiling_seconds
        subject = f"admission record for {part_name_at_version!r}" if part_name_at_version else "a subprocess placement"
        super().__init__(
            f"{subject} carries wall_clock_ceiling_seconds={wall_clock_ceiling_seconds!r}; "
            "§8 condition 4 requires a positive, declared value"
        )


class ForbiddenSharedScopeError(RuntimeError):
    """§8 condition 5 (restating §3): an opaque part declares the shared artifact scope. An opaque
    node MAY write ``quarantined`` and MUST NOT write ``shared``."""

    def __init__(self, part_name_at_version: str, artifact_scope: str | None):
        self.part_name_at_version = part_name_at_version
        self.artifact_scope = artifact_scope
        super().__init__(
            f"opaque part {part_name_at_version!r} declares artifact_scope={artifact_scope!r}; "
            "§8 condition 5 (restating §3) forbids an opaque node writing the shared scope"
        )


def validate_admission(part: "Part", record: AdmissionRecord) -> None:
    """The record-only half of §8 admission — everything checkable from ``record``/``part`` alone,
    with no dependency on a registry or a resolved wiring (see :func:`cross_check_conditions` for
    the three machine-side conditions that do need those). Raises, by name:

    - :class:`AdmissionConditionMissingError` — the verdict set is not exactly conditions 1-11
      with no duplicate, or any verdict's ``evidence`` is blank.
    - :class:`SelfReportedManifestError` — ``manifest_source`` is not the code-inspected constant.
    - :class:`MissingWallClockCeilingError` — ``wall_clock_ceiling_seconds`` is absent or <= 0.
    - :class:`ForbiddenSharedScopeError` — the part is opaque and declares the shared scope.
    """
    condition_ids = [verdict.condition for verdict in record.verdicts]
    if sorted(condition_ids) != list(ADMISSION_CONDITION_IDS):
        raise AdmissionConditionMissingError(
            part.name_at_version,
            f"verdicts carry condition ids {sorted(condition_ids)}, expected exactly "
            f"{list(ADMISSION_CONDITION_IDS)} with no duplicate",
        )
    for verdict in record.verdicts:
        if not verdict.evidence.strip():
            raise AdmissionConditionMissingError(
                part.name_at_version,
                f"condition {verdict.condition}'s verdict carries blank evidence",
            )

    if record.manifest_source != MANIFEST_SOURCE_CODE_INSPECTED:
        raise SelfReportedManifestError(part.name_at_version, record.manifest_source)

    if record.wall_clock_ceiling_seconds is None or not (record.wall_clock_ceiling_seconds > 0):
        raise MissingWallClockCeilingError(
            record.wall_clock_ceiling_seconds, part_name_at_version=part.name_at_version
        )

    if part.structural_depth == "opaque" and part.artifact_scope == "shared":
        raise ForbiddenSharedScopeError(part.name_at_version, part.artifact_scope)


def cross_check_conditions(part: "Part", record: AdmissionRecord, *, registry: Any, resolved_wiring: dict) -> None:
    """The three §8 conditions the record alone cannot prove — each needs the registry and/or a
    resolved wiring to check against. Lazy-imports ``databasise.seam`` symbols so this module (in
    the one-way ``parts`` -> ``seam`` direction the rest of the package already keeps) does not
    take a module-scope dependency on the seam package.

    - Condition 7: the wiring whose ``provides`` node resolves to this opaque part must be
      excluded from the *default* selector candidate set.
    - Condition 10: nothing this opaque part registers can be enumerated as an SA-1-shareable
      artifact — i.e. its own ``artifact_scope`` is never the shared value.
    - Condition 11: the seam's ``QueryObject`` has no ``as_of`` member, and no registered part's
      declared effects include a temporal capability.
    """
    from databasise.seam.query import QueryObject
    from databasise.seam.selectors import _is_default_eligible

    if _is_default_eligible(resolved_wiring, registry):
        raise AdmissionConditionMissingError(
            part.name_at_version,
            "condition 7: the wiring whose provides node resolves to this opaque part is "
            "default-eligible; an opaque provides node must be excluded from the default "
            "selector candidate set",
        )

    if part.artifact_scope == "shared":
        raise AdmissionConditionMissingError(
            part.name_at_version,
            "condition 10: this opaque part declares artifact_scope='shared', which would make "
            "its output enumerable as an SA-1-shareable artifact",
        )

    if "as_of" in QueryObject.model_fields:
        raise AdmissionConditionMissingError(
            part.name_at_version,
            "condition 11: QueryObject declares an 'as_of' member; no registered part may declare "
            "a temporal capability",
        )
    for name_at_version in registry.keys():
        registered_part = registry.get(name_at_version)
        if "as_of" in registered_part.effects:
            raise AdmissionConditionMissingError(
                part.name_at_version,
                f"condition 11: part {name_at_version!r} declares an 'as_of' effect",
            )


__all__ = [
    "MANIFEST_SOURCE_CODE_INSPECTED",
    "ADMISSION_CONDITION_IDS",
    "ConditionVerdict",
    "AdmissionRecord",
    "AdmissionConditionMissingError",
    "SelfReportedManifestError",
    "MissingWallClockCeilingError",
    "ForbiddenSharedScopeError",
    "validate_admission",
    "cross_check_conditions",
]

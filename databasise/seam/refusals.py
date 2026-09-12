"""Typed refusal exception hierarchy for the ``databasise.seam`` boundary (D-10/D-14), following
the house style already established by ``databasise.wirings.resolve.UnknownArmError`` and
``databasise.parity.run_arm``'s own named refusals: every refusal names exactly what was wrong in
its constructor and message, and stores the offending value on a named attribute, rather than
letting a bare ``ValueError``/``KeyError`` propagate.

**No seam refusal enumerates this machine's registered arms, wirings, or node ids.** Unlike
``UnknownArmError``'s ``"known arms: [...]"`` suffix, a seam refusal names only the consumer's own
input — enumerating the machine's own candidate set in a consumer-visible message is exactly the
identity disclosure §18.2 forbids. The selector refusals 04-03 adds to this module (an
unsatisfiable alias/capability/harness selector) depend on this same rule: name what the consumer
asked for, never what the machine has.
"""

from __future__ import annotations

from typing import Any


class SeamRefusalError(ValueError):
    """Base class for every typed refusal raised at the ``databasise.seam`` boundary."""


class EmptyQueryObjectError(SeamRefusalError):
    """Raised when a query object carries no set member at all (§18.1) — refused before any
    wiring is resolved, never silently answered as an empty-text query."""

    def __init__(self, query_object: Any):
        self.query_object = query_object
        super().__init__(f"query object carries no set member: {query_object!r}")


class UnconsumableQueryMemberError(SeamRefusalError):
    """Raised when a query object carries a set member no fitted modality can consume (D-14) —
    named explicitly, never silently dropped so the remainder answers from what is left."""

    def __init__(self, member_name: str):
        self.member_name = member_name
        super().__init__(f"query member {member_name!r} cannot be consumed")


class UnsatisfiableSelectorError(SeamRefusalError):
    """Raised when no fitted modality satisfies a §18.4 selector (D-10) — an alias absent from
    the registry, a capability set no candidate wiring's registered parts jointly declare, a
    harness name no candidate declares, or (for the default form) a candidate set with nothing
    eligible left after the opaque exclusion (§8 condition 7). Never answered by the nearest
    satisfiable wiring instead (a near-miss fallback is worse than a refusal — see this module's
    docstring), and the message below names only ``selector_kind``/``requested`` — the consumer's
    own input — never a candidate wiring id, arm name, or node id.
    """

    def __init__(self, *, selector_kind: str, requested: Any):
        self.selector_kind = selector_kind
        self.requested = requested
        super().__init__(
            f"no fitted modality satisfies the {selector_kind!r} selector: {requested!r}"
        )


class ForbiddenSelectorInputError(SeamRefusalError):
    """Raised at ``Selector`` model validation (before any resolution runs) when a legal member's
    value has the shape of an internal identity — an instance hash — rather than a consumer-facing
    alias/capability/harness name. ``extra="forbid"`` already refuses a selector naming a wiring
    id, arm name, or node position as its own key (04-01); this refusal covers the narrower case
    of an internal identity smuggled in as the *value* of an otherwise-legal member.
    """

    def __init__(self, *, member_name: str, value: str):
        self.member_name = member_name
        self.value = value
        super().__init__(
            f"selector member {member_name!r} carries a value shaped like an internal identity: "
            f"{value!r}"
        )


class AmbiguousIngestPayloadError(SeamRefusalError):
    """Raised at ``IngestDocument`` validation when both ``text`` and ``raw`` are set, or when
    neither is — ``set_members`` names which of the two mutually-exclusive members were actually
    set (empty for "neither")."""

    def __init__(self, *, set_members: list[str]):
        self.set_members = list(set_members)
        # The literal "AmbiguousIngestPayload" substring is load-bearing: pydantic's
        # model_validator wraps this exception into a pydantic.ValidationError at the
        # IngestDocument construction call site (losing the original exception object), so a
        # caller distinguishing this refusal from another by inspecting the wrapped error's own
        # message needs the refusal's own name to survive in that message text.
        super().__init__(
            "AmbiguousIngestPayloadError: an ingest document must set exactly one of "
            f"'text'/'raw'; got {self.set_members!r} set"
        )


class OversizedDocumentError(SeamRefusalError):
    """Raised at ``IngestDocument`` validation when a ``raw`` payload (or a ``text`` payload's
    UTF-8 encoding) exceeds ``databasise.seam.corpus.MAX_DOCUMENT_BYTES`` — before any bytes are
    written to disk and before the subprocess is launched."""

    def __init__(self, *, actual_bytes: int, limit_bytes: int):
        self.actual_bytes = actual_bytes
        self.limit_bytes = limit_bytes
        super().__init__(
            f"ingest document is {actual_bytes} bytes, exceeding the {limit_bytes}-byte cap"
        )


class UnknownDocumentError(SeamRefusalError):
    """Raised by ``Databasise.delete_document()`` (05-03-PLAN.md Task 2) when ``document_id``
    fails the machine's own token discipline — the same bare-token rule
    ``databasise.seam.corpus.generated_on_disk_name`` already enforces for a raw-upload's on-disk
    name. Never raised for an id that is well-formed but simply does not exist in the corpus — v1
    itself reports that case as a normal ``"not_found"`` status carried in
    ``databasise.seam.corpus.DeletionOutcome.status``, not a refusal.
    """

    def __init__(self, *, document_id: str):
        self.document_id = document_id
        super().__init__(
            f"document id {document_id!r} fails the machine's own token discipline"
        )


class NoWritePathForModalityError(SeamRefusalError):
    """Raised by ``Databasise.ingest()``/``Databasise.delete_document()`` (06-10-PLAN.md) when the
    caller's own selector resolves to a fitted modality that ships no
    ``databasise/wirings/<family>/corpus-<operation>.json`` file for the requested write operation.
    A write silently landing in a different modality's index than the caller selected is
    undetectable from the return value — this refusal exists precisely because that failure mode is
    worse than an explicit "no write path" error: refusing by name lets the caller know immediately,
    where a silent fallback would only surface later, as data that looks present but was actually
    routed somewhere the caller never asked for.

    Names only ``operation`` — never the resolved modality, wiring id, arm name, or node id —
    per this module's own no-enumeration house style (§18.2's closed set applied to this refusal).
    The literal ``NoWritePathForModalityError`` substring is load-bearing for the same reason
    ``AmbiguousIngestPayloadError``'s own docstring documents: a caller distinguishing this refusal
    from another by inspecting a wrapped error's own message needs the refusal's own name to
    survive in that message text.
    """

    def __init__(self, *, operation: str) -> None:
        self.operation = operation
        super().__init__(
            f"NoWritePathForModalityError: no write path exists for operation {operation!r}"
        )


class NoRawUploadPathForModalityError(SeamRefusalError):
    """Raised by ``Databasise.ingest()`` (06-REVIEW.md CR-01) when a raw-bytes
    ``IngestDocument`` is submitted against a selector whose resolved corpus-ingest wiring's
    target node is not an ``opaque`` node. ``ingest()`` stamps a raw upload's real bytes only
    into ``file_paths``/``docs_format`` — a convention only an ``opaque`` node (a v1 subprocess
    that parses the file itself, e.g. ``lightrag/full-ingest``) knows how to read; a non-opaque
    target node (e.g. ``hipporag/chunker-embedder``, which reads only ``document["text"]``) always
    sees an empty string for a raw upload, silently indexing nothing while the operation still
    reports a normal-looking success. Refusing by name before any node config is stamped is
    strictly better than that silent data loss.

    Names only ``operation`` — never the resolved modality, wiring id, arm name, or node id —
    per this module's own no-enumeration house style, mirroring
    ``NoWritePathForModalityError``. The literal ``NoRawUploadPathForModalityError`` substring is
    load-bearing for the same reason ``NoWritePathForModalityError``'s own docstring documents: a
    caller distinguishing this refusal from another by inspecting a wrapped error's own message
    needs the refusal's own name to survive in that message text.
    """

    def __init__(self, *, operation: str) -> None:
        self.operation = operation
        super().__init__(
            "NoRawUploadPathForModalityError: no raw-upload path exists for operation "
            f"{operation!r}"
        )


class UnknownJobError(SeamRefusalError):
    """Raised by ``Databasise.get_job_status()`` (05-04-PLAN.md Task 1) when the foreign driver
    reports zero documents for the given job id — the raise-not-None behaviour
    ``databasise.seam.trace_store.TraceStore.resolve`` already established for an unknown trace
    reference, applied here to an unknown ingest job. Never raised for a job that genuinely has no
    documents on its *current page* (a caller-requested offset past the end of a real job) — only
    for a job id v1's own doc-status store reports no matching documents for at all.
    """

    def __init__(self, *, job_id: str):
        self.job_id = job_id
        super().__init__(f"job id {job_id!r} does not resolve to any known ingest job")


class PageSizeExceededError(SeamRefusalError):
    """Raised by ``databasise.seam.corpus.Page`` validation (05-04-PLAN.md Task 1) when
    ``limit`` exceeds ``databasise.seam.corpus.MAX_PAGE_SIZE`` — refused, never silently clamped
    down to the cap, per this codebase's refusals-over-silent-narrowing house style."""

    def __init__(self, *, requested: int, limit: int):
        self.requested = requested
        self.limit = limit
        # The literal "PageSizeExceededError" substring is load-bearing, mirroring
        # AmbiguousIngestPayloadError's own documented reason: pydantic's model_validator wraps
        # this exception into a pydantic.ValidationError at the Page construction call site
        # (losing the original exception object), so a caller distinguishing this refusal from
        # another by inspecting the wrapped error's own message needs the refusal's own name to
        # survive in that message text.
        super().__init__(
            f"PageSizeExceededError: requested page size {requested} exceeds the {limit}-entry cap"
        )


class MalformedBase64PayloadError(SeamRefusalError):
    """Raised by ``databasise.mcp.tools.IngestToolArgs.to_ingest_document()`` when ``field`` is
    not decodable in its declared base64 encoding — ``binascii.Error`` never escapes the tool body
    unnamed. ``field`` names the caller's own input slot only, per this module's own house style;
    it never carries the rejected payload's content or value, since a rejected payload may be
    arbitrarily large or hostile. Unlike ``PageSizeExceededError``/``AmbiguousIngestPayloadError``,
    this refusal is raised directly rather than inside a pydantic validator, so its own exception
    object is never lost to a wrapped ``pydantic.ValidationError`` — the class name is therefore
    not embedded in the message text (that convention exists only for the validator-raised pair).
    Lives in the seam rather than in the MCP transport for two reasons: the seam owns the refusal
    vocabulary both transports map generically (the same relationship ``rest.py``'s own
    ``_checked_page`` already has with ``PageSizeExceededError``), and a refusal defined inside
    ``databasise/mcp/`` would only be discovered by ``test_rest_transport.py``'s transitive
    ``SeamRefusalError`` subclass walk in runs where the ``mcp`` extra happens to be installed,
    making that parametrized proof depend on which extras were active.
    """

    def __init__(self, *, field: str):
        self.field = field
        super().__init__(f"field {field!r} is not decodable in its declared base64 encoding")


class MalformedSelectorPayloadError(SeamRefusalError):
    """Raised by ``databasise.seam.rest``'s ``POST /documents/upload`` route (CR-02 gap closure)
    when the ``selector`` multipart form field is not valid JSON matching ``Selector``'s own
    shape. ``selector`` arrives as a JSON-encoded form field parsed manually via
    ``Selector.model_validate_json`` — never inside a pydantic validator — so, exactly like
    ``MalformedBase64PayloadError`` above, this refusal must be raised directly rather than let a
    raw ``pydantic.ValidationError`` escape uncaught (which the registered ``SeamRefusalError``
    handler cannot map, producing an unhandled 500 instead of the documented 422). ``field`` names
    only the caller's own input slot, per this module's own house style; it never carries the
    rejected payload's content.
    """

    def __init__(self, *, field: str):
        self.field = field
        super().__init__(f"field {field!r} is not valid JSON matching the expected selector shape")


class EmptyComparisonRequestError(SeamRefusalError):
    """Raised by ``Databasise.compare()`` (06-03-PLAN.md, API-08) when zero selectors are
    supplied — a comparison needs at least one arm to compare (or run, at exactly one; a
    single-selector request never reaches this refusal, since RIG §RUN.3's degenerate-width rule
    means it is answered as a run instead). Names only the fact that the input was empty, never a
    candidate wiring — §18.2's closed-set rule applied to this refusal path. The literal class-name
    substring is load-bearing for the same reason ``AmbiguousIngestPayloadError``'s own docstring
    documents: this refusal is raised directly inside ``Databasise.compare()``, never inside a
    pydantic validator, so it is not itself at risk of the wrapping this note otherwise warns
    about — the substring is kept anyway for a uniform "name your own type in your own message"
    house style across every refusal in this module.
    """

    def __init__(self) -> None:
        super().__init__(
            "EmptyComparisonRequestError: a comparison request must supply at least one selector"
        )


class DuplicateComparisonKeyError(SeamRefusalError):
    """Raised by ``databasise.seam.compare.compare_arms()`` (06-03-PLAN.md) when two supplied
    selectors render to the same comparison-response key — refused by name rather than silently
    collapsed into one entry. A partial mapping with a silently-absent arm is the one shape a
    consumer cannot distinguish from a modality that legitimately returned nothing, so a key
    collision refuses the whole comparison instead. Names only the colliding key value, never a
    candidate wiring or selector's own internal resolution.
    """

    def __init__(self, *, key: str) -> None:
        self.key = key
        super().__init__(
            f"DuplicateComparisonKeyError: two selectors both render to comparison key {key!r}"
        )


class MutableStoreComparisonExcludedError(SeamRefusalError):
    """Raised by ``Databasise.compare()`` (06-09-PLAN.md, MACH-10/F-07) when a comparison's
    selectors resolve to a wiring whose parts declare ``mutates_store``. `CONTRACT.md §14.4`
    point 3 requires this exclusion to be an explicit refusal, never a silent skip or a filter
    that quietly drops the arm: a node that mutates its own backing store is not safely
    re-runnable for a `§5` parity/determinism comparison without a defined snapshot/reset
    protocol, and this project's own recorded decision
    (``databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md``) is permanent exclusion rather than
    building one. Names only the excluded component's own ``name@version`` — never another
    candidate wiring, arm name, or node id — per `§18.2`'s closed-set rule applied to this refusal
    path, the same discipline every other refusal in this module already follows.

    Checked in the comparison path only (two or more selectors); a single-selector call is a run
    under RIG `§RUN.3`'s degenerate-width rule, and `§14.4` point 3 excludes the component from
    `§5`'s parity/determinism *comparisons*, not from being run — ``query()`` and the one-selector
    ``compare()`` path never raise this.
    """

    def __init__(self, *, component: str) -> None:
        self.component = component
        super().__init__(
            "MutableStoreComparisonExcludedError: component "
            f"{component!r} declares mutates_store and is excluded from §5 parity/determinism "
            "comparisons per the recorded disposition in "
            "databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md"
        )


class EmptyPromotionTraceIdsError(SeamRefusalError):
    """Raised by ``databasise.seam.promotion.resolve_single_arm`` (07-01-PLAN.md, D-04) when a
    ``promote()`` call supplies an empty ``promotion_trace_ids`` list. CONTRACT §6's cross-field
    rule (``promotion_trace_ids`` non-empty iff ``promotion_provenance == "operator_asserted"``)
    has no SQL-level CHECK constraint to enforce it — this refusal is what makes the rule real,
    firing before any ledger read or write. Names only the caller's own ``alias`` — never a
    candidate mutation id or wiring name.
    """

    def __init__(self, *, alias: str):
        self.alias = alias
        super().__init__(
            f"EmptyPromotionTraceIdsError: promotion for alias {alias!r} was given no trace ids "
            "to derive the target wiring from"
        )


class DisagreeingPromotionTraceIdsError(SeamRefusalError):
    """Raised by ``databasise.seam.promotion.resolve_single_arm`` (07-01-PLAN.md, D-04) when the
    supplied trace ids resolve to more than one distinct wiring — refused rather than silently
    promoting whichever record happened to be read first or last, since that would promote a
    wiring the caller never actually named. Names only the caller's own ``trace_ids`` — never the
    resolved arm names, per this module's own no-enumeration house style.
    """

    def __init__(self, *, trace_ids: list[str]):
        self.trace_ids = list(trace_ids)
        super().__init__(
            "DisagreeingPromotionTraceIdsError: trace ids "
            f"{self.trace_ids!r} resolve to more than one distinct wiring; a promotion target "
            "must be named by trace ids that all agree on exactly one"
        )


class InvalidChangeOriginError(SeamRefusalError):
    """Raised by ``Databasise.promote()`` (07-01-PLAN.md, D-08) when ``change_origin`` is absent
    (``None``) or is not one of CONTRACT §7's two enumerated values (``human_edit``,
    ``machine_mutation``) — never defaulted, never inferred from absence. Names only the caller's
    own supplied value; the message does not enumerate the accepted set as a menu the caller could
    pattern-match against, and does not imply a default exists.
    """

    def __init__(self, *, change_origin: Any):
        self.change_origin = change_origin
        super().__init__(
            f"InvalidChangeOriginError: change_origin {change_origin!r} is not a recognised value"
        )


class UnrecognisedPromotionVerbError(SeamRefusalError):
    """Raised by ``Databasise.promote()`` (07-04-PLAN.md, D-09, closing 07-REVIEW.md CR-01) when
    ``verb`` is not one of ``databasise.seam.promotion.PromotionVerb``'s six declared literals.
    Checked before trace-id resolution runs (07-VERIFICATION.md's `missing:` item 1) — an unknown
    verb refuses immediately, the identical position ``GateVerbNotBuiltError`` already occupies for
    a known-but-unbuilt verb. Typed ``Any`` rather than ``str``, for the identical reason
    ``InvalidChangeOriginError`` types ``change_origin`` as ``Any``: a JSON body can deliver
    ``None``, a number, or an object, and the refusal must name whatever actually arrived. Per this
    module's own house style, the message names only the caller's own value — it does not
    enumerate the accepted verb set as a menu to pattern-match against, and does not imply a
    default exists.
    """

    def __init__(self, *, verb: Any):
        self.verb = verb
        super().__init__(
            f"UnrecognisedPromotionVerbError: verb {verb!r} is not a recognised promotion verb"
        )


class GateVerbNotBuiltError(SeamRefusalError):
    """Raised by ``Databasise.promote()`` (07-01-PLAN.md, D-09) when ``verb`` is ``check``,
    ``preview``, or ``run`` — no gate implementation exists in this milestone, and Phase 7 does
    not build one. Refused immediately, before any trace resolution or class derivation runs,
    since there is nothing yet to resolve. One shared refusal type parameterized by ``verb``,
    mirroring ``UnsatisfiableSelectorError``'s own ``selector_kind`` parameterization, rather than
    three near-identical exception classes for the same "not built" fact. Names only the caller's
    own ``verb``.
    """

    def __init__(self, *, verb: str):
        self.verb = verb
        super().__init__(f"GateVerbNotBuiltError: verb {verb!r} is not built in this milestone")


class MeasurementPostureRefusalError(SeamRefusalError):
    """Raised by ``Databasise.promote()`` (07-01-PLAN.md, D-09/D-11) when ``promote-next`` or
    ``promote-now`` is called against a mutation classed ``answer-level`` or ``index-side`` —
    measurement-gated promotion is off by default for both classes (RIG.md §F3.2), and this
    refusal is what keeps that default posture true at the runtime gate rather than merely
    documented. Names only the caller's own ``verb`` and the machine-derived ``mutation_class`` —
    never a wiring name, arm name, or node id.
    """

    def __init__(self, *, verb: str, mutation_class: str):
        self.verb = verb
        self.mutation_class = mutation_class
        super().__init__(
            f"MeasurementPostureRefusalError: verb {verb!r} refuses for mutation class "
            f"{mutation_class!r}: measurement-gated promotion is off by default for this class "
            "per RIG.md §F3.2"
        )


class UncalibratedFloorRefusalError(SeamRefusalError):
    """Raised by ``Databasise.promote()`` (07-01-PLAN.md, D-09/D-11) when ``promote-next`` or
    ``promote-now`` is called against a mutation classed ``retrieval-side`` — this class is
    measurement-gated ON by default (RIG.md §F3.2), but no calibrated A/A floor exists yet
    (MACH-03 Pending): a null whose cache-bypass status is unknown is not usable as a floor
    (RIG.md §AA.2). Names only the caller's own ``verb`` and the machine-derived
    ``mutation_class``.
    """

    def __init__(self, *, verb: str, mutation_class: str):
        self.verb = verb
        self.mutation_class = mutation_class
        super().__init__(
            f"UncalibratedFloorRefusalError: verb {verb!r} refuses for mutation class "
            f"{mutation_class!r}: no calibrated A/A floor exists yet per RIG.md §AA.2"
        )


class UnknownGenerationVersionError(SeamRefusalError):
    """Raised by ``Databasise.rollback()``/``Databasise.retire()`` (07-02-PLAN.md, D-05/D-07) when
    ``version`` names no generation ``alias`` has ever minted or acted on
    (``Ledger.generation_state`` returns ``None``). Covers both "this alias never minted that
    version" and "that version was minted under a different alias" as the same refusal — from the
    caller's own vocabulary both are the fact that *this alias has no such generation*; naming the
    other alias would disclose a generation the caller did not ask about. Names only the caller's
    own ``alias``/``version``.
    """

    def __init__(self, *, alias: str, version: str):
        self.alias = alias
        self.version = version
        super().__init__(
            f"UnknownGenerationVersionError: alias {alias!r} has no generation at version "
            f"{version!r}"
        )


class TombstonedGenerationError(SeamRefusalError):
    """Raised by ``Databasise.rollback()``/``Databasise.retire()`` (07-02-PLAN.md, D-05/D-07) when
    the named generation's latest ledger state (``Ledger.generation_state``) is a tombstone — RIG
    §PR.2 and CONTRACT §0.4: a retired generation is not reachable again, whether by rolling back
    to it or by retiring it a second time (a silent second tombstone would be indistinguishable
    from a real retirement to the caller). Checked by reading the *latest* record for the specific
    ``(alias, version)`` generation, never by scanning history for a tombstone anywhere — a wiring
    legitimately retired once and later re-promoted must stay promotable under its new generation.
    Names only the caller's own ``alias``/``version``.
    """

    def __init__(self, *, alias: str, version: str):
        self.alias = alias
        self.version = version
        super().__init__(
            f"TombstonedGenerationError: alias {alias!r} version {version!r} is tombstoned and "
            "is not reachable again"
        )


class ActiveGenerationRetirementError(SeamRefusalError):
    """Raised by ``Databasise.retire()`` (07-02-PLAN.md, D-07) when the named generation is
    ``alias``'s own currently active generation (``Ledger.by_alias(alias).minted_version ==
    version``). Retiring it would leave the alias resolving to a wiring just declared ineligible,
    and CONTRACT §16.2 already refuses pins to tombstoned artifacts. The operator rolls back
    first, then retires — ``by_alias`` walking backward to the most recent non-retired generation
    would be a second alias-lifecycle mechanism CONTEXT.md states is "not required and not asked
    for". Names only the caller's own ``alias``/``version``.
    """

    def __init__(self, *, alias: str, version: str):
        self.alias = alias
        self.version = version
        super().__init__(
            f"ActiveGenerationRetirementError: alias {alias!r} version {version!r} is the "
            "currently active generation; roll back first, then retire"
        )


class ForeignEngineRefusalError(SeamRefusalError):
    """The seam-facing wrapper for a foreign-engine subprocess failure
    (``databasise.foreign.CorpusOpSubprocessError``/``CorpusOpTimeoutError``) — so
    ``rest.py``'s existing generic ``SeamRefusalError`` handler maps it without a new
    endpoint-level branch. ``operation`` names the seam operation that was attempted (e.g.
    ``"ingest"``); ``cause`` carries the underlying foreign-engine exception. The message never
    enumerates this machine's own wirings, arms or node ids, per this module's own docstring rule.
    """

    def __init__(self, *, operation: str, cause: BaseException):
        self.operation = operation
        self.cause = cause
        super().__init__(f"the foreign engine refused operation {operation!r}: {cause}")


__all__ = [
    "SeamRefusalError",
    "EmptyQueryObjectError",
    "UnconsumableQueryMemberError",
    "UnsatisfiableSelectorError",
    "ForbiddenSelectorInputError",
    "AmbiguousIngestPayloadError",
    "OversizedDocumentError",
    "UnknownDocumentError",
    "NoWritePathForModalityError",
    "UnknownJobError",
    "PageSizeExceededError",
    "MalformedBase64PayloadError",
    "MalformedSelectorPayloadError",
    "EmptyComparisonRequestError",
    "DuplicateComparisonKeyError",
    "MutableStoreComparisonExcludedError",
    "ForeignEngineRefusalError",
    "EmptyPromotionTraceIdsError",
    "DisagreeingPromotionTraceIdsError",
    "InvalidChangeOriginError",
    "UnrecognisedPromotionVerbError",
    "GateVerbNotBuiltError",
    "MeasurementPostureRefusalError",
    "UncalibratedFloorRefusalError",
    "UnknownGenerationVersionError",
    "TombstonedGenerationError",
    "ActiveGenerationRetirementError",
]

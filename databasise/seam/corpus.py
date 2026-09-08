"""``databasise.seam.corpus`` — the corpus-side seam DTOs: ``IngestDocument`` (the caller's input),
``IngestJob`` (the job handle ``Databasise.ingest()`` returns) and ``DeletionOutcome`` (the result
``Databasise.delete_document()`` returns, 05-03-PLAN.md Task 2), plus ``MAX_DOCUMENT_BYTES`` and
``generated_on_disk_name`` — the raw-upload path safety mechanism (05-01-PLAN.md Task 3).

``IngestDocument`` accepts exactly one of two input shapes — ``text`` (a structured, already-
extracted payload) or ``raw``+``content_type`` (an opaque byte blob v1's own parser handles) —
never both, never neither. ``file_name`` and ``content_type`` are advisory metadata only, carried
into the job payload for citation; neither is ever used to build a filesystem path.
``generated_on_disk_name`` is what makes that true structurally: the on-disk name is derived only
from a server-minted ``document_id``, refusing any id that does not match the same bare-token
discipline ``databasise/namespaces.py``'s ``_NAMESPACE_TOKEN_RE`` already enforces for a namespace
directory name.

**05-04-PLAN.md Task 1: the bounded read surface.** ``Page``/``MAX_PAGE_SIZE``,
``DocumentStatusEntry``, ``JobStatus``, ``CorpusStatus``, ``DocumentCounts`` and ``HealthReport``
are ``Databasise``'s corpus-introspection models (API-06) — every one of them is bounded at the
type level so a caller can never reach a full corpus or index dump through this surface: ``Page``
refuses (never clamps) a ``limit`` above ``MAX_PAGE_SIZE``, ``health()``/``document_counts()``
return fixed-size records with no per-document member at all, and ``corpus_status()`` returns at
most ``MAX_PAGE_SIZE`` document entries per call, each entry carrying only an identifier, a status,
a timestamp and an optional error message — never document text, chunk text, an embedding vector,
or a graph node payload.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from databasise.seam.envelope import SeamEvent
from databasise.seam.refusals import (
    AmbiguousIngestPayloadError,
    OversizedDocumentError,
    PageSizeExceededError,
)

# API-06: the hard cap on any single page this seam will ever return — a caller requesting more
# is refused by name (PageSizeExceededError), never silently clamped down to this value.
MAX_PAGE_SIZE = 100

MAX_DOCUMENT_BYTES = 25 * 1024 * 1024

# A generated on-disk name is derived only from a server-minted OR caller-supplied document id —
# same bare-token *security* discipline databasise/namespaces.py's own _NAMESPACE_TOKEN_RE
# enforces (no path separator, no parent-directory reference, so a value handed to
# generated_on_disk_name() can never escape the corpus-inbox directory it is joined under), but
# widened to also permit underscore: unlike namespaces.py's own tokens (always machine-generated
# hex — config_hash, sha256, uuid.hex), a document_id may be caller-supplied (Databasise.ingest())
# or may name an already-ingested real-world document whose id legitimately contains underscores
# (05-03-PLAN.md Task 3's own corpus fixture ids — "a_kiss_for_corliss" and its siblings — are
# exactly this case). Underscore introduces no path-traversal risk; forbidding it was stricter
# than the actual security requirement.
_DOCUMENT_ID_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")

_ON_DISK_SUFFIX = ".bin"


class IngestDocument(BaseModel):
    """The caller's ingest input. Exactly one of ``text``/``raw`` must be set — never both, never
    neither (``AmbiguousIngestPayloadError``, naming what was missing/duplicated). A ``raw``
    payload (or a ``text`` payload whose UTF-8 encoding) larger than ``MAX_DOCUMENT_BYTES`` is
    refused (``OversizedDocumentError``) before any bytes are written to disk and before the
    subprocess is launched.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str | None = None
    document_id: str | None = None
    file_name: str | None = None  # advisory metadata only, never a path component
    raw: bytes | None = None
    content_type: str | None = None

    @model_validator(mode="after")
    def _exactly_one_payload_shape_within_the_size_cap(self) -> "IngestDocument":
        set_members = [name for name in ("text", "raw") if getattr(self, name) is not None]
        if len(set_members) != 1:
            raise AmbiguousIngestPayloadError(set_members=set_members)

        if self.raw is not None and len(self.raw) > MAX_DOCUMENT_BYTES:
            raise OversizedDocumentError(actual_bytes=len(self.raw), limit_bytes=MAX_DOCUMENT_BYTES)
        if self.text is not None:
            actual_bytes = len(self.text.encode("utf-8"))
            if actual_bytes > MAX_DOCUMENT_BYTES:
                raise OversizedDocumentError(actual_bytes=actual_bytes, limit_bytes=MAX_DOCUMENT_BYTES)
        return self


class IngestJob(BaseModel):
    """The job handle ``Databasise.ingest()`` returns — ``job_id`` is v1's own ``track_id``, never
    a machine-internal wiring/node identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str
    enqueued: int


class DeletionOutcome(BaseModel):
    """The result ``Databasise.delete_document()`` returns (05-03-PLAN.md Task 2). ``status`` is
    drawn from v1's own four-value ``DeletionResult`` vocabulary (``v1/lightrag/base.py``) —
    imported conceptually rather than re-invented, since the machine never imports ``lightrag``
    itself (``databasise/tools/check_import_boundary.py``). Deleting an already-deleted or
    never-ingested document is a normal ``"not_found"`` outcome carried here, never a refusal — a
    caller deleting an id that no longer exists has asked a legitimate question and received a
    legitimate answer. ``seam_events`` carries the MACH-11 correlation this deletion produced
    (``databasise.seam.engine._mach11_events``) — empty when nothing was recorded, one entry when
    the deleting node's own ``mutates_store`` effect correlated against its recorded touches.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    status: Literal["success", "not_found", "not_allowed", "fail"]
    message: str
    seam_events: list[SeamEvent] = []


class Page(BaseModel):
    """A bounded page request (API-06) — ``limit`` above ``MAX_PAGE_SIZE`` is refused
    (``PageSizeExceededError``), never clamped down to the cap, per this codebase's
    refusals-over-silent-narrowing house style. A negative ``offset`` is refused as a plain
    ``ValueError`` — there is no named refusal type for it because, unlike an oversized limit, a
    negative offset carries no interesting caller-facing value worth naming beyond "invalid"."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    limit: int = 50
    offset: int = 0

    @model_validator(mode="after")
    def _bounded(self) -> "Page":
        if self.limit > MAX_PAGE_SIZE:
            raise PageSizeExceededError(requested=self.limit, limit=MAX_PAGE_SIZE)
        if self.offset < 0:
            raise ValueError(f"offset must be non-negative, got {self.offset}")
        return self


class DocumentStatusEntry(BaseModel):
    """One document's status within a ``JobStatus``/``CorpusStatus`` page — carries only an
    identifier, a status, a timestamp and an optional error message. No field here ever carries
    document text, chunk text, an embedding vector, or a graph node payload (API-06)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    status: str
    updated_at: str
    error_message: str | None = None


class JobStatus(BaseModel):
    """The result ``Databasise.get_job_status()`` returns (05-04-PLAN.md Task 1, API-01's polling
    half). ``documents`` carries one ``DocumentStatusEntry`` per document in this job's own page;
    ``counts`` is v1's own whole-corpus status counts (v1 exposes no per-job counts); ``next_offset``
    is ``None`` on the last page."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str
    documents: list[DocumentStatusEntry]
    counts: dict[str, int]
    next_offset: int | None = None


class CorpusStatus(BaseModel):
    """The result ``Databasise.corpus_status()`` returns (05-04-PLAN.md Task 1, API-06) — a
    bounded, paginated document list, never a full corpus dump. ``next_offset`` is ``None`` on the
    last page; a caller requesting a page beyond ``MAX_PAGE_SIZE`` is refused by
    ``Page``'s own validator before this method is ever called."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    documents: list[DocumentStatusEntry]
    counts: dict[str, int]
    total: int
    next_offset: int | None = None


class DocumentCounts(BaseModel):
    """The result ``Databasise.document_counts()`` returns (05-04-PLAN.md Task 1, API-06) — a
    fixed-size record, never a per-document list. ``by_status`` keys are exactly v1's own status
    names; ``total`` equals their sum."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    by_status: dict[str, int]
    total: int


class HealthReport(BaseModel):
    """The result ``Databasise.health()`` returns (05-04-PLAN.md Task 1, API-06) — a fixed-size
    record: an overall ``status``, a per-store reachability map (``stores``, keyed by ``"kv"``/
    ``"vector"``/``"graph"``) and the foreign engine's own liveness fields (``engine``, keyed by
    ``"interpreter_present"``/``"working_dir_present"``/``"storages_initialized"``). Never raises
    for an unreachable store or an unreachable foreign engine — an unreachable participant is
    reported as unreachable, which is what a health check is for."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["ok", "degraded"]
    stores: dict[str, bool]
    engine: dict[str, bool]


def generated_on_disk_name(document_id: str) -> str:
    """The on-disk file name for a raw-upload document, built only from the server-minted
    ``document_id`` and a fixed suffix. Refuses any ``document_id`` that does not match the bare-
    token discipline ``databasise/namespaces.py``'s ``_NAMESPACE_TOKEN_RE`` already enforces — no
    path separator, no parent-directory reference, so the returned name can never resolve outside
    the directory it is joined under.
    """
    if not _DOCUMENT_ID_TOKEN_RE.match(document_id):
        raise ValueError(
            f"invalid document id {document_id!r}: must match {_DOCUMENT_ID_TOKEN_RE.pattern} "
            "(no path separator, no parent-directory reference)"
        )
    return f"{document_id}{_ON_DISK_SUFFIX}"


__all__ = [
    "MAX_DOCUMENT_BYTES",
    "MAX_PAGE_SIZE",
    "IngestDocument",
    "IngestJob",
    "DeletionOutcome",
    "Page",
    "DocumentStatusEntry",
    "JobStatus",
    "CorpusStatus",
    "DocumentCounts",
    "HealthReport",
    "generated_on_disk_name",
]

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
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from databasise.seam.envelope import SeamEvent
from databasise.seam.refusals import AmbiguousIngestPayloadError, OversizedDocumentError

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
    "IngestDocument",
    "IngestJob",
    "DeletionOutcome",
    "generated_on_disk_name",
]

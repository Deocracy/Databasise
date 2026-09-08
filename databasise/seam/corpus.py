"""``databasise.seam.corpus`` — the corpus-side seam DTOs: ``IngestDocument`` (the caller's input)
and ``IngestJob`` (the job handle ``Databasise.ingest()`` returns), plus ``MAX_DOCUMENT_BYTES``.

05-01-PLAN.md Task 1 authors the structured-text shape; Task 3 extends ``IngestDocument`` with the
raw-byte-upload shape (``raw``/``content_type``) and adds ``generated_on_disk_name`` — the
path-safety mechanism for that upload path.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

MAX_DOCUMENT_BYTES = 25 * 1024 * 1024


class IngestDocument(BaseModel):
    """The caller's ingest input. Task 1 ships the structured-text shape only; Task 3 adds the
    raw-byte-upload shape and the mutual-exclusion/size-cap validation across both."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str | None = None
    document_id: str | None = None
    file_name: str | None = None  # advisory metadata only, never a path component


class IngestJob(BaseModel):
    """The job handle ``Databasise.ingest()`` returns — ``job_id`` is v1's own ``track_id``, never
    a machine-internal wiring/node identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    job_id: str
    enqueued: int


__all__ = ["MAX_DOCUMENT_BYTES", "IngestDocument", "IngestJob"]

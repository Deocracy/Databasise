"""Loads and hash-verifies the Phase 3 parity corpus snapshot (03-02-PLAN.md Task 2, D-06/D-14).

Refuse-rather-than-trust, following ``databasise/stores/vector.py``'s own checksum convention: a
document whose on-disk bytes no longer match the digest ``MANIFEST.json`` recorded at fixture-build
time is a drifted corpus, and this loader raises naming the first mismatched document id rather
than silently returning stale or tampered content. Uses stdlib ``hashlib.sha256`` exclusively — the
same primitive ``databasise/namespaces.py`` and ``databasise/stores/vector.py`` already hash with;
no second hashing scheme is introduced here.

The snapshot itself — which HotpotQA rows, which documents, which queries — is fixed by
``databasise/parity/build_corpus_fixture.py`` (see ``tests/fixtures/corpus/README.md`` for the
regenerate command) and checked in as data (``MANIFEST.json`` plus one ``.txt`` file per document)
under ``tests/fixtures/corpus/``. This module only loads and verifies that already-built snapshot;
it performs no network access itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "corpus"


class CorpusDriftError(RuntimeError):
    """A snapshot document's on-disk bytes no longer match the digest ``MANIFEST.json`` recorded,
    or the corpus-level hash computed from the (verified) per-document digests no longer matches
    the manifest's own recorded ``corpus_hash`` — a drifted fixture is refused, never silently
    loaded, per this project's stated refusals-over-silent-fallbacks house style.
    """


@dataclass(frozen=True)
class CorpusDocument:
    id: str
    title: str
    text: str
    sha256: str


@dataclass(frozen=True)
class CorpusQuery:
    id: str
    question: str
    answer: str
    gold_document_ids: tuple[str, ...]


@dataclass(frozen=True)
class CorpusSnapshot:
    documents: tuple[CorpusDocument, ...]
    queries: tuple[CorpusQuery, ...]
    corpus_hash: str
    queries_hash: str
    source: dict[str, str]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_snapshot(fixture_dir: Path | None = None) -> CorpusSnapshot:
    """Load ``MANIFEST.json`` and every document it names, verifying each document's SHA-256 and
    the manifest's own corpus-level and query-set hashes. Raises ``CorpusDriftError`` naming the
    first mismatched document id (or the corpus/queries hash itself) on any mismatch — a snapshot
    that fails verification is never returned.
    """
    fixture_dir = fixture_dir or _DEFAULT_FIXTURE_DIR
    manifest_path = fixture_dir / "MANIFEST.json"
    documents_dir = fixture_dir / "documents"

    if not manifest_path.exists():
        raise CorpusDriftError(f"corpus manifest not found at {manifest_path}")
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))

    documents: list[CorpusDocument] = []
    for doc_id in sorted(manifest["documents"]):
        entry = manifest["documents"][doc_id]
        doc_path = documents_dir / f"{doc_id}.txt"
        if not doc_path.exists():
            raise CorpusDriftError(
                f"corpus document {doc_id!r} is missing on disk at {doc_path}"
            )
        text = doc_path.read_text(encoding="utf-8")
        actual_sha256 = _sha256_text(text)
        expected_sha256 = entry["sha256"]
        if actual_sha256 != expected_sha256:
            raise CorpusDriftError(
                f"corpus document {doc_id!r} has drifted: manifest recorded sha256="
                f"{expected_sha256!r}, but the on-disk file's actual sha256 is "
                f"{actual_sha256!r} ({doc_path})"
            )
        documents.append(
            CorpusDocument(id=doc_id, title=entry["title"], text=text, sha256=actual_sha256)
        )

    recomputed_corpus_hash = hashlib.sha256(
        "\n".join(d.sha256 for d in documents).encode("utf-8")
    ).hexdigest()
    if recomputed_corpus_hash != manifest["corpus_hash"]:
        raise CorpusDriftError(
            f"corpus-level hash mismatch: manifest recorded {manifest['corpus_hash']!r}, "
            f"recomputed {recomputed_corpus_hash!r} — every per-document digest verified "
            "individually, so this indicates the manifest's own corpus_hash field is stale "
            "(e.g. a document was added or removed without regenerating it)"
        )

    queries_raw = manifest["queries"]
    recomputed_queries_hash = hashlib.sha256(
        json.dumps(queries_raw, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if recomputed_queries_hash != manifest["queries_hash"]:
        raise CorpusDriftError(
            f"query-set hash mismatch: manifest recorded {manifest['queries_hash']!r}, "
            f"recomputed {recomputed_queries_hash!r}"
        )

    queries = tuple(
        CorpusQuery(
            id=q["id"],
            question=q["question"],
            answer=q["answer"],
            gold_document_ids=tuple(q["gold_document_ids"]),
        )
        for q in queries_raw
    )

    return CorpusSnapshot(
        documents=tuple(documents),
        queries=queries,
        corpus_hash=recomputed_corpus_hash,
        queries_hash=recomputed_queries_hash,
        source=dict(manifest["source"]),
    )

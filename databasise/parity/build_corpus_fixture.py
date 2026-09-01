"""Regenerates the Phase 3 parity corpus fixture (03-02-PLAN.md Task 2, D-06/D-14).

Fetches a small, fixed slice of the HotpotQA distractor-setting validation split from
HuggingFace's public datasets-server API (no `datasets` package dependency — this is a one-time
fixture build, not a runtime dependency of `databasise/`), writes one plain-text document per
context paragraph under ``tests/fixtures/corpus/documents/``, and writes
``tests/fixtures/corpus/MANIFEST.json`` recording each document's SHA-256, a corpus-level SHA-256,
and a query set with each query's gold supporting document ids.

This is the "exact command that regenerates it" named in ``tests/fixtures/corpus/README.md``:

    cd databasise && uv run python -m databasise.parity.build_corpus_fixture

Re-running this script overwrites the fixture with the same content (the HotpotQA validation
split is a fixed, versioned dataset) — it does not draw a new random sample. It is not run as
part of any test or the parity harness itself; it is a one-time fixture generator, checked in
alongside its output so a second author can regenerate byte-identically without any of Task 2's
own HotpotQA-fetching logic living in the loader (``corpus.py``) that every later test imports.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

_DATASET = "hotpotqa/hotpot_qa"
_CONFIG = "distractor"
_SPLIT = "validation"
_NUM_QUESTIONS = 2  # kept small deliberately (03-02-PLAN.md: "sized to what makes one v1 index
# affordable rather than to what a statistical floor would need" — D-10 is not calibrated here)

_FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "corpus"
_DOCUMENTS_DIR = _FIXTURE_DIR / "documents"
_MANIFEST_PATH = _FIXTURE_DIR / "MANIFEST.json"

_HF_ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset={dataset}&config={config}&split={split}&offset=0&length={length}"
)


def _slugify(title: str) -> str:
    """A stable, filesystem-safe, human-readable document id derived from a HotpotQA title."""
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return slug or "untitled"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fetch_rows(num_questions: int) -> list[dict[str, Any]]:
    url = _HF_ROWS_URL.format(dataset=_DATASET, config=_CONFIG, split=_SPLIT, length=num_questions)
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 — fixed HTTPS host, fixture build only
        payload = json.load(resp)
    return [row["row"] for row in payload["rows"]]


def build(num_questions: int = _NUM_QUESTIONS) -> None:
    rows = _fetch_rows(num_questions)

    documents: dict[str, dict[str, Any]] = {}
    document_texts: dict[str, str] = {}
    queries: list[dict[str, Any]] = []

    for i, row in enumerate(rows):
        titles = row["context"]["title"]
        sentence_lists = row["context"]["sentences"]
        gold_ids: list[str] = []

        for title, sentences in zip(titles, sentence_lists, strict=True):
            doc_id = _slugify(title)
            text = title + "\n\n" + "".join(sentences)
            if doc_id in document_texts and document_texts[doc_id] != text:
                raise RuntimeError(
                    f"slug collision building corpus fixture: {doc_id!r} maps to two different "
                    f"titles/texts (title={title!r})"
                )
            document_texts[doc_id] = text
            documents[doc_id] = {"title": title, "sha256": _sha256_text(text)}

        for gold_title in row["supporting_facts"]["title"]:
            gold_id = _slugify(gold_title)
            if gold_id not in gold_ids:
                gold_ids.append(gold_id)

        queries.append(
            {
                "id": f"q{i + 1}",
                "question": row["question"],
                "answer": row["answer"],
                "gold_document_ids": gold_ids,
            }
        )

    _DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    for doc_id, text in document_texts.items():
        (_DOCUMENTS_DIR / f"{doc_id}.txt").write_text(text, encoding="utf-8")

    corpus_hash = hashlib.sha256(
        "\n".join(documents[doc_id]["sha256"] for doc_id in sorted(documents)).encode("utf-8")
    ).hexdigest()
    queries_hash = hashlib.sha256(
        json.dumps(queries, sort_keys=True).encode("utf-8")
    ).hexdigest()

    manifest = {
        "source": {"dataset": _DATASET, "config": _CONFIG, "split": _SPLIT},
        "document_count": len(documents),
        "documents": dict(sorted(documents.items())),
        "corpus_hash": corpus_hash,
        "queries": queries,
        "queries_hash": queries_hash,
    }
    _MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(documents)} documents and {len(queries)} queries to {_FIXTURE_DIR}")


if __name__ == "__main__":
    build()

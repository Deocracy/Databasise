"""Regenerates the Phase 3 parity corpus fixture (03-02-PLAN.md Task 2, D-06/D-14) and, at a
different question count/offset/output directory, the larger Phase 6 eval-bundle fixture
(06-04-PLAN.md Task 1, MACH-02).

Fetches a slice of the HotpotQA distractor-setting validation split from HuggingFace's public
datasets-server API (no `datasets` package dependency — this is a one-time fixture build, not a
runtime dependency of `databasise/`), writes one plain-text document per context paragraph under
``<fixture_dir>/documents/``, and writes ``<fixture_dir>/MANIFEST.json`` recording each document's
SHA-256, a corpus-level SHA-256, and a query set with each query's gold supporting document ids.

Two regenerate commands, both documented — the Phase 3 corpus (unparameterised, byte-identical to
before this module was parameterised):

    cd databasise && uv run python -m databasise.parity.build_corpus_fixture

and the Phase 6 eval-corpus fixture (30 questions, offset past the 2 rows the Phase 3 corpus
already took, written to a disjoint directory so `tests/fixtures/corpus/` is never touched):

    cd databasise && uv run python -m databasise.parity.build_corpus_fixture \\
        --num-questions 30 --offset 2 --fixture-dir tests/fixtures/eval-corpus

Re-running either command overwrites its own fixture with the same content (the HotpotQA
validation split is a fixed, versioned dataset) — it does not draw a new random sample. It is not
run as part of any test or the parity harness itself; it is a one-time fixture generator, checked
in alongside its output so a second author can regenerate byte-identically without any of this
module's own HotpotQA-fetching logic living in the loader (``corpus.py``) that every later test
imports.
"""

from __future__ import annotations

import argparse
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
_OFFSET = 0

_FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "corpus"

_HF_ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset={dataset}&config={config}&split={split}&offset={offset}&length={length}"
)


def _slugify(title: str) -> str:
    """A stable, filesystem-safe, human-readable document id derived from a HotpotQA title."""
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return slug or "untitled"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fetch_rows(num_questions: int, offset: int = _OFFSET) -> list[dict[str, Any]]:
    url = _HF_ROWS_URL.format(
        dataset=_DATASET, config=_CONFIG, split=_SPLIT, offset=offset, length=num_questions
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        payload = json.load(resp)
    return [row["row"] for row in payload["rows"]]


def build(
    num_questions: int = _NUM_QUESTIONS,
    fixture_dir: Path = _FIXTURE_DIR,
    offset: int = _OFFSET,
) -> None:
    documents_dir = fixture_dir / "documents"
    manifest_path = fixture_dir / "MANIFEST.json"
    rows = _fetch_rows(num_questions, offset=offset)

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
                # Offset-anchored, not enumerate-anchored (i+1 alone would re-mint "q1"/"q2" for
                # any non-zero offset, colliding with the Phase 3 corpus's own query ids — see
                # this module's own "no question id appears in both fixtures" regenerate contract).
                "id": f"q{offset + i + 1}",
                "question": row["question"],
                "answer": row["answer"],
                "gold_document_ids": gold_ids,
            }
        )

    documents_dir.mkdir(parents=True, exist_ok=True)
    for doc_id, text in document_texts.items():
        (documents_dir / f"{doc_id}.txt").write_text(text, encoding="utf-8")

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
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(documents)} documents and {len(queries)} queries to {fixture_dir}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--num-questions",
        type=int,
        default=_NUM_QUESTIONS,
        help=f"how many HotpotQA validation rows to fetch (default: {_NUM_QUESTIONS})",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=_OFFSET,
        help=f"row offset into the HotpotQA validation split (default: {_OFFSET})",
    )
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=_FIXTURE_DIR,
        help=f"output fixture directory (default: {_FIXTURE_DIR})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    _args = _parse_args()
    build(num_questions=_args.num_questions, fixture_dir=_args.fixture_dir, offset=_args.offset)

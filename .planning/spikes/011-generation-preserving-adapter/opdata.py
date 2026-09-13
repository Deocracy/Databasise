"""Shared op-emission data for spike 011 (stdlib only, no GPU, no network).

One-shot prompt: spike 003's INSTRUCTION bytes + one held-out example block
(spike 008's D1 format). Spike 008's example doc (shirley_temple) is a TEST
document in queries-v1, so training must not use it. This module picks the
example from a TRAIN document by the same median-op rule 008 used
(sort train docs by (op count, doc id), take the middle) and records it.

Teacher ops: spike 003's teacher.json (schema ops.v0.2), train documents
only. Test documents are never trained on (asserted by every trainer).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SHARED = REPO / ".planning" / "spikes" / "shared" / "queries-v1.json"
SPIKE003 = REPO / ".planning" / "spikes" / "003-op-emission-size-sweep"

sys.path.insert(0, str(SPIKE003))
from common import INSTRUCTION, load_units  # noqa: E402 (spike 003, read-only)


def load_teacher():
    teacher = json.loads((SPIKE003 / "teacher.json").read_text())
    assert teacher.get("schema") == "ops.v0.2"
    units, corpus_hash = load_units()
    assert teacher["corpus_hash"] == corpus_hash, "teacher labels are for another corpus state"
    return teacher, dict(units), corpus_hash


def train_doc_ids():
    q = json.loads(SHARED.read_text(encoding="utf-8"))
    test = set(q["test_document_ids"])
    all_docs = sorted({row["doc"] for row in q["queries"]})
    train = [d for d in all_docs if d not in test]
    assert len(train) == 15, f"expected 15 train docs, got {len(train)}"
    return train, sorted(test)


def pick_example_doc(teacher) -> str:
    """Median-op rule restricted to train documents.

    008 sorted all 20 docs by (op count, doc id) and took indices 8..11
    (shirley_temple, adam_collis, deliver_us_from_evil_2014_film,
    scott_derrickson). shirley_temple is test, so for training we sort the
    15 train docs the same way and take the middle (index 7).
    """
    train, _ = train_doc_ids()
    ranked = sorted(train, key=lambda d: (len(teacher["labels"][d]["ops"]), d))
    return ranked[len(ranked) // 2]


def example_block(doc_id: str, contents: dict) -> str:
    ops_json = json.dumps({"ops": teacher_ops(doc_id)})
    return f"Section:\n{contents[doc_id]}\n\nJSON:\n{ops_json}"


def teacher_ops(doc_id: str):
    teacher, _, _ = load_teacher()
    return teacher["labels"][doc_id]["ops"]


def oneshot_prompt(content: str, contents: dict, example_doc: str) -> str:
    ex = example_block(example_doc, contents)
    return INSTRUCTION + "\n\nExample:\n" + ex + "\n\nSection:\n" + content + "\n\nJSON:\n"


def target_json(doc_id: str) -> str:
    return json.dumps({"ops": teacher_ops(doc_id)})

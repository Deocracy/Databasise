"""Shared prompt + corpus loading for spike 003 (stdlib only).

The INSTRUCTION bytes are identical for the frontier teacher (chat user
message) and every student arm (completion prompt body): same task text,
same section content, same required output shape. Per-model chat templates
are deliberately NOT used on the student side, so Qwen3 "thinking" cannot
trigger: thinking-off holds by construction (completion API, no <think>
priming) and is verified empirically in student.py (every output scanned
for think tags).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # spike folder -> spikes -> .planning -> repo root
SPIKE001 = REPO / ".planning" / "spikes" / "001-score-io-model"

# Read-only reuse of the validated contract artefacts (never modified here).
sys.path.insert(0, str(SPIKE001))
import ops_validate  # noqa: E402  (spike 001, VALIDATED)
from grammar import grammar_for_subset  # noqa: E402  (spike 001, VALIDATED)

FILE_SET = ("graph", "sql")


def _load_corpus_module():
    path = REPO / "databasise" / "parity" / "corpus.py"
    spec = importlib.util.spec_from_file_location("spike003_corpus", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["spike003_corpus"] = mod  # dataclasses need the registration
    spec.loader.exec_module(mod)
    return mod


def load_units():
    """20 units: (doc_id, section_content). Content is the raw .txt bytes
    decoded as UTF-8 (title + blank line + paragraph); evidence spans index
    into exactly this string."""
    mod = _load_corpus_module()
    snap = mod.load_snapshot()
    units = [(d.id, d.text) for d in snap.documents]
    assert len(units) == 20, f"expected 20 corpus docs, got {len(units)}"
    return units, snap.corpus_hash


INSTRUCTION = (
    "You file facts from a text section into stores. "
    'Emit one JSON object {"ops":[...]} with at most 32 ops, '
    "targets restricted to [graph,sql]. "
    "Graph op: {\"target\":\"graph\",\"s\":subject,\"p\":predicate,\"o\":object,"
    "\"quote\":evidence}. "
    "Sql op: {\"target\":\"sql\",\"subject\":subject,\"attribute\":attribute,"
    "\"value\":value,\"value_type\":\"text\"|\"number\"|\"date\","
    "\"quote\":evidence}; dates as ISO 8601 or a year, numbers as decimals. "
    "Evidence (quote) is a 3-to-256-character VERBATIM substring copied "
    "character-for-character from the section text below; the quoted span "
    "must contain the subject or the value verbatim -- if the value is "
    "normalised (an ISO date, a decimal), quote a span containing the "
    "subject instead. Never invent offsets, never paraphrase the quote. "
    "Emit one graph op and one sql op per distinct checkable fact. "
    'If the section states no checkable fact, emit {"ops":[]}. '
    "Output JSON only, no prose."
)


def student_prompt(content: str) -> str:
    return INSTRUCTION + "\n\nSection:\n" + content + "\n\nJSON:\n"


TEACHER_SYSTEM = "You are a precise information-extraction labeller. Output JSON only, no prose."


def teacher_messages(content: str) -> list[dict]:
    return [
        {"role": "system", "content": TEACHER_SYSTEM},
        {"role": "user", "content": INSTRUCTION + "\n\nSection:\n" + content},
    ]

"""Phase 14 (14-03, D-02, D-04): the two new promotion refusals are catalogued, name only what the
caller supplied, and map to 422 on the REST transport. Self-contained: the classes are resolved with
``getattr`` so the file collects (and fails by assertion) on code that predates them."""

from __future__ import annotations

import re

from databasise.seam import refusals, rest
from databasise.wirings.resolve import all_wirings

_NAMES = ("PartialRunEvidenceError", "GateNotCalibratedError")


def _internal_words() -> set[str]:
    words: set[str] = set()
    for name, resolved in all_wirings():
        words.add(name)
        words.update(resolved["nodes"])
    return words


def _contains_word(message: str, word: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", message) is not None


def _build(name: str):
    cls = getattr(refusals, name, None)
    assert cls is not None, f"{name} is not defined in databasise.seam.refusals"
    if name == "PartialRunEvidenceError":
        return cls(trace_ids=["t-1"])
    return cls(verb="promote-next")


def test_both_classes_are_catalogued():
    for name in _NAMES:
        assert getattr(refusals, name, None) is not None, f"{name} is not defined"
        assert name in refusals.__all__, f"{name} is not in refusals.__all__"


def test_partial_run_evidence_names_only_the_trace_ids():
    exc = _build("PartialRunEvidenceError")
    assert exc.trace_ids == ["t-1"]
    message = str(exc)
    assert "t-1" in message
    for word in _internal_words():
        assert not _contains_word(message, word), f"message names {word!r}: {message}"


def test_gate_not_calibrated_names_only_the_verb():
    exc = _build("GateNotCalibratedError")
    assert exc.verb == "promote-next"
    message = str(exc)
    assert "promote-next" in message and "not calibrated" in message
    for word in _internal_words() | {"index-side", "retrieval-side", "answer-level"}:
        assert not _contains_word(message, word), f"message names {word!r}: {message}"
    assert not re.search(r"\d", message)


def test_both_map_to_422_with_their_refusal_type():
    for name in _NAMES:
        exc = _build(name)
        assert rest._status_for(exc) == 422
        assert refusals.refusal_body(exc)["refusal_type"] == name

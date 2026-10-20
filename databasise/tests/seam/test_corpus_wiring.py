"""14-06-PLAN.md Task 2 (LEDG-13, D-14): the corpus wiring path layout is defined once.

``engine._corpus_wiring`` loads ``<family>/corpus-<operation>.json`` through
``wirings.resolve.load_wiring``, so patching ``resolve._WIRINGS_ROOT`` redirects it, and a missing
file is the named 422 ``NoWritePathForModalityError``, never a ``FileNotFoundError``.
"""

from __future__ import annotations

import json

from databasise.seam import engine as engine_module
from databasise.wirings import resolve
from databasise.wirings.resolve import resolve_arm

_MARKER = {"marker": "corpus-ingest from the patched resolve root"}


def _call(operation: str):
    try:
        return engine_module._corpus_wiring(resolve_arm("naive"), operation), None
    except Exception as caught:  # noqa: BLE001 - the assertion is on the captured type
        return None, caught


def test_corpus_wiring_reads_through_load_wiring(tmp_path, monkeypatch):
    (tmp_path / "lightrag").mkdir()
    (tmp_path / "lightrag" / "corpus-ingest.json").write_text(json.dumps(_MARKER), encoding="utf-8")
    monkeypatch.setattr(resolve, "_WIRINGS_ROOT", tmp_path)

    loaded, error = _call("ingest")

    assert error is None, f"_corpus_wiring raised {type(error).__name__}: {error}"
    assert loaded == _MARKER


def test_a_missing_corpus_file_is_a_named_refusal(tmp_path, monkeypatch):
    (tmp_path / "lightrag").mkdir()
    monkeypatch.setattr(resolve, "_WIRINGS_ROOT", tmp_path)

    loaded, error = _call("delete")

    assert loaded is None, "a corpus-delete wiring loaded from a root that holds none"
    assert type(error).__name__ == "NoWritePathForModalityError", f"{type(error).__name__}: {error}"

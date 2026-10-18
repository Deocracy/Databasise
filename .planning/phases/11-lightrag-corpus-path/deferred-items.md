# Phase 11 Deferred Items

Out-of-scope findings logged during execution. Not fixed by the plan that found them.

## From 11-01

- `databasise/evidence/f07_report.py` Verdict and "A qualification" prose (rendered into
  `databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md`) still names two real mutable-store
  components; the table now lists three (`lightrag/v1-index-sync@0.1.0` added). The
  `_LIGHTRAG_FULL_DELETE_REASON` text also still says "a single-node wiring built inline", while
  `corpus-delete.json` is now a two-node wiring loaded from disk. Reword both in the f-string and
  re-render the record (the byte-identical test pins them together).
- Pre-existing ruff findings, not introduced by 11-01: `seam/engine.py` (import order, two unused
  `noqa: BLE001`, ASYNC230 on the staged-upload `open`, BLE001 in `health`), `seam/corpus.py`
  (UP037, unsorted `__all__`), `foreign/v1_corpus_adapter.py` (PLW1510, unsorted `__all__`).

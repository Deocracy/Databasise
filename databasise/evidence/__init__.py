"""Evidence: the committed, re-runnable records of what this project measured.

Renderers (each rewrites its own document from committed inputs, so a second run is not a second
finding):

- ``falsifier2.py`` (``python -m databasise.evidence.falsifier2``) renders ``FALSIFIER-2-EVIDENCE.md``
  from the named wirings under ``wirings/`` and ``probe_registry()``; its verdict and exit status
  are computed from the probe results.
- ``parity_report.py`` (``python -m databasise.evidence.parity_report``) renders
  ``PARITY-EVIDENCE.md`` from ``parity_results/``, the committed per-arm parity run records;
  ``--check-results`` verifies their provenance without writing.
- ``f07_report.py`` (``python -m databasise.evidence.f07_report``) renders
  ``F-07-MUTABLE-STORE-DISPOSITION.md`` from ``default_registry()``.

Committed data: ``parity_results/`` (parity run records), ``eval-bundles/`` (the committed eval bundle
``bundle@v1`` and the judge prompt), ``wirings/`` (Falsifier 2's named wirings) and
``rig-trace.databasise.schema.json``.

Hand-written records (structural tests for several of them live under ``databasise/tests/evidence/``):
``CROSS-MODALITY-EVIDENCE.md`` (MODAL-05), ``FALSIFIER-4-EVIDENCE.md``, ``FALSIFIER-5-EVIDENCE.md``,
``F-14-SEAM-INVARIANCE.md``, ``HIPPORAG-PORT-RECORD.md``, ``PROMOTION-LEDGER-EVIDENCE.md``,
``EVAL-BUNDLE-V1.md``, ``DECLARED-DEVIATIONS.md``, ``RIG-TRACE-DEVIATIONS.md``,
``ADMISSION-CODEBASE-MEMORY-MCP.md``, ``DR-04-DECISION.md``, ``INJECTED-LLM-ENDPOINT-SURVEY.md`` and
``COVERAGE.md``.
"""

from __future__ import annotations

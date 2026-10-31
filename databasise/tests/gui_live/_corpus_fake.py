"""18-02 (D-19): the shared LightRAG corpus fake for the live console tests.

It reuses the RUN-10 stub bodies, so LightRAG ingest, delete, status and health run offline over one
in-memory corpus. ``Databasise.__init__`` resolves ``default_registry()`` at construction, so the
registry swap has to be in place before ``build_app``. When a later plan needs another corpus op, it
extends this file in the same RED commit as the test that uses it.
"""

from __future__ import annotations

from typing import Any

import pytest

import databasise.seam.engine as engine_module
from databasise.tests.seam.test_run10_upload_poll_delete_counts import _shared_corpus


def install(mp: pytest.MonkeyPatch) -> dict[str, dict[str, Any]]:
    """Patches ``run_corpus_op`` and ``default_registry`` on ``mp`` and returns the shared corpus
    (document id -> ``{track_id, status}``)."""
    corpus, registry = _shared_corpus(mp)
    mp.setattr(engine_module, "default_registry", lambda: registry)
    return corpus

"""Phase 15 review-fix checks for the eval CLIs (15-REVIEW.md, lane A findings)."""

from __future__ import annotations

import pytest

from databasise.eval import corpus_ingest
from databasise.parity.corpus import load_snapshot


@pytest.mark.parametrize("limit", ["-5", "0"])
def test_corpus_ingest_limit_below_one_exits_2(limit, capsys):
    """A-CR-01: a negative --limit would slice to all but |limit| documents; argparse refuses it."""
    with pytest.raises(SystemExit) as exc_info:
        corpus_ingest.main(["--limit", limit])
    assert exc_info.value.code == 2
    assert "documents" not in capsys.readouterr().out


@pytest.mark.parametrize("limit", [-5, 0])
def test_corpus_ingest_estimate_refuses_limit_below_one(limit):
    """A-CR-01: the library entry point refuses by name instead of slicing."""
    snapshot = load_snapshot(corpus_ingest.CORPUS_DIR)
    with pytest.raises(corpus_ingest.NonPositiveLimitError):
        corpus_ingest.estimate(snapshot, limit=limit, arm="lightrag")

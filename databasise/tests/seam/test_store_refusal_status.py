"""10-01-PLAN.md Task 2 (STOR-01, D-02): a busy store is a 409, the third caller-facing status
``rest._status_for`` returns (``test_refusal_status_codes.py`` lists it in ``_MAPPED_ELSEWHERE``)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from databasise.seam.refusals import StoreBusyError
from databasise.seam.rest import _status_for


def test_store_busy_maps_to_409():
    assert _status_for(StoreBusyError(store_kind="graph")) == 409

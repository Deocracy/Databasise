"""``databasise.seam`` — the consumer-facing §18 seam (D-01).

A caller reaches the engine through ``Databasise.query(query_object, selector=None)`` and receives
a closed ``ResponseEnvelope`` — no wiring name, arm name, node id or instance hash crossing the
boundary in either direction (D-05). ``databasise.run_wiring`` and
``databasise.runner.scheduler.run_wiring`` remain machine-internal (D-02); this package is the
redacting surface over them.

This module deliberately does not import ``databasise.seam.rest`` at module scope — that optional
REST transport (04-05) is only imported by a consumer who has installed the ``rest`` extra.
"""

from __future__ import annotations

from databasise.seam.compare import compare_arms
from databasise.seam.engine import Databasise
from databasise.seam.envelope import ResponseEnvelope
from databasise.seam.query import QueryObject
from databasise.seam.selectors import Selector

__all__ = ["Databasise", "QueryObject", "ResponseEnvelope", "Selector", "compare_arms"]

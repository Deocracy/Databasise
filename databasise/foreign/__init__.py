"""``databasise.foreign`` — CONTRACT §17's foreign-part adapter layer: process lifecycle, the RPC
channel, health. Not ``databasise/parity/`` — parity is Phase 3's read-only comparison harness
between the decomposed and original LightRAG query arms; this package is shared by every opaque
Part that needs to reach a foreign interpreter for a real write operation (ingest today, delete and
status added in 05-03/05-04), and a second admitted engine (05-06) reuses this same launch shape
rather than a copy under ``parity/``.
"""

from __future__ import annotations

from databasise.foreign.v1_corpus_adapter import (
    CorpusOpSubprocessError,
    CorpusOpTimeoutError,
    MissingV1InterpreterError,
    run_corpus_op,
)

__all__ = [
    "run_corpus_op",
    "CorpusOpTimeoutError",
    "CorpusOpSubprocessError",
    "MissingV1InterpreterError",
]

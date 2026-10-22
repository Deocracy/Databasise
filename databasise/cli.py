"""Shared contract for the offline CLIs (15-02, D-03).

Exit table: 0 done or estimate-only; 1 named refusal (one stderr line ``ClassName: message``, printed
by :func:`refuse`); 2 bad arguments (argparse only); 3 ran but inconclusive. ``main()`` returns the int.

Not in ``databasise.launcher``: that package imports ``parity.import_index`` at module level (a cycle
once import_index imports this module) and its own ``refuse`` prints a ``databasise: `` prefix that
RUN-06/07 pin. Top-level imports here are stdlib only; seam, openai and httpx load inside functions.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, TextIO

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_INCONCLUSIVE = 3

_MAX_REFUSAL_CHARS = 500


def refusal_line(exc: BaseException) -> str:
    """``ClassName: message`` as exactly one line (whitespace collapsed, at most 500 characters of
    message, the class name never doubled)."""
    text = re.sub(r"\s+", " ", str(exc)).strip()[:_MAX_REFUSAL_CHARS]
    name = type(exc).__name__
    return text if text.startswith(f"{name}:") else f"{name}: {text}"


def refuse(exc: BaseException, *, stream: TextIO | None = None) -> int:
    """Print :func:`refusal_line` to stderr and return :data:`EXIT_REFUSED`."""
    print(refusal_line(exc), file=stream or sys.stderr)
    return EXIT_REFUSED


def offline_refusals(*extra: type[BaseException]) -> tuple[type[BaseException], ...]:
    """The TOOL-04 refusal tuple. Never a bare ``ValueError`` or ``RuntimeError`` (D-03)."""
    import httpx
    import openai

    from databasise.clients.builder import BUILDER_REFUSALS
    from databasise.clients.openai_compat import (
        EmbeddingBatchMismatchError,
        EmptyChoicesError,
        MissingCompletionContentError,
        ModelIdentityMissingError,
    )
    from databasise.clients.rerank import RerankResponseError
    from databasise.eval.bundle import (
        BundleDriftError,
        CorruptUsageLogError,
        MissingTargetFamilyError,
        SealedPartitionOpenedError,
    )
    from databasise.parity.corpus import CorpusDriftError
    from databasise.seam.refusals import SeamRefusalError
    from databasise.store_lock import StoreLockedError
    from databasise.stores.vector import VectorStoreCorruptedError

    return (
        *BUILDER_REFUSALS,
        ModelIdentityMissingError,
        EmptyChoicesError,
        MissingCompletionContentError,
        EmbeddingBatchMismatchError,
        RerankResponseError,
        VectorStoreCorruptedError,
        StoreLockedError,
        SeamRefusalError,
        FileNotFoundError,
        BundleDriftError,
        CorruptUsageLogError,
        CorpusDriftError,
        MissingTargetFamilyError,
        SealedPartitionOpenedError,
        openai.OpenAIError,
        httpx.HTTPError,
        *extra,
    )


class InstalledPackageWriteError(RuntimeError):
    """An evidence renderer refuses to overwrite its committed document inside an installed package
    (C-WR-03): the documents are source-checkout records, never site-packages state."""


def write_committed_documents(*documents: tuple[Path, str]) -> None:
    """Write each ``(path, text)``, after checking that no path lies in an installed package, so a
    refusal writes none of them."""
    for path, _text in documents:
        if {"site-packages", "dist-packages"} & set(path.resolve().parts):
            raise InstalledPackageWriteError(
                f"{path} is inside an installed package; run this renderer from a source checkout"
            )
    for path, text in documents:
        path.write_text(text, encoding="utf-8")


def positive_int(text: str) -> int:
    """An argparse ``type`` that rejects 0 and negatives, so a bad value exits 2 at parse time."""
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {text}")
    return value


class ArmSelectorMismatchError(RuntimeError):
    def __init__(self, *, arm_id: str, expected_wiring_id: str | None, resolved_arm_id: Any, resolved_wiring_id: Any):
        self.arm_id = arm_id
        self.expected_wiring_id = expected_wiring_id
        self.resolved_arm_id = resolved_arm_id
        self.resolved_wiring_id = resolved_wiring_id
        super().__init__(
            f"selector resolves to arm_id={resolved_arm_id!r} wiring_id={resolved_wiring_id!r}, "
            f"expected arm_id={arm_id!r} wiring_id={expected_wiring_id!r}"
        )


def check_named_arm(selector: Any, *, arm_id: str, registry: Any) -> None:
    """Prove, before any spend, that the §18.4 capability ``selector`` still picks the arm named
    ``arm_id`` (Phase 13 gave every arm its own ``wiring_id`` and ``arm_id``). Reads no store, builds
    no client."""
    from databasise.seam.selectors import resolve_selector
    from databasise.wirings.resolve import wiring_for_name

    expected = wiring_for_name(arm_id)
    resolved = resolve_selector(selector, registry=registry)
    expected_wiring_id = None if expected is None else expected.get("wiring_id")
    if (
        expected is None
        or resolved.get("arm_id") != expected.get("arm_id")
        or resolved.get("wiring_id") != expected_wiring_id
    ):
        raise ArmSelectorMismatchError(
            arm_id=arm_id,
            expected_wiring_id=expected_wiring_id,
            resolved_arm_id=resolved.get("arm_id"),
            resolved_wiring_id=resolved.get("wiring_id"),
        )

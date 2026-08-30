"""The resolved-closure environment digest folded into every config_hash, per CONTRACT.md §1.

D-12 (one-way door, confirmed 01-01-PLAN.md Task 3, recorded in 01-01-SUMMARY.md): **option-a**
selected — the environment digest folded into every ``config_hash`` is the resolved distribution
closure read from ``importlib.metadata`` at runtime: what is actually installed, never what a
lockfile declares, never a Nix store path. Nix is substrate-only (spike 004: it names nothing in
the model, NixOS hosts the system and Nix builds the software, while the machine builds the
indexes). Accepted consequence: two machines with identical lockfiles but different resolved
wheels intentionally produce different identities, per CONTRACT.md §1's own environment-hash
clause ("For an opaque node, the environment hash MUST cover the whole resolved runtime closure,
not merely the component's own build inputs").
"""

from __future__ import annotations

import functools
import hashlib
import platform
import sys
from importlib.metadata import Distribution, distributions

from databasise.identity.canon import canonicalise


def _record_digest(dist: Distribution) -> str | None:
    """SHA-256 over ``dist``'s sorted RECORD hash lines, or None where RECORD is absent."""
    record_text = dist.read_text("RECORD")
    if record_text is None:
        return None
    lines = sorted(record_text.splitlines())
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


@functools.cache
def environment_hash() -> str:
    """The resolved-closure environment digest, memoised per process (D-12)."""
    dist_rows = sorted(
        (
            [dist.metadata["Name"] or "", dist.version, _record_digest(dist)]
            for dist in distributions()
        ),
        key=lambda row: row[0],
    )
    payload = {
        "python_version": list(sys.version_info[:3]),
        "platform": platform.platform(),
        "distributions": dist_rows,
    }
    return hashlib.sha256(canonicalise(payload)).hexdigest()

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

The collection path asserts no collected value (distribution name, version, or RECORD contents)
embeds a Nix store path — spike 004's rule that Nix is substrate-only and store paths are never
identity, enforced here rather than merely assumed. Where a distribution has no RECORD file, its
digest is recorded as ``None`` rather than omitting the distribution row entirely: omitting it
would let two differently-provisioned environments collide on identity, which is the exact
failure D-12 exists to prevent.
"""

from __future__ import annotations

import functools
import hashlib
import platform
import sys
from importlib.metadata import Distribution, distributions
from typing import Any

from databasise.identity.canon import canonicalise

_NIX_STORE_PREFIX = "/nix/store/"


class EnvironmentDigestError(RuntimeError):
    """A collected environment value embedded a Nix store path — Nix is substrate-only per
    spike 004, and store paths are never identity (D-12).
    """


def _assert_no_nix_store_path(value: str, *, source: str) -> None:
    """Guard the collection path: no collected value may embed a Nix store path (D-12)."""
    if _NIX_STORE_PREFIX in value:
        raise EnvironmentDigestError(
            f"{source} contains a Nix store path ({_NIX_STORE_PREFIX!r} substring); Nix is "
            "substrate-only per spike 004 and store paths are never identity"
        )


def _record_digest(dist: Distribution) -> str | None:
    """SHA-256 over ``dist``'s sorted RECORD hash lines, or None where RECORD is absent."""
    record_text = dist.read_text("RECORD")
    if record_text is None:
        return None
    _assert_no_nix_store_path(record_text, source="RECORD contents")
    lines = sorted(record_text.splitlines())
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _collect_environment_payload() -> dict[str, Any]:
    """Build the environment-hash payload dict fresh (uncached) — the same structure
    :func:`environment_hash` hashes, exposed separately so tests can exercise version-change
    sensitivity without fighting the process-wide ``functools.cache`` on the public function.
    """
    dist_rows: list[list[Any]] = []
    for dist in distributions():
        name = dist.metadata["Name"] or ""
        version = dist.version
        _assert_no_nix_store_path(name, source="distribution name")
        _assert_no_nix_store_path(version, source="distribution version")
        dist_rows.append([name, version, _record_digest(dist)])
    dist_rows.sort(key=lambda row: row[0])
    return {
        "python_version": list(sys.version_info[:3]),
        "platform": platform.platform(),
        "distributions": dist_rows,
    }


@functools.cache
def environment_hash() -> str:
    """The resolved-closure environment digest, memoised per process (D-12)."""
    return hashlib.sha256(canonicalise(_collect_environment_payload())).hexdigest()

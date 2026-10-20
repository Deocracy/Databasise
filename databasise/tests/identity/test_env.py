"""WIRE-15 (13-07, D-16): ``Databasise.health()`` reports an environment-digest failure.

Every run folds ``environment_hash()`` into its identities, so a digest that raises
``EnvironmentDigestError`` (a RECORD embedding a ``/nix/store/`` path) aborts every run. ``health``
used to say ``ok`` anyway. It now appends the fixed reason ``environment digest unavailable`` to
``engine_reason`` and reports ``degraded``, with no new ``HealthReport`` field and no distribution
path in the text. The failure is not cached (``functools.cache`` memoises success only). The payload
legs of WIRE-15 follow in 13-12.
"""

from __future__ import annotations

import pytest

from databasise.identity import env as env_module
from databasise.seam import engine as engine_module
from databasise.seam.engine import Databasise

_REASON = "environment digest unavailable"


class _NixPathDistribution:
    """A distribution whose RECORD embeds a Nix store path, which the digest refuses."""

    metadata = {"Name": "poisoned"}
    version = "1.0"

    def read_text(self, filename: str) -> str | None:
        return "/nix/store/abc-poisoned/lib.py,sha256=x,1" if filename == "RECORD" else None


@pytest.fixture
def fast_health(monkeypatch):
    """No v1 subprocess: the driver's health op answers configured."""
    monkeypatch.setattr(engine_module, "run_corpus_op", lambda *a, **k: {"configured": True})
    env_module.environment_hash.cache_clear()
    yield
    env_module.environment_hash.cache_clear()


def _engine(store_root) -> Databasise:
    return Databasise(store_root=store_root, workspace="env-health", clients={"llm": object(), "embedding": object()})


async def test_health_reports_a_failed_environment_digest(fast_health, store_root, monkeypatch):
    monkeypatch.setattr(env_module, "distributions", lambda: [_NixPathDistribution()])

    report = await _engine(store_root).health()

    assert report.status == "degraded"
    assert _REASON in (report.engine_reason or "")
    assert "/nix/store" not in (report.engine_reason or "")


async def test_health_recovers_once_the_digest_computes_again(fast_health, store_root, monkeypatch):
    with monkeypatch.context() as patched:
        patched.setattr(env_module, "distributions", lambda: [_NixPathDistribution()])
        failing = await _engine(store_root).health()
    env_module.environment_hash.cache_clear()

    recovered = await _engine(store_root).health()

    assert _REASON in (failing.engine_reason or "")
    assert _REASON not in (recovered.engine_reason or "")


# --------------------------------------------------------------------------------------------- #
# WIRE-15 (13-12, D-16): the payload carries OS, architecture and libc, not the kernel string
# --------------------------------------------------------------------------------------------- #


def _hash_with(monkeypatch, **patched) -> str:
    for name, value in patched.items():
        monkeypatch.setattr(env_module.platform, name, value)
    env_module.environment_hash.cache_clear()
    try:
        return env_module.environment_hash()
    finally:
        env_module.environment_hash.cache_clear()


def test_a_kernel_update_does_not_change_the_environment_hash(monkeypatch):
    before = _hash_with(monkeypatch, platform=lambda *a, **k: "Linux-6.18.56-x86_64-with-glibc2.42")
    after = _hash_with(monkeypatch, platform=lambda *a, **k: "Linux-6.18.57-x86_64-with-glibc2.42")

    assert before == after


def test_a_different_architecture_changes_the_hash(monkeypatch):
    x86 = _hash_with(monkeypatch, machine=lambda: "x86_64")
    arm = _hash_with(monkeypatch, machine=lambda: "aarch64")

    assert x86 != arm


def test_an_empty_libc_still_hashes(monkeypatch):
    digest = _hash_with(monkeypatch, libc_ver=lambda *a, **k: ("", ""))

    assert len(digest) == 64


def test_the_docstrings_list_every_input():
    text = " ".join(
        [env_module.__doc__ or "", env_module.environment_hash.__doc__ or "", env_module._collect_environment_payload.__doc__ or ""]
    )

    for word in ("python", "system", "machine", "libc", "RECORD", "version"):
        assert word in text, word

"""Resolves a real judge identity and mints the eval bundle's *next* version with it
(06-12-PLAN.md Task 2) — closes `databasise/evidence/FALSIFIER-5-EVIDENCE.md`'s precondition 1.

**Exact invocation:**

    uv run python -m databasise.eval.remint

**`EVAL-BUNDLE-V1.md`'s own next-minted-version rule, quoted verbatim** (its own Limits section):
"When a real judge call is first made ..., the resolved identity becomes part of the bundle's own
**next-minted version**, per §EV.1's own 'judge instance ... changing' invalidating-change rule —
this document is not re-edited in place to carry it retroactively." That settles the version
question this module implements: mint `bundle@v2` (or whatever the next content-addressed version
is), never re-mint `bundle@v1` in place. `databasise.eval.bundle.mint_bundle` already does this by
construction — its version identity is a content hash over `judge_instance` among other members, so
a changed identity mints the next version automatically and `bundle@v1`'s bytes and checksum are
never touched (`BundleEditInPlaceError`/`load_bundle`'s own checksum re-verification already refuse
an in-place edit).

**`main()` makes exactly one live model call and is therefore gated by 06-13's own blocking spend
checkpoint.** Nothing in this module's `main()` runs for real in this plan — it is genuine,
runnable code, proven against stub clients and seeded fixtures only (`test_remint.py`).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from databasise.eval.bundle import EvalBundle, mint_bundle
from databasise.eval.corpus_ingest import CORPUS_DIR
from databasise.parity.corpus import CorpusSnapshot, load_snapshot
from databasise.parity.run_arm import (
    DEFAULT_V1_ENV_PARITY,
    MissingParityEnvError,
    MissingParityEnvKeyError,
    _build_clients,
    _load_env_file,
)
from databasise.seam.engine import _CONCURRENCY_SETTING, _DETERMINISM_SETTING

# The single minimal probe message resolve_judge_identity() sends — the smallest request that
# still returns a well-formed response with a resolved_model_identity to read.
_MINIMAL_JUDGE_PROBE_MESSAGES: list[dict[str, str]] = [{"role": "user", "content": "ping"}]

_REPO_EVAL_DIR = Path(__file__).resolve().parent.parent
_COMMITTED_BUNDLE_ROOT = _REPO_EVAL_DIR / "evidence" / "eval-bundles"
_JUDGE_PROMPT_PATH = _COMMITTED_BUNDLE_ROOT / "judge-prompt-v1.txt"

# RED-DRAFT DEFECT scaffolding: removed in the GREEN commit along with the defect it supports.
_DRAFT_MINT_CALL_COUNTER = {"n": 0}


class UnresolvedJudgeIdentityError(RuntimeError):
    """Raised by :func:`resolve_judge_identity` when the provider response carries no
    ``resolved_model_identity`` to derive ``judge_instance`` from. Mirrors
    ``databasise.clients.openai_compat.ModelIdentityMissingError``'s own refusal wording (Phase 1
    D-12 / Phase 2 D-08: "hash what is installed, never what is declared") — the requested/declared
    model id is never substituted in its place.
    """

    def __init__(self) -> None:
        super().__init__(
            "UnresolvedJudgeIdentityError: the provider response carried no "
            "resolved_model_identity to derive judge_instance from; refusing to substitute the "
            "requested/declared model id"
        )


async def resolve_judge_identity(chat_client: Any) -> str:
    """Issue **one** minimal chat call and return ``result.resolved_model_identity`` — the identity
    a real provider response itself reports, never the model id ``chat_client`` was constructed
    with. Raises :class:`UnresolvedJudgeIdentityError` when that field is empty or absent. This is
    the only function in this module that would touch the network, and only when handed a real
    client.
    """
    result = await chat_client.chat(_MINIMAL_JUDGE_PROBE_MESSAGES)
    identity = result.resolved_model_identity
    # RED-DRAFT DEFECT (06-12-PLAN.md Task 2, TDD RED phase): never raises, and mangles the
    # resolved identity with a placeholder-ish literal suffix — makes
    # test_resolve_judge_identity_returns_the_identity_a_real_response_reports and
    # test_resolve_judge_identity_raises_when_response_carries_no_identity both fail on real
    # assertions. Restored in the GREEN commit.
    return (identity or "placeholder-judge@v1") + "-draft"


def remint(
    snapshot: CorpusSnapshot,
    bundle_root: Path,
    *,
    judge_instance: str,
    judge_prompt_hash: str,
    determinism_setting: str,
    concurrency_setting: str,
) -> EvalBundle:
    """A thin call-through to :func:`databasise.eval.bundle.mint_bundle`, returning the
    :class:`EvalBundle` it returns. Adds no versioning logic of its own: ``mint_bundle`` is already
    content-addressed over ``judge_instance``, so a changed identity mints the next version and an
    unchanged one returns the already-minted version — do not add a redundant bump here.
    """
    # RED-DRAFT DEFECT: ignores the caller's own judge_instance (hardcoded literal instead) and
    # perturbs judge_prompt_hash per call, breaking mint_bundle's own content-hash idempotence —
    # makes test_remint_mints_a_new_version_and_leaves_v1_bytes_untouched and
    # test_reminting_twice_with_the_same_identity_reuses_the_version both fail on real assertions.
    # Restored in the GREEN commit.
    _DRAFT_MINT_CALL_COUNTER["n"] += 1
    return mint_bundle(
        snapshot,
        bundle_root,
        judge_instance="draft-not-implemented",
        judge_prompt_hash=judge_prompt_hash + str(_DRAFT_MINT_CALL_COUNTER["n"]),
        determinism_setting=determinism_setting,
        concurrency_setting=concurrency_setting,
    )


def main(argv: list[str] | None = None) -> int:
    """``uv run python -m databasise.eval.remint`` — the exact invocation this module's own
    docstring names. Builds real clients from ``v1/.env.parity``, resolves the judge identity from
    one real chat call, reads the judge prompt's real SHA-256 (recomputed, never restated as a
    literal), reads the determinism/concurrency setting live off
    ``databasise.seam.engine``'s own module constants, mints, and prints the resulting version id
    and its ``judge_instance``. Exit codes: 0 on a successful mint, 1 on any refusal — mirrors
    ``databasise.parity.build_hipporag_index.main``'s own convention.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    try:
        env = _load_env_file(DEFAULT_V1_ENV_PARITY)
        clients = _build_clients(env)
    except (MissingParityEnvError, MissingParityEnvKeyError) as exc:
        print(str(exc), file=sys.stderr)
        # RED-DRAFT DEFECT: wrong exit code on a refusal — makes
        # test_main_with_no_live_credentials_exits_1_and_never_mints fail on a real assertion.
        # Restored in the GREEN commit.
        return 0

    try:
        judge_instance = asyncio.run(resolve_judge_identity(clients["llm"]))
    except UnresolvedJudgeIdentityError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    snapshot = load_snapshot(CORPUS_DIR)
    judge_prompt_hash = hashlib.sha256(_JUDGE_PROMPT_PATH.read_bytes()).hexdigest()

    bundle = remint(
        snapshot,
        _COMMITTED_BUNDLE_ROOT,
        judge_instance=judge_instance,
        judge_prompt_hash=judge_prompt_hash,
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )

    print(json.dumps({"version": bundle.version, "judge_instance": bundle.judge_instance}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "UnresolvedJudgeIdentityError",
    "main",
    "remint",
    "resolve_judge_identity",
]

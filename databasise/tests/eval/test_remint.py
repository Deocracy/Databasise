"""Tests for databasise.eval.remint (06-12-PLAN.md Task 2's <behavior> block).

No live call in any test — resolve_judge_identity is driven against stub chat client doubles, and
remint/main against a tmp_path bundle root and monkeypatched env/client construction. Mirrors
databasise/tests/eval/test_bundle_versioning.py's own fixture and assertion style.
"""

from __future__ import annotations

import pytest

from databasise.clients.base import ChatResult
from databasise.eval import remint
from databasise.eval.bundle import mint_bundle
from databasise.eval.remint import UnresolvedJudgeIdentityError, resolve_judge_identity
from databasise.parity.run_arm import MissingParityEnvError
from databasise.runner.trace import TokenAccounting

_JUDGE_PROMPT_HASH = "a" * 64
_DETERMINISM_SETTING = "cache-bypassed"
_CONCURRENCY_SETTING = "sequential"


class _StubChatClientWithIdentity:
    def __init__(self, identity: str):
        self._identity = identity

    async def chat(self, messages, **kwargs):
        return ChatResult(
            text="ok",
            tokens=TokenAccounting(prompt_tokens=1, completion_tokens=1, call_count=1, counted_by="stub"),
            resolved_model_identity=self._identity,
        )


class _StubChatClientWithNoIdentity:
    async def chat(self, messages, **kwargs):
        return ChatResult(
            text="ok",
            tokens=TokenAccounting(prompt_tokens=1, completion_tokens=1, call_count=1, counted_by="stub"),
            resolved_model_identity="",
        )


def _mint_v1(bundle_root, eval_snapshot):
    return mint_bundle(
        eval_snapshot,
        bundle_root,
        judge_instance="unresolved",
        judge_prompt_hash=_JUDGE_PROMPT_HASH,
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )


# --------------------------------------------------------------------------------------------- #
# Test 1
# --------------------------------------------------------------------------------------------- #


async def test_resolve_judge_identity_returns_the_identity_a_real_response_reports():
    identity = await resolve_judge_identity(_StubChatClientWithIdentity("vendor/model-x"))
    assert identity == "vendor/model-x"


# --------------------------------------------------------------------------------------------- #
# Test 2
# --------------------------------------------------------------------------------------------- #


async def test_resolve_judge_identity_raises_when_response_carries_no_identity():
    with pytest.raises(UnresolvedJudgeIdentityError):
        await resolve_judge_identity(_StubChatClientWithNoIdentity())


# --------------------------------------------------------------------------------------------- #
# Test 3
# --------------------------------------------------------------------------------------------- #


def test_remint_mints_a_new_version_and_leaves_v1_bytes_untouched(bundle_root, eval_snapshot):
    v1 = _mint_v1(bundle_root, eval_snapshot)
    v1_bundle_path = bundle_root / v1.version / "bundle.json"
    v1_checksum_path = bundle_root / v1.version / "bundle.sha256"
    v1_bundle_bytes_before = v1_bundle_path.read_bytes()
    v1_checksum_bytes_before = v1_checksum_path.read_bytes()

    v2 = remint.remint(
        eval_snapshot,
        bundle_root,
        judge_instance="vendor/model-x",
        judge_prompt_hash=_JUDGE_PROMPT_HASH,
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )

    assert v2.version != v1.version
    assert v2.judge_instance == "vendor/model-x"
    assert v1_bundle_path.read_bytes() == v1_bundle_bytes_before
    assert v1_checksum_path.read_bytes() == v1_checksum_bytes_before


# --------------------------------------------------------------------------------------------- #
# Test 4
# --------------------------------------------------------------------------------------------- #


def test_reminting_twice_with_the_same_identity_reuses_the_version(bundle_root, eval_snapshot):
    v1 = _mint_v1(bundle_root, eval_snapshot)

    v2 = remint.remint(
        eval_snapshot,
        bundle_root,
        judge_instance="vendor/model-x",
        judge_prompt_hash=_JUDGE_PROMPT_HASH,
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )
    v2_again = remint.remint(
        eval_snapshot,
        bundle_root,
        judge_instance="vendor/model-x",
        judge_prompt_hash=_JUDGE_PROMPT_HASH,
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )

    assert v2_again.version == v2.version
    existing_versions = {p.name for p in bundle_root.iterdir() if p.is_dir()}
    assert existing_versions == {v1.version, v2.version}


# --------------------------------------------------------------------------------------------- #
# Test 5
# --------------------------------------------------------------------------------------------- #


def test_main_with_no_live_credentials_exits_1_and_never_mints(monkeypatch, capsys, bundle_root, tmp_path):
    def _raise_missing(path):
        raise MissingParityEnvError(path)

    minted_calls: list[object] = []
    monkeypatch.setattr(remint, "DEFAULT_V1_ENV_PARITY", tmp_path / "absent.env.parity")
    monkeypatch.setattr(remint, "_load_env_file", _raise_missing)
    monkeypatch.setattr(remint, "remint", lambda *a, **k: minted_calls.append((a, k)))

    exit_code = remint.main(["--spend"])

    assert exit_code == 1
    assert minted_calls == []  # never proceeded to a mint with a placeholder identity

    err = capsys.readouterr().err
    assert "absent.env.parity" in err  # the patched path, never the real v1/.env.parity


# --------------------------------------------------------------------------------------------- #
# 15-10 (D-03, D-04) — estimate-only by default; the package-directory constant keeps its value.
# --------------------------------------------------------------------------------------------- #


def test_remint_without_spend_is_estimate_only(monkeypatch, capsys, tmp_path):
    calls: list[str] = []

    async def _resolve(client):
        calls.append("resolve")
        return "vendor/model-x"

    monkeypatch.setattr(remint, "DEFAULT_V1_ENV_PARITY", tmp_path / "absent.env.parity")
    monkeypatch.setattr(remint, "_load_env_file", lambda path: calls.append("env") or {})
    monkeypatch.setattr(remint, "_build_clients", lambda env: calls.append("clients") or {"llm": None})
    monkeypatch.setattr(remint, "resolve_judge_identity", _resolve)
    monkeypatch.setattr(remint, "remint", lambda *a, **k: calls.append("mint"))  # never touch the real bundles

    try:
        code = remint.main([])
    except BaseException as caught:  # noqa: BLE001
        code = f"raised {type(caught).__name__}"

    out = capsys.readouterr().out
    assert calls == [], calls
    assert code == 0, code
    assert "1 chat call" in out
    assert "mode: estimate-only" in out.splitlines()


def test_the_bundle_root_still_resolves_to_the_package_bundles():
    from pathlib import Path

    package_dir = Path(remint.__file__).resolve().parent.parent
    assert getattr(remint, "_PACKAGE_DIR", None) == package_dir
    assert remint._COMMITTED_BUNDLE_ROOT == package_dir / "evidence" / "eval-bundles"
    assert remint._COMMITTED_BUNDLE_ROOT.as_posix().endswith("databasise/evidence/eval-bundles")

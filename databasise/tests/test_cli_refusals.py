"""TOOL-04 (D-03): the six offline CLIs map every named failure to one stderr line and exit 1.

Each case injects one named error from the client builder, the env loader, the corpus or bundle loader,
the work function or the provider call, runs ``main([... "--spend"])`` and asserts the returned code is 1,
that stderr holds exactly one non-empty line, that the line names the error class, and that no traceback
appears. The remaining cases pin ``--n-resamples 0`` (exit 2 before any client), the one event loop of a
two-family ``aa_run --spend`` run, the unchanged bundle root, and exit 2 on an unknown flag for every
offline CLI.

Fail-first (D-22): only stdlib, pytest, ``openai`` and ``httpx`` are imported at module level; every
package name is resolved inside a test, and every outcome (argparse's SystemExit included) is captured
and asserted on. No test reads a real env file (D-24): an autouse fixture points each module's
``DEFAULT_V1_ENV_PARITY`` at an absent temp path, and the loaders and client builders are stubbed.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import httpx
import openai
import pytest

_ENV_MODULES = (
    "databasise.parity.run_arm",
    "databasise.parity.build_hipporag_index",
    "databasise.parity.storage_audit",
    "databasise.parity.run_comparison",
    "databasise.parity.run_cross_modality",
    "databasise.parity.v1_arm",
    "databasise.foreign.v1_corpus_adapter",
    "databasise.eval.remint",
    "databasise.eval.corpus_ingest",
    "databasise.eval.aa_run",
)

_RUN_ARM = "databasise.parity.run_arm"
_AA_RUN = "databasise.eval.aa_run"
_REMINT = "databasise.eval.remint"


@pytest.fixture(autouse=True)
def _no_real_env_file(tmp_path, monkeypatch):
    """D-24: no case here can open the real ``v1/.env.parity``."""
    absent = tmp_path / "absent.env.parity"
    for name in _ENV_MODULES:
        module = importlib.import_module(name)
        if hasattr(module, "DEFAULT_V1_ENV_PARITY"):
            monkeypatch.setattr(module, "DEFAULT_V1_ENV_PARITY", absent)
    return absent


# --------------------------------------------------------------------------------------------- #
# The errors: name -> (module, constructor taking the class)
# --------------------------------------------------------------------------------------------- #


def _api_connection_error(cls):
    return cls(request=httpx.Request("POST", "http://llm.invalid/v1/chat"))


_ERRORS = {
    "MissingParityEnvKeyError": ("databasise.clients.builder", lambda c: c(["LLM_MODEL"])),
    "UnparseableProviderRoutingError": ("databasise.clients.builder", lambda c: c("OPENAI_LLM_EXTRA_BODY", "{bad")),
    "EmptyQueryObjectError": ("databasise.seam.refusals", lambda c: c(None)),
    "FileNotFoundError": ("builtins", lambda c: c("no such file")),
    "BundleDriftError": ("databasise.eval.bundle", lambda c: c("bundle@v1", "aaa", "bbb")),
    "CorpusDriftError": ("databasise.parity.corpus", lambda c: c("the fixture drifted")),
    "MissingTargetFamilyError": ("databasise.eval.bundle", lambda c: c("a question has no gold document ids")),
    "APIConnectionError": ("openai", _api_connection_error),
    "UnresolvedJudgeIdentityError": (_REMINT, lambda c: c()),
    # aa_run's named ValueError subclasses and refusals
    "SplitNotCalibratableError": (_AA_RUN, lambda c: c("holdout", reason="reserved")),
    "NoMintedBundleError": (_AA_RUN, lambda c: c("no minted bundle found")),
    "MissingTargetFamilyCoverageError": (_AA_RUN, lambda c: c("family lacks targets")),
    "QuestionNotInBundleError": (_AA_RUN, lambda c: c("question q9 is not in the bundle")),
    "EmptyGoldDocumentIdsError": (_AA_RUN, lambda c: c("no gold document ids")),
    "GoldPassageMappingError": (_AA_RUN, lambda c: c("evidence has no document key")),
    "UnpairedScoresError": ("databasise.eval.calibration", lambda c: c("the two runs differ")),
    "EmptyPairedDifferencesError": ("databasise.eval.calibration", lambda c: c("no differences")),
    "UnparseableJudgeVerdictError": (_AA_RUN, lambda c: c("maybe")),
    "UnusableFloorError": ("databasise.eval.calibration", lambda c: c("a node reports a cache hit")),
    "UnkeyableFloorError": (_AA_RUN, lambda c: c("gold_passage")),
    "ConfoundedPassError": (_AA_RUN, lambda c: c("q1", partial=True, degraded=False)),
    "EmptyEvalIndexError": (_AA_RUN, lambda c: c("lightrag", "chunks", Path("/nowhere"))),
}


def _make_error(name):
    module_name, build = _ERRORS[name]
    cls = getattr(importlib.import_module(module_name), name, None)
    assert cls is not None, f"{module_name} has no {name}"
    return build(cls)


# --------------------------------------------------------------------------------------------- #
# The CLIs: where each named failure is injected
# --------------------------------------------------------------------------------------------- #


async def _async_none(*_args, **_kwargs):
    return None


def _none(*_args, **_kwargs):
    return None


def _empty_env(*_args, **_kwargs):
    return {}


def _stub_clients(*_args, **_kwargs):
    return {"llm": None}


def _object(**_kwargs):
    return object()


async def _judge_identity(*_args, **_kwargs):
    return "judge-model@1"


def _minted(*_args, **_kwargs):
    return SimpleNamespace(version="bundle@v2", judge_instance="judge-model@1")


_SPECS = {
    "run_arm": {
        "module": _RUN_ARM,
        "argv": ["--arm", "naive", "--query", "q", "--spend"],
        "env": (_RUN_ARM, "_load_env_file"),
        "clients": (_RUN_ARM, "_build_clients"),
        "work": (_RUN_ARM, "run_arm"),
        "base": {(_RUN_ARM, "_load_env_file"): _empty_env},
    },
    "storage_audit": {
        "module": "databasise.parity.storage_audit",
        "argv": ["--arm", "naive", "--spend"],
        "env": (_RUN_ARM, "_load_env_file"),
        "clients": (_RUN_ARM, "_build_clients"),
        "work": ("databasise.parity.storage_audit", "run_audit"),
        "base": {(_RUN_ARM, "_load_env_file"): _empty_env},
    },
    "run_comparison": {
        "module": "databasise.parity.run_comparison",
        "argv": ["--arm", "naive", "--spend"],
        "work": ("databasise.parity.run_comparison", "compare_arm_on_query"),
    },
    "run_cross_modality": {
        "module": "databasise.parity.run_cross_modality",
        "argv": ["--spend"],
        "work": ("databasise.parity.run_cross_modality", "run_cross_modality"),
    },
    "aa_run": {
        "module": _AA_RUN,
        "argv": ["--split", "dev", "--spend"],
        "env": (_AA_RUN, "_load_env_file"),
        "clients": (_AA_RUN, "_build_clients"),
        "work": (_AA_RUN, "calibrate_family"),
        "base": {
            (_AA_RUN, "_load_env_file"): _empty_env,
            (_AA_RUN, "_build_clients"): _stub_clients,
            (_AA_RUN, "Databasise"): _object,
            (_AA_RUN, "MultiNamespaceVectorStore"): _object,
        },
    },
    "remint": {
        "module": _REMINT,
        "argv": ["--spend"],
        "env": (_REMINT, "_load_env_file"),
        "clients": (_REMINT, "_build_clients"),
        "work": (_REMINT, "resolve_judge_identity"),
        "base": {
            (_REMINT, "_load_env_file"): _empty_env,
            (_REMINT, "_build_clients"): _stub_clients,
            (_REMINT, "resolve_judge_identity"): _judge_identity,
            (_REMINT, "remint"): _minted,
        },
    },
}

_PARITY = [
    ("MissingParityEnvKeyError", "clients"),
    ("UnparseableProviderRoutingError", "clients"),
    ("FileNotFoundError", "env"),
    ("EmptyQueryObjectError", "work"),
    ("CorpusDriftError", "work"),
    ("APIConnectionError", "work"),
]
_AA_RUN_NAMED = [
    "SplitNotCalibratableError",
    "NoMintedBundleError",
    "MissingTargetFamilyCoverageError",
    "QuestionNotInBundleError",
    "EmptyGoldDocumentIdsError",
    "GoldPassageMappingError",
    "UnpairedScoresError",
    "EmptyPairedDifferencesError",
    "UnparseableJudgeVerdictError",
    "UnusableFloorError",
    "UnkeyableFloorError",
    "ConfoundedPassError",
    "EmptyEvalIndexError",
]

_CASES = (
    [(cli, name, target) for cli in ("run_arm", "storage_audit") for name, target in _PARITY]
    + [(cli, name, "work") for cli in ("run_comparison", "run_cross_modality") for name, _ in _PARITY]
    + [(cli, name, target) for cli in ("aa_run",) for name, target in _PARITY]
    + [
        ("aa_run", "BundleDriftError", (_AA_RUN, "load_bundle")),
        ("aa_run", "MissingTargetFamilyError", "work"),
    ]
    + [("aa_run", name, "work") for name in _AA_RUN_NAMED]
    + [
        ("remint", "MissingParityEnvKeyError", "clients"),
        ("remint", "UnparseableProviderRoutingError", "clients"),
        ("remint", "FileNotFoundError", "env"),
        ("remint", "CorpusDriftError", (_REMINT, "load_snapshot")),
        ("remint", "BundleDriftError", (_REMINT, "remint")),
        ("remint", "MissingTargetFamilyError", (_REMINT, "remint")),
        ("remint", "APIConnectionError", "work"),
        ("remint", "UnresolvedJudgeIdentityError", "work"),
    ]
)


def _replace(monkeypatch, target, replacement):
    module_name, attr = target
    module = importlib.import_module(module_name)
    assert hasattr(module, attr), f"{module_name} has no {attr}"
    monkeypatch.setattr(module, attr, replacement)


def _raising_like(original, error):
    if inspect.iscoroutinefunction(original):

        async def _fake(*_args, **_kwargs):
            raise error

        return _fake

    def _fake(*_args, **_kwargs):
        raise error

    return _fake


def _async_if_needed(module_name, attr, replacement):
    """Keep a stub awaitable when the original is a coroutine function."""
    original = getattr(importlib.import_module(module_name), attr)
    if inspect.iscoroutinefunction(original) and not inspect.iscoroutinefunction(replacement):

        async def _wrapped(*args, **kwargs):
            return replacement(*args, **kwargs)

        return _wrapped
    return replacement


def _point_stores_at(tmp_path, monkeypatch, module):
    import_index = importlib.import_module("databasise.parity.import_index")
    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", tmp_path / "store")
    for attr in ("_EVAL_INGEST_STORE_ROOT",):
        if hasattr(module, attr):
            monkeypatch.setattr(module, attr, tmp_path / "eval")
    if hasattr(module, "_RESULTS_DIR"):
        monkeypatch.setattr(module, "_RESULTS_DIR", tmp_path / "results")


def _call(module, argv):
    try:
        return module.main(list(argv))
    except BaseException as caught:  # noqa: BLE001 - argparse raises SystemExit; an unmapped error is the failure
        return caught


@pytest.mark.parametrize(
    ("cli", "error_name", "target"),
    [pytest.param(c, e, t, id=f"{c}-{e}-{t if isinstance(t, str) else t[1]}") for c, e, t in _CASES],
)
def test_a_named_failure_is_one_stderr_line_and_exit_one(cli, error_name, target, tmp_path, monkeypatch, capsys):
    spec = _SPECS[cli]
    module = importlib.import_module(spec["module"])
    _point_stores_at(tmp_path, monkeypatch, module)

    for stub_target, stub in spec.get("base", {}).items():
        _replace(monkeypatch, stub_target, _async_if_needed(*stub_target, stub))

    resolved = spec.get(target, spec["work"]) if isinstance(target, str) else target
    original = getattr(importlib.import_module(resolved[0]), resolved[1])
    _replace(monkeypatch, resolved, _raising_like(original, _make_error(error_name)))

    outcome = _call(module, spec["argv"])

    err = capsys.readouterr().err
    lines = [line for line in err.splitlines() if line.strip()]
    assert outcome == 1, f"main returned {outcome!r}; stderr: {err!r}"
    assert len(lines) == 1, lines
    assert error_name in lines[0], lines
    assert "Traceback" not in err


def test_n_resamples_zero_exits_two_before_any_client(tmp_path, monkeypatch):
    aa_run = importlib.import_module(_AA_RUN)
    _point_stores_at(tmp_path, monkeypatch, aa_run)
    built: list[str] = []

    def _build(*_args, **_kwargs):
        built.append("clients")
        return {"llm": None}

    monkeypatch.setattr(aa_run, "_load_env_file", _empty_env)
    monkeypatch.setattr(aa_run, "_build_clients", _build)
    monkeypatch.setattr(aa_run, "Databasise", _object)
    monkeypatch.setattr(aa_run, "MultiNamespaceVectorStore", _object)

    outcome = _call(aa_run, ["--split", "dev", "--n-resamples", "0", "--spend"])

    assert isinstance(outcome, SystemExit) and outcome.code == 2, repr(outcome)
    assert built == []


class _LoopBoundClient:
    """Binds to the loop of its first awaited call and raises on any other loop, as a client whose
    httpx transport was opened on a loop that ``asyncio.run`` has since closed does."""

    def __init__(self):
        self.loop = None
        self.calls = 0

    async def chat(self, messages, **kwargs):
        running = asyncio.get_running_loop()
        if self.loop is None:
            self.loop = running
        elif self.loop is not running:
            raise openai.APIConnectionError(message="Event loop is closed", request=httpx.Request("POST", "http://x"))
        self.calls += 1
        return None


def test_a_two_family_spend_run_uses_one_event_loop(tmp_path, monkeypatch, capsys):
    aa_run = importlib.import_module(_AA_RUN)
    calibration = importlib.import_module("databasise.eval.calibration")
    _point_stores_at(tmp_path, monkeypatch, aa_run)
    client = _LoopBoundClient()
    families: list[str] = []

    async def _calibrate(**kwargs):
        families.append(kwargs["family_name"])
        await kwargs["llm_client"].chat([{"role": "user", "content": "ping"}])
        return SimpleNamespace(
            identity=calibration.NullIdentity("bundle@v1", "T1", "m", "cache-bypassed", "sequential"),
            floor=0.25,
            n_questions=3,
            n_resamples=10,
            seed=None,
            wiring_instance_hash=f"sha256:{'c' * 64}",
        )

    monkeypatch.setattr(aa_run, "_load_env_file", _empty_env)
    monkeypatch.setattr(aa_run, "_build_clients", lambda *_a, **_k: {"llm": client})
    monkeypatch.setattr(aa_run, "Databasise", _object)
    monkeypatch.setattr(aa_run, "MultiNamespaceVectorStore", _object)
    monkeypatch.setattr(aa_run, "calibrate_family", _calibrate)

    outcome = _call(aa_run, ["--split", "dev", "--spend"])

    captured = capsys.readouterr()
    assert outcome == 0, f"main returned {outcome!r}; stderr: {captured.err!r}"
    assert families == ["gold_passage", "answer_level"], families
    assert client.calls == 2


def test_the_committed_bundle_root_is_unchanged():
    remint = importlib.import_module(_REMINT)
    package_dir = Path(remint.__file__).resolve().parent.parent
    assert remint._COMMITTED_BUNDLE_ROOT == package_dir / "evidence" / "eval-bundles"
    assert remint._COMMITTED_BUNDLE_ROOT.as_posix().endswith("databasise/evidence/eval-bundles")


_OFFLINE_CLIS = [
    "databasise.parity.build_hipporag_index",
    "databasise.eval.remint",
    "databasise.parity.run_arm",
    "databasise.parity.storage_audit",
    "databasise.parity.run_comparison",
    "databasise.parity.run_cross_modality",
    "databasise.parity.v1_arm",
    "databasise.eval.corpus_ingest",
    "databasise.eval.aa_run",
    "databasise.parity.import_index",
    "databasise.tools.check_import_boundary",
    "databasise.evidence.parity_report",
    "databasise.evidence.falsifier2",
    "databasise.evidence.f07_report",
]


@pytest.mark.parametrize("module_name", [pytest.param(m, id=m.rsplit(".", 1)[1]) for m in _OFFLINE_CLIS])
def test_every_offline_cli_exits_two_on_an_unknown_flag(module_name, tmp_path, monkeypatch):
    module = importlib.import_module(module_name)
    import_index = importlib.import_module("databasise.parity.import_index")
    monkeypatch.setattr(import_index, "DEFAULT_STORE_ROOT", tmp_path / "store")

    def _boom(*_args, **_kwargs):
        raise AssertionError("work started on a bad argument")

    # Pitfall 12: import_index must reject the flag before it imports or verifies anything.
    for name in ("import_v1_index", "verify_import", "store_lock"):
        if module_name.endswith("import_index") and hasattr(module, name):
            monkeypatch.setattr(module, name, _boom)

    outcome = _call(module, ["--no-such-flag"])

    assert isinstance(outcome, SystemExit) and outcome.code == 2, repr(outcome)
    assert not (tmp_path / "store").exists()

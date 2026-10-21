"""Shared CLI helper (15-02, D-03, D-10): the exit table, the one-line refusal, the refusal tuple, the
``positive_int`` argparse type and the selector-vs-named-wiring check."""

from __future__ import annotations

import argparse
import io
import subprocess
import sys

import pytest

from databasise import cli


def _refuse(exc):
    stream = io.StringIO()
    code = cli.refuse(exc, stream=stream)
    return code, stream.getvalue()


def test_refuse_prints_one_line_with_the_class_name_and_returns_1():
    code, out = _refuse(KeyError("x"))
    assert code == 1
    assert out.count("\n") == 1 and out.startswith("KeyError: ")


def test_refuse_does_not_repeat_a_class_name_the_message_already_carries():
    class FooError(Exception):
        pass

    _, out = _refuse(FooError("FooError: already named"))
    assert out == "FooError: already named\n"


def test_refuse_collapses_multiline_text_and_truncates():
    _, out = _refuse(RuntimeError("line\n" * 800))
    assert out.count("\n") == 1
    assert len(out.rstrip("\n")) <= len("RuntimeError: ") + 500


def test_offline_refusals_never_contains_bare_valueerror_or_runtimeerror():
    import openai

    from databasise.store_lock import StoreLockedError

    class Extra(Exception):
        pass

    refusals = cli.offline_refusals(Extra)
    assert ValueError not in refusals and RuntimeError not in refusals
    assert FileNotFoundError in refusals and StoreLockedError in refusals and openai.OpenAIError in refusals
    assert refusals[-1] is Extra


def test_importing_cli_loads_no_seam_module():
    code = "import sys, databasise.cli; sys.exit(1 if 'databasise.seam.engine' in sys.modules else 0)"
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0


def test_positive_int_rejects_zero_at_parse_time():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=cli.positive_int)
    assert parser.parse_args(["--n", "3"]).n == 3
    for bad in ("0", "-1"):
        with pytest.raises(SystemExit) as caught:
            parser.parse_args(["--n", bad])
        assert caught.value.code == 2


def test_check_named_arm_accepts_a_selector_that_resolves_to_the_named_arm():
    from databasise.parts.registry import default_registry
    from databasise.seam.selectors import Selector

    registry = default_registry()
    assert cli.check_named_arm(Selector(capability=["reads_vector"]), arm_id="naive", registry=registry) is None
    assert (
        cli.check_named_arm(Selector(capability=["reads_graph", "reads_kv"]), arm_id="hipporag", registry=registry)
        is None
    )


def test_check_named_arm_refuses_a_mismatch_by_name():
    from databasise.parts.registry import default_registry
    from databasise.seam.selectors import Selector

    with pytest.raises(cli.ArmSelectorMismatchError) as caught:
        cli.check_named_arm(Selector(capability=["reads_vector"]), arm_id="hipporag", registry=default_registry())
    text = str(caught.value)
    assert "hipporag" in text and "naive" in text
    assert "hipporag-base" in text and "lightrag-base" in text


def test_check_named_arm_refuses_an_unknown_arm_by_name():
    from databasise.parts.registry import default_registry
    from databasise.seam.selectors import Selector

    with pytest.raises(cli.ArmSelectorMismatchError) as caught:
        cli.check_named_arm(Selector(capability=["reads_vector"]), arm_id="nope", registry=default_registry())
    assert "nope" in str(caught.value)

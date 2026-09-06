"""04-01-PLAN.md Task 3: the envelope is closed at every nesting depth (D-05, Pitfall 7) — proven
structurally, parametrized by introspecting ``databasise.seam.envelope`` itself rather than a
hand-maintained list of its model classes, and against the internal-identity vocabulary derived
from ``databasise.runner.trace.RunRecord``/``NodeTrace``'s own dataclass fields rather than
retyped as literals here.
"""

from __future__ import annotations

import dataclasses
import inspect
import re
import typing

import pydantic
import pytest

from databasise.runner.trace import NodeTrace, RunRecord
from databasise.seam import envelope as envelope_module
from databasise.seam.envelope import ResponseEnvelope

_STRICT_BASE = envelope_module._StrictModel


def _model_classes_defined_in_module(module) -> list[type[pydantic.BaseModel]]:
    """Every ``pydantic.BaseModel`` subclass defined directly in ``module`` — never a
    hand-maintained list, so a nested model 04-02/04-04 adds later is covered automatically."""
    return [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, pydantic.BaseModel) and obj.__module__ == module.__name__
    ]


_ENVELOPE_MODEL_CLASSES = _model_classes_defined_in_module(envelope_module)


def test_every_model_defined_in_the_envelope_module_inherits_the_strict_base():
    for model_cls in _ENVELOPE_MODEL_CLASSES:
        assert issubclass(model_cls, _STRICT_BASE), (
            f"{model_cls.__name__} does not inherit the module's shared strict base"
        )


@pytest.mark.parametrize(
    "model_cls", _ENVELOPE_MODEL_CLASSES, ids=[c.__name__ for c in _ENVELOPE_MODEL_CLASSES]
)
def test_an_unexpected_keyword_is_rejected_at_every_nesting_depth(model_cls):
    with pytest.raises(pydantic.ValidationError):
        model_cls(__unexpected_key_never_declared__="leak")


def test_response_envelope_construction_raises_on_an_unexpected_top_level_keyword():
    with pytest.raises(pydantic.ValidationError):
        ResponseEnvelope(
            answer="x",
            depth_label="stage",
            partial=False,
            degraded=False,
            not_a_real_field="leak",
        )


def test_assigning_to_a_field_on_a_constructed_envelope_raises():
    envelope = ResponseEnvelope(answer="x", depth_label="stage", partial=False, degraded=False)
    with pytest.raises(pydantic.ValidationError):
        envelope.answer = "y"


# --------------------------------------------------------------------------------------------- #
# The envelope's declared field set carries no internal-identity name, derived from RunRecord/
# NodeTrace's own dataclass fields at test time — never retyped as literals here.
# --------------------------------------------------------------------------------------------- #

_IDENTITY_NAME_PATTERN = re.compile(r"(^|_)(id|hash)(_|$)")


def _identity_field_names(dataclass_type) -> set[str]:
    return {f.name for f in dataclasses.fields(dataclass_type) if _IDENTITY_NAME_PATTERN.search(f.name)}


def _nested_model_classes(annotation) -> list[type[pydantic.BaseModel]]:
    """Every ``pydantic.BaseModel`` class reachable from a field's type annotation through
    ``Optional``/``list`` wrapping — the only generic shapes this envelope module uses."""
    origin = typing.get_origin(annotation)
    if origin is None:
        if inspect.isclass(annotation) and issubclass(annotation, pydantic.BaseModel):
            return [annotation]
        return []
    found: list[type[pydantic.BaseModel]] = []
    for arg in typing.get_args(annotation):
        found.extend(_nested_model_classes(arg))
    return found


def _all_declared_field_names(model_cls, _seen: set | None = None) -> set[str]:
    if _seen is None:
        _seen = set()
    if model_cls in _seen:
        return set()
    _seen.add(model_cls)
    names: set[str] = set(model_cls.model_fields.keys())
    for field_info in model_cls.model_fields.values():
        for nested_cls in _nested_model_classes(field_info.annotation):
            names |= _all_declared_field_names(nested_cls, _seen)
    return names


def test_no_envelope_field_name_matches_the_internal_identity_vocabulary():
    forbidden = _identity_field_names(RunRecord) | _identity_field_names(NodeTrace)
    # Sanity: the derivation actually found the identity fields we expect it to find — proves the
    # regex-over-dataclass-fields approach is doing real work, not vacuously passing on an empty set.
    assert {"run_id", "wiring_id", "wiring_instance_hash", "arm_id", "node_id", "instance_hash"} <= forbidden

    declared = _all_declared_field_names(ResponseEnvelope)
    leaked = declared & forbidden
    assert not leaked, f"envelope field(s) collide with internal-identity vocabulary: {leaked}"

"""The enforcement half of ``databasise/parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md``
(05-05-PLAN.md Task 2).

Going red means a published across-the-boundary value moved (a `Part`'s declared identity/effects/
scope, an `AdmissionRecord` field, or the driver script's stdin/stdout protocol) and a version bump
per CONTRACT §0 plus a fresh admission record is owed. **This is not a lint.** Silencing a red run
by editing the pinned literal below to match the new live value — without also bumping
``name_at_version`` and re-running admission — defeats the entire purpose of pinning it; see the
rule document's §5 for the same statement in prose.

This file pins nothing that lives inside the subprocess or inside v1's own venv: no assertion here
reaches into v1's facade construction, a chunking parameter, a prompt, or any v1-internal module.
``environment_hash`` is a deliberate partial exception — see its own comment below.
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path
from typing import Any

from databasise.parts.registry import default_registry

_HERE = Path(__file__).resolve()
_DATABASISE_ROOT = _HERE.parents[3]
_RULE_DOCUMENT_PATH = _DATABASISE_ROOT / "parts_core" / "lightrag" / "OPAQUE-BOUNDARY-RULE.md"
_DRIVER_SCRIPT_PATH = _DATABASISE_ROOT / "foreign" / "v1_corpus_driver_script.py"

_INGEST_NAME_AT_VERSION = "lightrag/full-ingest@0.1.0"
_DELETE_NAME_AT_VERSION = "lightrag/full-delete@0.1.0"

_registry = default_registry()
_INGEST_PART = _registry.get(_INGEST_NAME_AT_VERSION)
_DELETE_PART = _registry.get(_DELETE_NAME_AT_VERSION)

# Every field databasise.parts.admission.AdmissionRecord declares today. A field added to (or
# removed from) that dataclass changes this set and fails _assert_admission_field_set_unchanged
# below before it ever reaches an unclassified, silently-widened boundary.
_ADMISSION_FIELD_NAMES = frozenset(
    {
        "part_name_at_version",
        "entry_path",
        "storage",
        "wall_clock_ceiling_seconds",
        "wall_clock_ceiling_basis",
        "feed_tier",
        "ttl_days",
        "network_namespace",
        "environment_hash",
        "manifest_source",
        "verdicts",
    }
)


def _assert_admission_field_set_unchanged(record: Any) -> None:
    live_names = {f.name for f in dataclasses.fields(record)}
    assert live_names == _ADMISSION_FIELD_NAMES, (
        f"AdmissionRecord's field set changed to {sorted(live_names)!r}; a new or removed field "
        "is an unclassified boundary widening until this test's _ADMISSION_FIELD_NAMES and "
        "OPAQUE-BOUNDARY-RULE.md are both updated to account for it"
    )


def _part_boundary(part: Any) -> dict[str, Any]:
    """The six across-the-boundary ``Part`` fields (never ``body`` — a callable, not a pinnable
    literal — and never ``admission``, projected separately by :func:`_admission_boundary`).
    """
    return {
        "name_at_version": part.name_at_version,
        "kind": part.kind,
        "structural_depth": part.structural_depth,
        "effects": tuple(part.effects),
        "upstream_ref": part.upstream_ref,
        "artifact_scope": part.artifact_scope,
    }


def _admission_boundary(record: Any) -> dict[str, Any]:
    """Every ``AdmissionRecord`` field except ``environment_hash`` (checked separately, see the
    module docstring and the rule document's §2 — pinning its computed digest value literally
    would turn a routine ``uv sync`` bump inside v1's own venv into a false-positive boundary
    violation). ``verdicts`` is pinned by ``(condition, verdict)`` pair only — never by the
    accompanying ``evidence`` prose, which is free to reword.
    """
    _assert_admission_field_set_unchanged(record)
    return {
        "part_name_at_version": record.part_name_at_version,
        "entry_path": record.entry_path,
        "storage": record.storage,
        "wall_clock_ceiling_seconds": record.wall_clock_ceiling_seconds,
        "wall_clock_ceiling_basis": record.wall_clock_ceiling_basis,
        "feed_tier": record.feed_tier,
        "ttl_days": record.ttl_days,
        "network_namespace": record.network_namespace,
        "manifest_source": record.manifest_source,
        "verdicts": tuple((verdict.condition, verdict.verdict) for verdict in record.verdicts),
    }


def _full_boundary(part: Any) -> dict[str, Any]:
    """The comparison helper the negative control (below) proves has teeth: every pinned
    across-the-boundary value for one part, merged from its ``Part`` fields and its
    ``AdmissionRecord`` fields into one dict comparable against a literal pin by equality.
    """
    boundary = _part_boundary(part)
    boundary.update(_admission_boundary(part.admission))
    return boundary


# Literal pinned copies (05-05-PLAN.md Task 2.B) — a diff to any value below without a
# corresponding name_at_version bump and fresh admission record is exactly what this test exists
# to catch.
PINNED_INGEST_BOUNDARY = {
    "name_at_version": "lightrag/full-ingest@0.1.0",
    "kind": "opaque",
    "structural_depth": "opaque",
    "effects": ("calls_llm", "writes_artifact", "reads_kv", "reads_graph"),
    "upstream_ref": "v1/lightrag/pipeline.py",
    "artifact_scope": "quarantined",
    "part_name_at_version": "lightrag/full-ingest@0.1.0",
    "entry_path": "in-process opaque core, hosted as a subprocess under v1's pinned interpreter",
    "storage": "machine",
    "wall_clock_ceiling_seconds": 900.0,
    "wall_clock_ceiling_basis": (
        "one document at a time through v1's own extraction pipeline over the 20-document "
        "HotpotQA fixture (05-RESEARCH.md); the machine declares this ceiling, v1 never "
        "self-reports one"
    ),
    "feed_tier": "document",
    "ttl_days": 90,
    "network_namespace": (
        "denied-by-construction: the machine's own OpenAI-compatible base_url and key are "
        "injected into the subprocess env via LLM_BINDING_HOST/EMBEDDING_BINDING_HOST; the "
        "subprocess configures no independent outbound endpoint"
    ),
    "manifest_source": "code-inspected",
    "verdicts": (
        (1, "satisfied"),
        (2, "satisfied"),
        (3, "satisfied by construction"),
        (4, "satisfied"),
        (5, "satisfied"),
        (6, "satisfied"),
        (7, "satisfied (machine-side obligation)"),
        (8, "open — accepted as a scope boundary, not a clean yes"),
        (9, "partially satisfied — spend reported as unbudgetable, never estimated"),
        (10, "satisfied (machine-side obligation)"),
        (11, "satisfied by construction"),
    ),
}

PINNED_DELETE_BOUNDARY = {
    "name_at_version": "lightrag/full-delete@0.1.0",
    "kind": "opaque",
    "structural_depth": "opaque",
    "effects": ("mutates_store", "reads_kv", "reads_graph"),
    "upstream_ref": "v1/lightrag/lightrag.py",
    "artifact_scope": None,
    "part_name_at_version": "lightrag/full-delete@0.1.0",
    "entry_path": "in-process opaque core, hosted as a subprocess under v1's pinned interpreter",
    "storage": "machine",
    "wall_clock_ceiling_seconds": 300.0,
    "wall_clock_ceiling_basis": (
        "v1's own deletion path (adelete_by_doc_id) performs graph and vector surgery plus a "
        "bounded rebuild over surviving sources for a partially-affected entity/relation; the "
        "machine declares this ceiling, v1 never self-reports one"
    ),
    "feed_tier": "n/a — this port consumes a document id, never a machine-produced feed",
    "ttl_days": 90,
    "network_namespace": (
        "denied-by-construction: the same machine-injected LLM_BINDING_HOST/EMBEDDING_BINDING_HOST "
        "env the ingest driver script uses (v1_corpus_driver_script.py's shared _build_rag/"
        "_llm_model_func) — the delete driver configures no independent outbound endpoint, even "
        "when a partial-rebuild path reaches the LLM"
    ),
    "manifest_source": "code-inspected",
    "verdicts": (
        (1, "satisfied"),
        (2, "satisfied"),
        (3, "satisfied by construction"),
        (4, "satisfied"),
        (5, "satisfied"),
        (6, "satisfied"),
        (7, "satisfied (machine-side obligation)"),
        (8, "open — accepted as a scope boundary, not a clean yes"),
        (9, "partially satisfied — spend always reported as unbudgetable, never estimated"),
        (10, "satisfied (machine-side obligation)"),
        (11, "satisfied by construction"),
    ),
}

# The driver script's protocol (05-05-PLAN.md Task 2.C): one entry per operation the driver
# dispatches on, each carrying the exact stdin key set it reads off `job` and the exact stdout key
# set the dict it returns carries — derived live via AST walk below and asserted equal to this pin.
PINNED_DRIVER_PROTOCOL = {
    "ingest": {
        "stdin": frozenset({"documents", "track_id", "working_dir", "file_paths", "docs_format"}),
        "stdout": frozenset({"track_id", "enqueued", "usage"}),
    },
    "delete": {
        "stdin": frozenset({"doc_id", "delete_llm_cache", "working_dir"}),
        "stdout": frozenset({"status", "doc_id", "message", "status_code", "file_path"}),
    },
    "entities": {
        "stdin": frozenset({"doc_id", "working_dir"}),
        "stdout": frozenset({"chunk_ids", "entities"}),
    },
    "entity_info": {
        "stdin": frozenset({"entity_names", "working_dir"}),
        "stdout": frozenset({"entities"}),
    },
    "status": {
        "stdin": frozenset({"track_id", "limit", "offset", "working_dir"}),
        "stdout": frozenset({"counts", "documents", "total"}),
    },
    "health": {
        "stdin": frozenset({"working_dir"}),
        "stdout": frozenset({"working_dir_present", "storages_initialized"}),
    },
}


class _UnresolvableProtocolFieldError(AssertionError):
    """The AST walk found a return-dict key it cannot determine statically (e.g. a ``**`` unpack)
    — a protocol field the check cannot see is a hole in the boundary, not an acceptable gap
    (05-05-PLAN.md Task 2.C).
    """


def _job_read_keys(func_node: ast.AsyncFunctionDef) -> set[str]:
    """Every string-literal key read off the ``job`` parameter inside ``func_node`` — both
    ``job["key"]`` (Subscript) and ``job.get("key", ...)`` (Call) forms.
    """
    keys: set[str] = set()
    for node in ast.walk(func_node):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "job"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            keys.add(node.slice.value)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "job"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            keys.add(node.args[0].value)
    return keys


def _returned_dict_keys(func_node: ast.AsyncFunctionDef) -> set[str]:
    """Every string-literal key of a dict literal in a ``return {...}`` statement inside
    ``func_node``. Raises :class:`_UnresolvableProtocolFieldError` naming the function if any
    ``return``'s dict literal cannot be read statically (a ``**`` unpack or a non-constant key) —
    never silently skipped.
    """
    keys: set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            for key_node in node.value.keys:
                if key_node is None:
                    raise _UnresolvableProtocolFieldError(
                        f"{func_node.name}'s return dict uses a ** unpack — its keys cannot be "
                        "determined statically by this AST walk"
                    )
                if not (isinstance(key_node, ast.Constant) and isinstance(key_node.value, str)):
                    raise _UnresolvableProtocolFieldError(
                        f"{func_node.name}'s return dict has a non-string-literal key "
                        f"({ast.dump(key_node)}) — cannot be determined statically"
                    )
                keys.add(key_node.value)
    return keys


def _derive_driver_protocol(script_path: Path) -> dict[str, dict[str, frozenset[str]]]:
    """Walk ``script_path``'s AST (never import it — it imports ``lightrag``, which is not
    installed in this venv) to derive, live, the same shape :data:`PINNED_DRIVER_PROTOCOL` pins:
    one entry per operation the ``_run()`` dispatcher recognizes, each carrying the stdin/stdout
    key sets of the ``_run_<op>`` function it calls.
    """
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    run_functions: dict[str, ast.AsyncFunctionDef] = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("_run_")
    }
    dispatcher = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_run"
    )

    op_to_function: dict[str, str] = {}
    for node in ast.walk(dispatcher):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "op"
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and isinstance(test.comparators[0].value, str)
        ):
            continue
        op_name = test.comparators[0].value
        for stmt in node.body:
            if not (isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Await)):
                continue
            call = stmt.value.value
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                op_to_function[op_name] = call.func.id

    protocol: dict[str, dict[str, frozenset[str]]] = {}
    for op_name, func_name in op_to_function.items():
        func_node = run_functions[func_name]
        protocol[op_name] = {
            "stdin": frozenset(_job_read_keys(func_node)),
            "stdout": frozenset(_returned_dict_keys(func_node)),
        }
    return protocol


def test_ingest_part_boundary_matches_the_pin():
    assert _full_boundary(_INGEST_PART) == PINNED_INGEST_BOUNDARY


def test_delete_part_boundary_matches_the_pin():
    assert _full_boundary(_DELETE_PART) == PINNED_DELETE_BOUNDARY


def test_environment_hash_is_present_shaped_and_shared_between_both_ports():
    # Deliberately structural, not a literal-value pin — see the module docstring and
    # OPAQUE-BOUNDARY-RULE.md §2 for why the computed digest itself is not pinned.
    ingest_hash = _INGEST_PART.admission.environment_hash
    delete_hash = _DELETE_PART.admission.environment_hash
    assert ingest_hash and ingest_hash.startswith("sha256:")
    assert delete_hash and delete_hash.startswith("sha256:")
    assert ingest_hash == delete_hash, (
        "both ports launch under the same v1 closure — their independently-computed "
        "environment_hash values must agree"
    )


def test_driver_protocol_matches_the_pin():
    live = _derive_driver_protocol(_DRIVER_SCRIPT_PATH)
    assert live == PINNED_DRIVER_PROTOCOL


def test_driver_dispatches_on_exactly_the_pinned_operation_set():
    live = _derive_driver_protocol(_DRIVER_SCRIPT_PATH)
    assert set(live.keys()) == set(PINNED_DRIVER_PROTOCOL.keys())


def test_rule_document_and_check_agree():
    """The anti-drift assertion (05-05-PLAN.md Task 2.D): a value pinned by this check but absent
    from the rule document's prose is a rule nobody can read.
    """
    assert _RULE_DOCUMENT_PATH.exists()
    text = _RULE_DOCUMENT_PATH.read_text(encoding="utf-8")

    assert _INGEST_NAME_AT_VERSION in text
    assert _DELETE_NAME_AT_VERSION in text
    assert Path(__file__).name in text

    for identifier in PINNED_INGEST_BOUNDARY:
        assert identifier in text, (
            f"{identifier!r} is pinned by this check but does not appear anywhere in "
            f"{_RULE_DOCUMENT_PATH.name} — the prose and the check have drifted apart"
        )


def test_the_comparison_has_teeth_a_mutated_part_copy_differs_from_the_pin():
    """Negative control (05-05-PLAN.md Task 2.E): mutate a copy of the live ingest `Part` — never
    the registry entry itself — and prove :func:`_full_boundary` reports a difference, so the
    equality checks above are comparing something real rather than trivially comparing a value to
    itself.
    """
    mutated = dataclasses.replace(_INGEST_PART, effects=[*_INGEST_PART.effects, "net"])

    assert mutated is not _INGEST_PART
    assert _INGEST_PART.effects == ["calls_llm", "writes_artifact", "reads_kv", "reads_graph"], (
        "dataclasses.replace must not have mutated the live registry entry"
    )
    assert _full_boundary(mutated) != PINNED_INGEST_BOUNDARY
    assert _full_boundary(mutated)["effects"] != _full_boundary(_INGEST_PART)["effects"]

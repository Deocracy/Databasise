"""Op validation + Proof (spike 001). Standard library only.

Mirrors ops.schema.json field-for-field (checked by test_schema_mirror: the
schema file's constraints are re-read from disk and asserted against this
module's behaviour), then applies SCORE-IO-SPEC.md section 6 Proof checks:

  Schema | Evidence | Non-empty | Value type | Slug | Permission

Proof rejects an op, logs it, and continues: validate_ops returns one
verdict per op plus an overall verdict; it never raises on bad model output
(only on harness misuse such as an unknown file target).
"""

from __future__ import annotations

import datetime
import json
import re
from decimal import Decimal, InvalidOperation

MAX_OPS = 32

GRAPH_FIELDS = {"target", "s", "p", "o", "s_type", "o_type", "evidence"}
GRAPH_REQUIRED = ("target", "s", "p", "o", "evidence")
SQL_FIELDS = {"target", "subject", "attribute", "value", "value_type",
              "unit", "valid_from", "valid_to", "evidence"}
SQL_REQUIRED = ("target", "subject", "attribute", "value", "value_type",
                "evidence")
FOLIO_FIELDS = {"target", "slug", "kind", "title", "markdown", "supersedes"}
FOLIO_REQUIRED = ("target", "slug", "kind", "title", "markdown")
AGENT_FIELDS = {"target", "ask", "why"}
AGENT_REQUIRED = ("target", "ask", "why")

SLUG_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*\Z")
VALUE_TYPES = ("text", "number", "date")
FOLIO_KINDS = ("procedure", "doc")


def _str(v, lo: int, hi: int) -> bool:
    return isinstance(v, str) and lo <= len(v) <= hi


def _check_shape(op: dict) -> str | None:
    """Return an error string, or None if the op matches its target shape."""
    if not isinstance(op, dict):
        return "op is not an object"
    target = op.get("target")
    if target == "graph":
        if set(op) - GRAPH_FIELDS:
            return f"graph: extra fields {sorted(set(op) - GRAPH_FIELDS)}"
        for f in GRAPH_REQUIRED:
            if f not in op:
                return f"graph: missing {f}"
        if not _str(op["s"], 1, 512):
            return "graph: s length"
        if not _str(op["p"], 1, 128):
            return "graph: p length"
        if not _str(op["o"], 1, 512):
            return "graph: o length"
        for f in ("s_type", "o_type"):
            if f in op and not _str(op[f], 0, 64):
                return f"graph: {f} length"
        if not _valid_evidence_shape(op["evidence"]):
            return "graph: evidence shape"
    elif target == "sql":
        if set(op) - SQL_FIELDS:
            return f"sql: extra fields {sorted(set(op) - SQL_FIELDS)}"
        for f in SQL_REQUIRED:
            if f not in op:
                return f"sql: missing {f}"
        if not _str(op["subject"], 1, 512):
            return "sql: subject length"
        if not _str(op["attribute"], 1, 128):
            return "sql: attribute length"
        if not _str(op["value"], 1, 512):
            return "sql: value length"
        if op["value_type"] not in VALUE_TYPES:
            return "sql: value_type enum"
        for f in ("unit", "valid_from", "valid_to"):
            if f in op and not _str(op[f], 0, 32):
                return f"sql: {f} length"
        if not _valid_evidence_shape(op["evidence"]):
            return "sql: evidence shape"
    elif target == "folio":
        if set(op) - FOLIO_FIELDS:
            return f"folio: extra fields {sorted(set(op) - FOLIO_FIELDS)}"
        for f in FOLIO_REQUIRED:
            if f not in op:
                return f"folio: missing {f}"
        if not (isinstance(op["slug"], str) and len(op["slug"]) <= 64
                and SLUG_RE.match(op["slug"])):
            return "folio: slug pattern"
        if op["kind"] not in FOLIO_KINDS:
            return "folio: kind enum"
        if not _str(op["title"], 1, 128):
            return "folio: title length"
        if not _str(op["markdown"], 1, 4096):
            return "folio: markdown length"
        if ("supersedes" in op and not
                (isinstance(op["supersedes"], str)
                 and len(op["supersedes"]) <= 64
                 and SLUG_RE.match(op["supersedes"]))):
            return "folio: supersedes pattern"
    elif target == "agent":
        if set(op) - AGENT_FIELDS:
            return f"agent: extra fields {sorted(set(op) - AGENT_FIELDS)}"
        for f in AGENT_REQUIRED:
            if f not in op:
                return f"agent: missing {f}"
        if not _str(op["ask"], 1, 512):
            return "agent: ask length"
        if not _str(op["why"], 1, 256):
            return "agent: why length"
    else:
        return f"unknown target {target!r}"
    return None


def _valid_evidence_shape(ev) -> bool:
    return (isinstance(ev, list) and len(ev) == 2
            and all(isinstance(x, int) and not isinstance(x, bool) and x >= 0
                    for x in ev))


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def check_value_type(value_type: str, value: str) -> str | None:
    if value_type == "text":
        return None
    if value_type == "number":
        try:
            v = Decimal(value.strip())
        except InvalidOperation:
            return f"number does not parse: {value!r}"
        if not v.is_finite():
            return f"number not finite: {value!r}"
        return None
    if value_type == "date":
        v = value.strip()
        if re.fullmatch(r"\d{4}", v):
            y = int(v)
            return None if 1000 <= y <= 9999 else f"year out of range: {v!r}"
        try:
            datetime.date.fromisoformat(v)
            return None
        except ValueError:
            pass
        try:
            datetime.datetime.fromisoformat(v)
            return None
        except ValueError:
            return f"date does not parse as ISO 8601: {value!r}"
    return f"unknown value_type {value_type!r}"


def check_evidence(op: dict, content: str) -> str | None:
    start, end = op["evidence"]
    if not (0 <= start <= end <= len(content)):
        return f"evidence span [{start},{end}] outside content len {len(content)}"
    span = _norm(content[start:end])
    if op["target"] == "graph":
        probes = (op["s"], op["o"])
    else:
        probes = (op["subject"], op["value"])
    if not any(_norm(p) and _norm(p) in span for p in probes):
        return "evidence span contains neither subject nor value"
    return None


def check_non_empty(op: dict) -> str | None:
    if op["target"] == "graph":
        fields = ("s", "p", "o")
    elif op["target"] == "sql":
        fields = ("subject", "attribute", "value")
    else:
        return None
    for f in fields:
        if not op[f].strip():
            return f"{f} empty after trimming"
    return None


def prove_op(op: dict, file_set: tuple[str, ...], content: str,
             folio_slugs: set[str]) -> list[str]:
    """Proof checks for one op. Returns a list of rejection reasons ([] = pass)."""
    reasons: list[str] = []
    shape_err = _check_shape(op)
    if shape_err is not None:
        return [f"schema: {shape_err}"]
    if op["target"] not in file_set:
        reasons.append(f"permission: target {op['target']!r} not in file set")
        return reasons  # shape is known; further checks would mislead
    if op["target"] in ("graph", "sql"):
        for label, err in (("non-empty", check_non_empty(op)),
                           ("evidence", check_evidence(op, content))):
            if err is not None:
                reasons.append(f"{label}: {err}")
        if op["target"] == "sql":
            vt = check_value_type(op["value_type"], op["value"])
            if vt is not None:
                reasons.append(f"value-type: {vt}")
    elif op["target"] == "folio":
        if op["slug"] in folio_slugs and "supersedes" not in op:
            reasons.append(f"slug: {op['slug']!r} already in Folios store "
                           "without supersedes")
    return reasons


def validate_ops(obj: dict, file_set: tuple[str, ...], content: str,
                 folio_slugs: set[str] | None = None) -> dict:
    """Validate a model output object. Never raises on bad model output.

    Returns {"ok": bool, "verdicts": [{"index","target","pass","reasons"}]}.
    """
    folio_slugs = folio_slugs or set()
    verdicts: list[dict] = []
    if not isinstance(obj, dict) or set(obj) != {"ops"}:
        return {"ok": False, "verdicts": [],
                "error": "top-level must be exactly {\"ops\": [...]}"}
    ops = obj["ops"]
    if not isinstance(ops, list) or len(ops) > MAX_OPS:
        return {"ok": False, "verdicts": [],
                "error": f"ops must be a list of at most {MAX_OPS}"}
    ok = True
    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            verdicts.append({"index": i, "target": None, "pass": False,
                             "reasons": ["schema: op is not an object"]})
            ok = False
            continue
        reasons = prove_op(op, file_set, content, folio_slugs)
        verdicts.append({"index": i, "target": op.get("target"),
                         "pass": not reasons, "reasons": reasons})
        if reasons:
            ok = False
    return {"ok": ok, "verdicts": verdicts}


def load_schema_constraints(schema_path: str) -> dict:
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)

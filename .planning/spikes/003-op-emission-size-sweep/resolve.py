"""Quote evidence resolution + Proof for spike 003 v0.2 (stdlib only).

The model emits "quote": a verbatim substring of the section. The harness
resolves it to [start,end] offsets by locating its first occurrence in the
section after the SAME normalisation Proof uses (" ".join(s.lower().split()),
spike-001 ops_validate._norm), then runs Proof's existing span/value-type/
non-empty/shape checks on the resolved span. A quote that cannot be located
is a rejection with reason "quote: not found in section".

Offset mapping: normalise with a per-character original-index map so the
resolved span indexes the original (unnormalised) content, exactly what
Proof's check_evidence expects.
"""

from __future__ import annotations


def _norm_map(content: str):
    """Return (norm_text, origins) where origins[i] is the original index of
    norm_text[i]. Mirrors " ".join(content.lower().split()): tokens are
    maximal non-whitespace runs, lowercased per character, joined with one
    space whose origin is the preceding token's last index."""
    norm: list[str] = []
    origins: list[int] = []
    i, n = 0, len(content)
    first = True
    while i < n:
        if content[i].isspace():
            i += 1
            continue
        j = i
        while j < n and not content[j].isspace():
            j += 1
        token = content[i:j]
        lowered = token.lower()
        if len(lowered) != len(token):
            # lower() expanded a character (e.g. U+0130); mapping would be
            # ambiguous -- refuse rather than misattribute offsets.
            raise ValueError(f"non-1:1 lowercase in token {token!r}")
        if not first:
            norm.append(" ")
            origins.append(j - 1)
        for k, ch in enumerate(lowered):
            norm.append(ch)
            origins.append(i + k)
        first = False
        i = j
    return "".join(norm), origins


def resolve_quote(quote, content: str) -> tuple[int, int] | str:
    """Resolve quote to [start,end) offsets, or return an error string."""
    if not isinstance(quote, str):
        return "quote: not a string"
    if not (3 <= len(quote) <= 256):
        return f"quote: length {len(quote)} outside 3..256"
    qnorm = " ".join(quote.lower().split())
    if len(qnorm) < 3:
        return "quote: empty after normalisation"
    try:
        hay, origins = _norm_map(content)
    except ValueError as e:
        return f"quote: {e}"
    at = hay.find(qnorm)
    if at < 0:
        return "quote: not found in section"
    start = origins[at]
    end = origins[at + len(qnorm) - 1] + 1
    return (start, end)


def prove_op_v02(op: dict, file_set: tuple[str, ...], content: str,
                 ops_validate) -> tuple[list[str], list[int] | None]:
    """Full Proof for one v0.2 op. Returns (reasons, resolved_span)."""
    if not isinstance(op, dict):
        return (["schema: op is not an object"], None)
    # v0.2 shape check (mirrors ops.v0.2.schema.json; graph/sql only)
    err = _check_shape_v02(op)
    if err is not None:
        return ([f"schema: {err}"], None)
    if op["target"] not in file_set:
        return ([f"permission: target {op['target']!r} not in file set"], None)
    reasons: list[str] = []
    ne = ops_validate.check_non_empty(op)
    if ne is not None:
        reasons.append(f"non-empty: {ne}")
    span = resolve_quote(op.get("quote"), content)
    if isinstance(span, str):
        reasons.append(f"evidence: {span}")
        resolved = None
    else:
        resolved = [span[0], span[1]]
        ev = ops_validate.check_evidence({**op, "evidence": resolved}, content)
        if ev is not None:
            reasons.append(f"evidence: {ev}")
    if op["target"] == "sql":
        vt = ops_validate.check_value_type(op["value_type"], op["value"])
        if vt is not None:
            reasons.append(f"value-type: {vt}")
    return (reasons, resolved)


def _check_shape_v02(op: dict) -> str | None:
    target = op.get("target")
    if target == "graph":
        allowed = {"target", "s", "p", "o", "s_type", "o_type", "quote"}
        need = ("target", "s", "p", "o", "quote")
        if set(op) - allowed:
            return f"graph: extra fields {sorted(set(op) - allowed)}"
        for f in need:
            if f not in op:
                return f"graph: missing {f}"
        if not (isinstance(op["s"], str) and 1 <= len(op["s"]) <= 512):
            return "graph: s length"
        if not (isinstance(op["p"], str) and 1 <= len(op["p"]) <= 128):
            return "graph: p length"
        if not (isinstance(op["o"], str) and 1 <= len(op["o"]) <= 512):
            return "graph: o length"
        for f in ("s_type", "o_type"):
            if f in op and not (isinstance(op[f], str) and len(op[f]) <= 64):
                return f"graph: {f} length"
        if not (isinstance(op.get("quote"), str) and 3 <= len(op["quote"]) <= 256):
            return "graph: quote length"
        return None
    if target == "sql":
        allowed = {"target", "subject", "attribute", "value", "value_type",
                   "unit", "valid_from", "valid_to", "quote"}
        need = ("target", "subject", "attribute", "value", "value_type", "quote")
        if set(op) - allowed:
            return f"sql: extra fields {sorted(set(op) - allowed)}"
        for f in need:
            if f not in op:
                return f"sql: missing {f}"
        if not (isinstance(op["subject"], str) and 1 <= len(op["subject"]) <= 512):
            return "sql: subject length"
        if not (isinstance(op["attribute"], str) and 1 <= len(op["attribute"]) <= 128):
            return "sql: attribute length"
        if not (isinstance(op["value"], str) and 1 <= len(op["value"]) <= 512):
            return "sql: value length"
        if op["value_type"] not in ("text", "number", "date"):
            return "sql: value_type enum"
        for f in ("unit", "valid_from", "valid_to"):
            if f in op and not (isinstance(op[f], str) and len(op[f]) <= 32):
                return f"sql: {f} length"
        if not (isinstance(op.get("quote"), str) and 3 <= len(op["quote"]) <= 256):
            return "sql: quote length"
        return None
    return f"unknown target {target!r} (v0.2 allows graph, sql)"


def validate_v02(obj: dict, file_set: tuple[str, ...], content: str,
                 ops_validate) -> dict:
    """Never raises on bad model output. Returns {"ok", "verdicts",
    "passed", "failed"} where passed/failed are the op dicts (failed carry
    "_reasons"; passed carry "_span")."""
    if not isinstance(obj, dict) or set(obj) != {"ops"}:
        return {"ok": False, "verdicts": [], "passed": [], "failed": [],
                "error": 'top-level must be exactly {"ops": [...]}'}
    ops = obj["ops"]
    if not isinstance(ops, list) or len(ops) > 32:
        return {"ok": False, "verdicts": [], "passed": [], "failed": [],
                "error": "ops must be a list of at most 32"}
    verdicts, passed, failed = [], [], []
    ok = True
    for i, op in enumerate(ops):
        reasons, span = prove_op_v02(op if isinstance(op, dict) else {}, file_set,
                                     content, ops_validate)
        v = {"index": i,
             "target": op.get("target") if isinstance(op, dict) else None,
             "pass": not reasons, "reasons": reasons}
        if span is not None:
            v["span"] = span
        verdicts.append(v)
        if reasons:
            ok = False
            failed.append({**(op if isinstance(op, dict) else {}),
                           "_reasons": reasons})
        else:
            passed.append({**op, "_span": span})
    return {"ok": ok, "verdicts": verdicts, "passed": passed, "failed": failed}

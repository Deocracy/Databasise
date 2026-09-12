"""Schema -> GBNF grammar for llama.cpp (spike 001). Standard library only.

Contract (SCORE-IO-SPEC.md section 5 + MANIFEST requirement): the grammar
guarantees *format* only -- the right JSON shape with targets restricted to
the section's `file` set. Accuracy (lengths, evidence spans, value types,
slug uniqueness) is Proof's job and is measured on the rig, never settled
by the grammar. Length caps (512/4096/32 ops) are therefore intentionally
NOT in the grammar: GBNF cannot count, and pretending otherwise would be
dishonest. test_spike.py asserts this split: over-long strings are grammar-
admissible but Proof-rejected.

Usage: grammar_for_subset(("graph","sql")) -> GBNF text for llama.cpp
`llama_sampler_init_grammar`. spike 002 binds it to a real model; here we
verify (a) well-formedness (balanced syntax, every referenced rule defined,
root defined), (b) restriction (allowed target literals present, disallowed
absent), (c) round trip: sample op JSONs validate under the file-set-
restricted validator iff their targets are allowed.
"""

from __future__ import annotations

import re

from score import FILE_TARGETS

GBNF_VERSION = "score-io-v0.1"

_PRELUDE = r"""space ::= " "?
string ::= "\"" char* "\""
char ::= [^"\\\x00-\x1F] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])
int ::= [0-9]+
evidence ::= "[" space int "," space int "]"
comma ::= space "," space
"""

_TARGET_RULE = {
    "graph": (
        'graph-op ::= "{" space "\\"target\\"" space ":" space "\\"graph\\"" '
        'comma "\\"s\\"" space ":" space string '
        'comma "\\"p\\"" space ":" space string '
        'comma "\\"o\\"" space ":" space string '
        '("," space "\\"s_type\\"" space ":" space string)? '
        '("," space "\\"o_type\\"" space ":" space string)? '
        'comma "\\"evidence\\"" space ":" space evidence space "}"'
    ),
    "sql": (
        'sql-op ::= "{" space "\\"target\\"" space ":" space "\\"sql\\"" '
        'comma "\\"subject\\"" space ":" space string '
        'comma "\\"attribute\\"" space ":" space string '
        'comma "\\"value\\"" space ":" space string '
        'comma "\\"value_type\\"" space ":" space ("\\"text\\"" | "\\"number\\"" | "\\"date\\"") '
        '("," space "\\"unit\\"" space ":" space string)? '
        '("," space "\\"valid_from\\"" space ":" space string)? '
        '("," space "\\"valid_to\\"" space ":" space string)? '
        'comma "\\"evidence\\"" space ":" space evidence space "}"'
    ),
    "folio": (
        'folio-op ::= "{" space "\\"target\\"" space ":" space "\\"folio\\"" '
        'comma "\\"slug\\"" space ":" space string '
        'comma "\\"kind\\"" space ":" space ("\\"procedure\\"" | "\\"doc\\"") '
        'comma "\\"title\\"" space ":" space string '
        'comma "\\"markdown\\"" space ":" space string '
        '("," space "\\"supersedes\\"" space ":" space string)? space "}"'
    ),
    "agent": (
        'agent-op ::= "{" space "\\"target\\"" space ":" space "\\"agent\\"" '
        'comma "\\"ask\\"" space ":" space string '
        'comma "\\"why\\"" space ":" space string space "}"'
    ),
}


def grammar_for_subset(file_set: tuple[str, ...]) -> str:
    unknown = set(file_set) - set(FILE_TARGETS)
    if unknown:
        raise ValueError(f"unknown file targets {sorted(unknown)}")
    if not file_set:
        raise ValueError("empty file set: grammar would accept nothing")
    names = [t for t in FILE_TARGETS if t in file_set]
    op_rule = "op ::= " + " | ".join(f"{t}-op" for t in names)
    lines = [
        f"# MelodyScribe ops grammar {GBNF_VERSION} file={','.join(names)}",
        'root ::= "{" space "\\"ops\\"" space ":" space "[" '
        'space (op (space "," space op)*)? space "]" space "}"',
        op_rule,
    ]
    lines.extend(_TARGET_RULE[t] for t in names)
    lines.append(_PRELUDE.rstrip("\n"))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- checks

_RULE_DEF_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9_-]*)\s*::=", re.MULTILINE)
_RULE_REF_RE = re.compile(r"\b([a-z][a-zA-Z0-9_-]*)-op\b")


def check_wellformed(grammar: str) -> list[str]:
    """GBNF sanity: balanced quotes/parens/brackets, root + rules defined."""
    errors: list[str] = []
    stripped = []
    for line in grammar.splitlines():
        if line.startswith("#"):
            continue
        # cut character classes first: they may contain a bare `"` which
        # is literal in GBNF but would confuse the string-literal stripper
        no_cls = re.sub(r"\[(\\.|[^\]\\])*\]", "[]", line)
        # then cut string literals so brackets inside them do not count
        no_str = re.sub(r'"(\\.|[^"\\])*"', '""', no_cls)
        stripped.append(no_str)
    text = "\n".join(stripped)
    if text.count('"') % 2:
        errors.append("unbalanced quotes")
    for a, b in (("(", ")"), ("[", "]")):
        if text.count(a) != text.count(b):
            errors.append(f"unbalanced {a}{b}")
    defined = set(_RULE_DEF_RE.findall(text))
    for need in ("root", "op", "space", "string", "char", "int",
                 "evidence", "comma"):
        if need not in defined:
            errors.append(f"rule {need} not defined")
    for ref in set(_RULE_REF_RE.findall("\n".join(stripped))):
        if f"{ref}-op" not in defined:
            errors.append(f"rule {ref}-op referenced but not defined")
    return errors


def check_restriction(grammar: str, file_set: tuple[str, ...]) -> list[str]:
    """Allowed target literals present as values, disallowed absent."""
    errors: list[str] = []
    for t in FILE_TARGETS:
        # the literal \"t\" is how a target value appears inside a rule
        present = f'\\"{t}\\"' in grammar
        if t in file_set and not present:
            errors.append(f"allowed target {t} missing from grammar")
        if t not in file_set and present:
            errors.append(f"disallowed target {t} present in grammar")
    return errors


def all_subsets() -> list[tuple[str, ...]]:
    out: list[tuple[str, ...]] = []
    for mask in range(1, 1 << len(FILE_TARGETS)):
        out.append(tuple(t for i, t in enumerate(FILE_TARGETS) if mask >> i & 1))
    out.append(tuple(FILE_TARGETS))  # 'any' expands to the full set
    seen, uniq = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq

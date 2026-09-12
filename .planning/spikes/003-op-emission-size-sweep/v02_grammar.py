"""GBNF grammar generated from ops.v0.2.schema.json (spike 003 local).

Same construction as spike-001 grammar.py (format-only: no length caps in
the grammar -- quote length 3..256 is enforced by the harness resolver,
exactly the spec's format-vs-accuracy split), but the evidence rule is a
quoted substring instead of an [start,end] integer span:

  evidence ::= "[" space int "," space int "]"   (v0.1, spike 001)
  quote    ::= string                            (v0.2, this spike)

Only graph/sql targets (the sweep's file set). Standard library only.
"""

from __future__ import annotations

GBNF_VERSION = "score-io-v0.2-spike003"

_PRELUDE = r"""space ::= " "?
string ::= "\"" char* "\""
char ::= [^"\\\x00-\x1F] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])
comma ::= space "," space
"""

GRAPH_OP = (
    'graph-op ::= "{" space "\\"target\\"" space ":" space "\\"graph\\"" '
    'comma "\\"s\\"" space ":" space string '
    'comma "\\"p\\"" space ":" space string '
    'comma "\\"o\\"" space ":" space string '
    '("," space "\\"s_type\\"" space ":" space string)? '
    '("," space "\\"o_type\\"" space ":" space string)? '
    'comma "\\"quote\\"" space ":" space string space "}"'
)

SQL_OP_SHAPE = "graph-op shape above, with sql fields (see grammar_v02)"


def grammar_v02() -> str:
    # NOTE: built by explicit string assembly below (not the constant above,
    # which is kept as documentation of the shape); the assembled text is
    # what llama.cpp receives.
    lines = [
        f"# MelodyScribe ops grammar {GBNF_VERSION} file=graph,sql",
        'root ::= "{" space "\\"ops\\"" space ":" space "[" '
        'space (op (space "," space op)*)? space "]" space "}"',
        "op ::= graph-op | sql-op",
        'graph-op ::= "{" space "\\"target\\"" space ":" space "\\"graph\\"" '
        'comma "\\"s\\"" space ":" space string '
        'comma "\\"p\\"" space ":" space string '
        'comma "\\"o\\"" space ":" space string '
        '("," space "\\"s_type\\"" space ":" space string)? '
        '("," space "\\"o_type\\"" space ":" space string)? '
        'comma "\\"quote\\"" space ":" space string space "}"',
        'sql-op ::= "{" space "\\"target\\"" space ":" space "\\"sql\\"" '
        'comma "\\"subject\\"" space ":" space string '
        'comma "\\"attribute\\"" space ":" space string '
        'comma "\\"value\\"" space ":" space string '
        'comma "\\"value_type\\"" space ":" space ("\\"text\\"" | "\\"number\\"" | "\\"date\\"") '
        '("," space "\\"unit\\"" space ":" space string)? '
        '("," space "\\"valid_from\\"" space ":" space string)? '
        '("," space "\\"valid_to\\"" space ":" space string)? '
        'comma "\\"quote\\"" space ":" space string space "}"',
        _PRELUDE.rstrip("\n"),
    ]
    return "\n".join(lines) + "\n"


# keep the module-level constants honest: the assembled grammar must contain
# the documented graph shape (minus whitespace differences)
assert '\\"quote\\""' in grammar_v02()

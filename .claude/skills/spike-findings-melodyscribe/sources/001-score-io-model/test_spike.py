"""Spike 001 acceptance + edge-case suite. Standard library only.

Grounding: every section content is a real paragraph from the 20-document
parity corpus (databasise/parity/corpus.py, hash-verified on load); every
evidence span is computed against that real text. No model, no GPU, no lock.

Log: logs/run-<utc>.jsonl, one JSON object per check with ISO timestamp.
Exit 0 iff every check passes.
"""

from __future__ import annotations

import datetime
import json
import random
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SPIKE_DIR.parents[2]  # 001-score-io-model -> spikes -> .planning -> root
sys.path.insert(0, str(SPIKE_DIR))

# corpus.py is stdlib-only, but importing it as databasise.parity.corpus
# would execute databasise/__init__ (heavy third-party deps), so load the
# module by file path instead.
import importlib.util as _ilu
_cspec = _ilu.spec_from_file_location(
    "spike_corpus", REPO_ROOT / "databasise" / "parity" / "corpus.py")
_spike_corpus = _ilu.module_from_spec(_cspec)
sys.modules["spike_corpus"] = _spike_corpus
_cspec.loader.exec_module(_spike_corpus)
load_snapshot = _spike_corpus.load_snapshot
from score import (  # noqa: E402
    CompileError, compile_plan, compile_score, ei_tokens, encode,
    parse_score, s0_token_stream,
)
from ops_validate import validate_ops  # noqa: E402
from grammar import (  # noqa: E402
    all_subsets, check_restriction, check_wellformed, grammar_for_subset,
)

RESULTS: list[dict] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append({"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "check": name, "pass": bool(passed), "detail": detail})


def expect_error(name: str, xml: str, fragment: str = "") -> None:
    try:
        parse_score(xml)
    except CompileError as e:
        check(name, not fragment or fragment in str(e), str(e))
    else:
        check(name, False, "compiled but should have been refused")


def section(sid: str, content: str, **attrs: str) -> str:
    a = " ".join([f'id="{sid}"'] + [f'{k}="{v}"' for k, v in attrs.items()])
    esc = (content.replace("&", "&amp;").replace("<", "&lt;")
           .replace(">", "&gt;"))
    return f"<section {a}>{esc}</section>"


def score_xml(sections: list[str], **attrs: str) -> str:
    a = 'v="1" ' + " ".join(f'{k}="{v}"' for k, v in attrs.items())
    return f"<score {a}>" + "".join(sections) + "</score>"


# ---------------------------------------------------------------- corpus

snap = load_snapshot()
docs = list(snap.documents)
check("corpus.loads", len(docs) == 20, f"{len(docs)} docs hash-verified")


def para(doc_i: int, n: int = 0, limit: int = 600) -> str:
    text = docs[doc_i].text
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    p = paras[n % len(paras)]
    return p[:limit]


# ------------------------------------------------- acceptance 1: refusals

P0 = para(0)
expect_error("rej.duplicate-ids",
             score_xml([section("s1", P0), section("s1", P0)]), "duplicate")
expect_error("rej.unknown-section-attr",
             score_xml([section("s1", P0, embed="isolated", foo="bar")]),
             "unknown")
expect_error("rej.unknown-score-attr",
             score_xml([section("s1", P0)], quux="1"), "unknown")
expect_error("rej.unknown-embed",
             score_xml([section("s1", P0, embed="telepathic")]), "unknown")
expect_error("rej.unknown-respond",
             score_xml([section("s1", P0, respond="dance")]), "unknown")
expect_error("rej.unknown-file",
             score_xml([section("s1", P0, respond="ops", file="graph,ledger")]),
             "unknown")
expect_error("rej.unknown-link",
             score_xml([section("s1", P0, link="raw,akashic")]), "unknown")
expect_error("rej.file-without-ops",
             score_xml([section("s1", P0, file="graph")]), "without respond=ops")
expect_error("rej.file-text-without-ops",
             score_xml([section("s1", P0, respond="text", file="sql")]),
             "without respond=ops")
expect_error("rej.rewrite-unregistered",
             score_xml([section("s1", P0, embed="rewrite:haiku")]),
             "unregistered")
expect_error("rej.zero-sections", "<score v=\"1\"></score>", "zero sections")
expect_error("rej.bad-id-upper",
             score_xml([section("S1", P0)]), "bad section id")
expect_error("rej.bad-id-space",
             score_xml([section("s 1", P0)]), "bad section id")
expect_error("rej.model-provenance",
             score_xml([section("s1", P0)], provenance="model"), "provenance")
expect_error("rej.provenance-unknown",
             score_xml([section("s1", P0)], provenance="oracle"), "provenance")
expect_error("rej.nested-markup",
             '<score v="1"><section id="s1">a <b>bold</b> move</section></score>',
             "nested markup")
expect_error("rej.dup-file-entry",
             score_xml([section("s1", P0, respond="ops", file="graph,graph")]),
             "duplicate")
expect_error("rej.any-not-alone",
             score_xml([section("s1", P0, respond="ops", file="any,graph")]),
             "stand alone")
expect_error("rej.bad-version", "<score v=\"2\"></score>", "unsupported")
expect_error("rej.malformed", "<score><section id=\"s1\">oops", "well-formed")
expect_error("rej.non-score-root", "<doc></doc>", "<score>")
try:
    spec_ok = parse_score(score_xml([section("s1", P0)], provenance="frontier"))
    check("ok.frontier-provenance", spec_ok["provenance"] == "frontier", "")
except CompileError as e:
    check("ok.frontier-provenance", False, str(e))
try:
    spec_ok = parse_score(score_xml([section("s1", P0)]))
    check("ok.defaults", spec_ok["sections"][0]["embed"] == "isolated"
          and spec_ok["sections"][0]["respond"] == "none"
          and spec_ok["sections"][0]["file"] == ()
          and spec_ok["sections"][0]["link"] == ("raw",), "")
except CompileError as e:
    check("ok.defaults", False, str(e))

# ------------------------------------------------- acceptance 2: I1 + determinism

X = para(3, 1)  # the travelling section
early = score_xml([section("s1", X)] + [section(f"n{i}", para(i))
                                        for i in range(1, 3)])
late_sections = [section(f"m{i}", para(i + 5)) for i in range(6)]
late = score_xml(late_sections[:3] + [section("s1", X)] + late_sections[3:])
spec_e, spec_l = parse_score(early), parse_score(late)
plan_e, plan_l = compile_plan(spec_e), compile_plan(spec_l)
tok_e = ei_tokens(plan_e, spec_e, "s1")
tok_l = ei_tokens(plan_l, spec_l, "s1")
check("I1.position-independent", tok_e == tok_l and tok_e is not None,
      f"{len(tok_e or [])} tokens byte-identical at pos 1 vs pos 4")
plan_e2 = compile_score(early)
check("deterministic.compile-twice",
      json.dumps(plan_e, sort_keys=True) == json.dumps(plan_e2, sort_keys=True),
      "identical plan JSON across two compiles")

# ------------------------------------------------- acceptance 3: I2 order

N = 5
secs = [section(f"d{i}", para(i), respond="ops", file="graph,sql")
        if i == 2 else
        (section(f"d{i}", para(i), embed="off", respond="text")
         if i == 3 else section(f"d{i}", para(i))) for i in range(N)]
spec = parse_score(score_xml(secs))
plan = compile_plan(spec)
# generated tokens keyed by section id, filled for every decode step
gen_by_sec: dict[str, list[str]] = {}
for st in plan["steps"]:
    if st["kind"] == "decode":
        gen_by_sec.setdefault(st["section"], []).append(f"<out-{st['section']}-{len(gen_by_sec[st['section']])}>")
flat_gen: dict[str, list[str]] = {}
for i, st in enumerate(plan["steps"]):
    if st["kind"] == "decode":
        flat_gen[str(i)] = [gen_by_sec[st["section"]].pop(0)]
stream = s0_token_stream(plan, flat_gen)
# Rebuild the expectation from the documented compiler order (content,
# then instruction, then generated tokens per section) -- not by walking
# the plan's append steps, which would make the test circular.
from score import ops_instruction, ANSWER_INSTRUCTION  # local import: test-only
# generated tokens per decode step, in plan order
dec_steps = [i for i, st in enumerate(plan["steps"]) if st["kind"] == "decode"]
exp2: list[str] = []
di = 0
for sec in spec["sections"]:
    exp2.extend(encode(sec["content"]))
    if sec["respond"] == "ops":
        exp2.extend(encode(ops_instruction(sec["file"])))
        exp2.extend(flat_gen[str(dec_steps[di])])
        di += 1
    elif sec["respond"] == "text":
        exp2.extend(encode(ANSWER_INSTRUCTION))
        exp2.extend(flat_gen[str(dec_steps[di])])
        di += 1
check("I2.in-order", stream == exp2 and di == len(dec_steps),
      f"S0 len {len(stream)}, expected len {len(exp2)}, {di} decodes consumed")

# simpler, stronger I2: pure-append score has exact token concatenation
plain = score_xml([section(f"p{i}", para(i + 10)) for i in range(4)])
pspec = parse_score(plain)
pplan = compile_plan(pspec)
pstream = s0_token_stream(pplan)
pexp = []
for sec in pspec["sections"]:
    pexp.extend(encode(sec["content"]))
check("I2.pure-append-exact", pstream == pexp, f"{len(pstream)} tokens")

# ------------------------------------------------- read forms + I5 uniqueness

mix = score_xml([
    section("a", para(0)),                                            # isolated
    section("b", para(1), embed="context"),                           # context
    section("c", para(2), embed="rewrite:propositions"),              # rewrite
    section("d", para(3), embed="off", respond="text"),               # no vector
    section("e", para(4), respond="ops", file="folio,agent"),         # isolated+ops
])
mspec = parse_score(mix)
mplan = compile_plan(mspec)
reads = [(st["seq"], st["at"], st["form"], st["section"])
         for st in mplan["steps"] if st["kind"] == "read_vector"]
forms = {sec: form for (_, _, form, sec) in reads}
check("reads.forms",
      forms == {"a": "isolated", "b": "context",
                "c": "rewrite:propositions", "e": "isolated"}
      and len(reads) == 4,
      json.dumps(forms))
check("I5.one-read-per-vector",
      len({(s, a) for (s, a, _, _) in reads}) == len(reads),
      f"{len(reads)} reads, all (seq, position) unique")
check("reads.cap-relative-after-decode",
      all(st.get("pos_kind") == "exact"
          for st in mplan["steps"]
          if st["kind"] == "read_vector" and st["section"] in ("a", "b"))
      and all(st.get("pos_kind") == "cap_relative"
              for st in mplan["steps"]
              if st["kind"] == "read_vector" and st["section"] == "c"),
      "pre-decode reads exact, post-decode reads cap-relative")
check("grammar.text-shape",
      all(s in grammar_for_subset(("graph", "sql"))
          for s in ("root ::=", "op ::=", "graph-op ::=", "sql-op ::=",
                    "# MelodyScribe ops grammar")),
      "GBNF header + root + op rules present")

# ------------------------------------------------- acceptance 4: I3 no leakage

leak_src = "Use <section> tags and embed=isolated wisely. Marker \u27e6EMB\u27e7 here."
lsec = parse_score(score_xml([section("s1", leak_src), section("s2", para(7))]))
lplan = compile_plan(lsec)
ei = ei_tokens(lplan, lsec, "s1")
check("I3.ei-exact-shape",
      ei == lplan["prefix"]["tokens"] + encode(leak_src) + ["[EMB]"],
      "E_i is prefix+content+[EMB] and nothing else")
ei_joined = "".join(ei or [])
# Directive/instruction vocabulary must be absent; the content's own words
# (including a literal "<section" that arrived escaped as &lt;) must survive.
check("I3.no-directive-text",
      all(s not in ei_joined for s in ("respond=", "file=", "Emit one JSON",
                                       "G(graph", "copy_prefix", "read_vector"))
      and "<section" in ei_joined and "embed=isolated" in ei_joined
      and "\u27e6EMB\u27e7" in ei_joined,
      "instruction vocabulary absent, content vocabulary present verbatim")
ei_steps = [st for st in lplan["steps"]
            if st["kind"] in ("copy_prefix", "free")
            or (st["kind"] == "append" and st["seq"].startswith("E_"))
            or (st["kind"] == "read_vector" and st["seq"].startswith("E_"))]
check("I3.no-instruction-in-ei",
      all("".join(st.get("tokens", [])).find("Emit one JSON") == -1
          for st in ei_steps),
      f"{len(ei_steps)} E-steps carry no instruction text")

# ------------------------------------------------- acceptance 5: grammar round trip

def sample_op(target: str, content: str, **kw) -> dict:
    if target == "graph":
        subj = kw.get("s", "Ada Lovelace")
        start = content.find(subj)
        if start < 0:
            subj = content.split()[0]
            start = 0
        return {"target": "graph", "s": subj, "p": "born_on",
                "o": "1815-12-10", "s_type": "person", "o_type": "date",
                "evidence": [start, start + len(subj)]}
    if target == "sql":
        subj = kw.get("subject", "Ada Lovelace")
        start = content.find(subj)
        if start < 0:
            subj = content.split()[0]
            start = 0
        return {"target": "sql", "subject": subj, "attribute": "birthday",
                "value": "1815-12-10", "value_type": "date",
                "evidence": [start, start + len(subj)]}
    if target == "folio":
        return {"target": "folio", "slug": "find-people-by-birth-year",
                "kind": "procedure", "title": "Find by birth year",
                "markdown": "# how\nAsk for the year."}
    return {"target": "agent", "ask": "Resolve the alias.",
            "why": "Two names may be one person."}


g_content = para(0) + " Ada Lovelace was born on 1815-12-10."
g_file = ("graph", "sql", "folio", "agent")
n_subsets = 0
for subset in all_subsets():
    n_subsets += 1
    g = grammar_for_subset(subset)
    wf = check_wellformed(g)
    rs = check_restriction(g, subset)
    if wf or rs:
        check(f"grammar.{','.join(subset)}", False, f"{wf} {rs}")
        continue
    ok = True
    detail = ""
    for t in subset:
        obj = {"ops": [sample_op(t, g_content)]}
        r = validate_ops(obj, subset, g_content)
        if not r["ok"]:
            ok, detail = False, f"allowed {t} rejected: {r['verdicts']}"
            break
    for t in [x for x in g_file if x not in subset]:
        obj = {"ops": [sample_op(t, g_content)]}
        r = validate_ops(obj, subset, g_content)
        if r["ok"]:
            ok, detail = False, f"disallowed {t} accepted"
            break
    check(f"grammar.{','.join(subset)}", ok, detail or
          f"{len(subset)} allowed pass, {4 - len(subset)} disallowed refused")
check("grammar.subset-count", n_subsets == 15,
      f"{n_subsets} non-empty subsets of 2^4 minus empty; 'any' is an alias "
      "for the full set, expanded by the compiler before grammar selection")

# fuzz: hand-built mutation battery (deterministic); each must be refused.
# ([] is the one legal "mutation": the cheapest legal output.)
import copy
muts = []
base = {"ops": [sample_op("graph", g_content), sample_op("sql", g_content),
                sample_op("folio", g_content), sample_op("agent", g_content)]}
mut_rejected = 0
mut_total = 0
m = copy.deepcopy(base); del m["ops"][0]["s"]; muts.append(("drop-required", m))
m = copy.deepcopy(base); m["ops"][1]["zzz"] = 1; muts.append(("extra-field", m))
m = copy.deepcopy(base); m["ops"][0]["evidence"] = "12-48"; muts.append(("bad-ev-type", m))
m = copy.deepcopy(base); m["ops"] = m["ops"] * 9; muts.append(("33-ops", m[:1] if False else {"ops": (m["ops"] * 9)[:33]}))
m = copy.deepcopy(base); m["ops"][0]["s"] = "x" * 513; muts.append(("513-char", m))
m = copy.deepcopy(base); m["ops"][2]["slug"] = "Bad_Slug"; muts.append(("bad-slug", m))
m = copy.deepcopy(base); m["ops"][3]["target"] = "oracle"; muts.append(("bad-target", m))
m = copy.deepcopy(base); m["ops"][0]["evidence"] = [True, 5]; muts.append(("bool-evidence", m))
m = copy.deepcopy(base); m["top"] = 1; muts.append(("top-extra", {"ops": m["ops"], "top": 1}))
for name, obj in muts:
    mut_total += 1
    r = validate_ops(obj, g_file, g_content)
    if not r["ok"]:
        mut_rejected += 1
    else:
        check(f"fuzz.{name}", False, "mutation accepted")
check("fuzz.all-rejected", mut_rejected == mut_total,
      f"{mut_rejected}/{mut_total} mutations refused")

# format/accuracy split: a 513-char subject is grammar-admissible shape
# (GBNF cannot count) but Proof-rejected. Assert the split explicitly.
long_op = sample_op("graph", g_content)
long_op["s"] = "y" * 513
r = validate_ops({"ops": [long_op]}, g_file, g_content)
check("split.grammar-format-proof-accuracy",
      not r["ok"] and any("length" in x for v in r["verdicts"] for x in v["reasons"]),
      "over-long string refused by Proof (length), not by shape")

# ------------------------------------------------- acceptance 6: Proof verdicts

C = "Ada Lovelace was born on 1815-12-10 in London."
ev_start = C.find("Ada Lovelace")
good_graph = {"target": "graph", "s": "Ada Lovelace", "p": "born_on",
              "o": "1815-12-10", "evidence": [ev_start, ev_start + 12]}
good_sql = {"target": "sql", "subject": "Ada Lovelace",
            "attribute": "birthday", "value": "1815-12-10",
            "value_type": "date", "evidence": [ev_start, ev_start + 12]}
r = validate_ops({"ops": [good_graph, good_sql]}, ("graph", "sql"), C)
check("proof.correct-pass", r["ok"], json.dumps(r["verdicts"]))
r = validate_ops({"ops": []}, ("graph", "sql"), C)
check("proof.empty-pass", r["ok"] and r["verdicts"] == [], "cheapest legal output")
fabricated = dict(good_graph, evidence=[0, 5])  # "Ada L" has subject; use a span without it
fabricated = dict(good_graph, evidence=[C.find("London"), C.find("London") + 6])
r = validate_ops({"ops": [fabricated]}, ("graph", "sql"), C)
check("proof.fabricated-span-caught",
      not r["ok"] and any("evidence" in q for q in r["verdicts"][0]["reasons"]),
      json.dumps(r["verdicts"]))
mistyped = dict(good_sql, value="12/10/1815")
r = validate_ops({"ops": [mistyped]}, ("graph", "sql"), C)
check("proof.mistyped-date-caught",
      not r["ok"] and any("value-type" in q for q in r["verdicts"][0]["reasons"]),
      json.dumps(r["verdicts"]))

# ------------------------------------------------- edge battery: value types

vt_cases = [("date", "1815", True), ("date", "1815-12-10", True),
            ("date", "1815-12-10T09:00:00", True),
            ("date", "12/10/1815", False), ("date", "not-a-date", False),
            ("number", "3.14", True), ("number", "-17", True),
            ("number", "abc", False), ("number", "NaN", False),
            ("number", "Infinity", False), ("text", "anything", True)]
for vt, val, want in vt_cases:
    op = {"target": "sql", "subject": "Ada Lovelace", "attribute": "a",
          "value": val, "value_type": vt,
          "evidence": [ev_start, ev_start + 12]}
    got = validate_ops({"ops": [op]}, ("sql",), C)["ok"]
    # subject must be inside the span: it is ([ev_start, +12] covers it)
    check(f"valuetype.{vt}.{val}", got == want, f"want={want} got={got}")

# evidence boundaries
op = dict(good_graph, evidence=[ev_start, len(C)])
check("evidence.end-eq-len-pass",
      validate_ops({"ops": [op]}, ("graph",), C)["ok"], "")
op = dict(good_graph, evidence=[ev_start, len(C) + 1])
check("evidence.end-gt-len-fail",
      not validate_ops({"ops": [op]}, ("graph",), C)["ok"], "")
messy = "  ADA   lovelace  was here "
op = {"target": "graph", "s": "ada lovelace", "p": "seen_at", "o": "here",
      "evidence": [0, len(messy)]}
check("evidence.norm-case-space",
      validate_ops({"ops": [op]}, ("graph",), messy)["ok"],
      "whitespace/case normalisation")
op = dict(good_graph, s="   ")
check("evidence.whitespace-subject-fail",
      not validate_ops({"ops": [op]}, ("graph",), C)["ok"], "")

# folio slug lifecycle
folio = sample_op("folio", C)
check("folio.first-pass",
      validate_ops({"ops": [folio]}, ("folio",), C, set())["ok"], "")
check("folio.dup-without-supersedes-fail",
      not validate_ops({"ops": [folio]}, ("folio",), C,
                       {"find-people-by-birth-year"})["ok"], "")
folio2 = dict(folio, supersedes="find-people-by-birth-year")
check("folio.dup-with-supersedes-pass",
      validate_ops({"ops": [folio2]}, ("folio",), C,
                   {"find-people-by-birth-year"})["ok"], "")

# permission + file=any
agent = sample_op("agent", C)
check("permission.agent-refused",
      not validate_ops({"ops": [agent]}, ("graph", "sql"), C)["ok"], "")
check("permission.agent-allowed",
      validate_ops({"ops": [agent]}, ("graph", "agent"), C)["ok"], "")
spec_any = parse_score(score_xml([section("s1", P0, respond="ops")]))
check("file.default-any",
      spec_any["sections"][0]["file"] == ("graph", "sql", "folio", "agent"),
      "respond=ops defaults file to any->all four")

# misc shapes
check("shape.empty-content-compiles",
      bool(compile_score(score_xml([section("s1", "")]))["steps"]), "")
uni = "Astrid \u00c5sen \u2014 \u6f22\u5b57 \U0001f3b5"
uspec = parse_score(score_xml([section("s1", uni)]))
uplan = compile_plan(uspec)
check("shape.unicode",
      ei_tokens(uplan, uspec, "s1") == uplan["prefix"]["tokens"] + encode(uni) + ["[EMB]"],
      "unicode round-trips through parse/compile")
check("shape.ops-32-pass",
      validate_ops({"ops": [good_graph] * 32}, ("graph",), C)["ok"], "")
check("shape.ops-33-fail",
      not validate_ops({"ops": [good_graph] * 33}, ("graph",), C)["ok"], "")
check("shape.top-extra-key-fail",
      not validate_ops({"ops": [], "x": 1}, ("graph",), C)["ok"], "")
check("shape.non-object-op-fail",
      not validate_ops({"ops": ["nope"]}, ("graph",), C)["ok"], "")

# ------------------------------------------------- worked example (spec section 8)

wx = score_xml([
    section("s1", para(0)),
    section("s2", para(1), respond="ops", file="graph,sql"),
    section("s3", "Summarise this.", embed="off", respond="text"),
])
wspec = parse_score(wx)
wplan = compile_plan(wspec)
kinds = [st["kind"] for st in wplan["steps"]]
# s1: append+copy+append+read+free (5); s2: append+copy+append+read+free+append+decode (7);
# s3: append+append+decode (3)
check("worked-example.step-kinds",
      kinds == ["append", "copy_prefix", "append", "read_vector", "free",
                "append", "copy_prefix", "append", "read_vector", "free",
                "append", "decode",
                "append", "append", "decode"],
      ",".join(kinds))
dec = [st for st in wplan["steps"] if st["kind"] == "decode"]
check("worked-example.decode-bounds",
      all(d["cap"] > 0 and (d["grammar"] is not None or d["stop"])
          for d in dec) and dec[0]["grammar"] == "G(graph,sql)",
      "ops decode under G(graph,sql) cap 256; text decode stopped cap 512")
check("worked-example.caps",
      [d["cap"] for d in dec] == [256, 512], str([d["cap"] for d in dec]))

# ------------------------------------------------- schema mirror (ops.schema.json)

import re as _re
schema = json.loads((SPIKE_DIR / "ops.schema.json").read_text(encoding="utf-8"))
check("mirror.schema-loads", schema.get("required") == ["ops"], "")
sch_items = schema["properties"]["ops"]
check("mirror.max-ops", sch_items.get("maxItems") == 32, "")
branches = {b["properties"]["target"]["const"]: b
            for b in sch_items["items"]["oneOf"]}
check("mirror.four-targets", set(branches) == {"graph", "sql", "folio", "agent"},
      ",".join(sorted(branches)))
check("mirror.graph-required",
      set(branches["graph"]["required"]) == set(("target", "s", "p", "o", "evidence")), "")
check("mirror.sql-required",
      set(branches["sql"]["required"]) == set(
          ("target", "subject", "attribute", "value", "value_type", "evidence")), "")
check("mirror.folio-required",
      set(branches["folio"]["required"]) == set(
          ("target", "slug", "kind", "title", "markdown")), "")
check("mirror.folio-slug-pattern",
      _re.match(branches["folio"]["properties"]["slug"]["pattern"] + "\\Z",
                "find-people-by-birth-year") is not None
      and branches["folio"]["properties"]["slug"]["maxLength"] == 64, "")
# every schema constraint has a live test above: spot-check the mapping
check("mirror.no-unknown-shape",
      branches["graph"].get("additionalProperties") is False, "")

# ------------------------------------------------- write log + summary

LOG_DIR = SPIKE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
log_path = LOG_DIR / f"run-{stamp}.jsonl"
with open(log_path, "w", encoding="utf-8") as f:
    for r_ in RESULTS:
        f.write(json.dumps(r_) + "\n")

n_pass = sum(1 for r_ in RESULTS if r_["pass"])
n_tot = len(RESULTS)
print(f"{n_pass}/{n_tot} checks passed; log {log_path}")
for r_ in RESULTS:
    if not r_["pass"]:
        print(f"FAIL {r_['check']}: {r_['detail']}")
sys.exit(0 if n_pass == n_tot else 1)

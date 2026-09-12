# Score I/O Contract

Implementation blueprint for the MelodyScribe input/output contract: the Score document that enters the model, the token plan it compiles to, the op list that leaves the model, and Proof, the validator every op passes before dispatch. Synthesised from spike 001 (VALIDATED, 95/95 checks) and the spec v0.2 evidence deviation recorded by spike 003.

## Requirements

From the `melodyscribe` idea in `.planning/spikes/MANIFEST.md`:

- Model-written skills (Folios) run sandboxed and are read only by MelodyScribe; the frontier reads one human-authored skill (D-MS-01, D-MS-02)
- The model never authors Score directives; directives come from the chunker or the frontier skill
- Grammar constraints guarantee format only; accuracy comes from training and is measured on the rig
- No vendor benchmark settles anything; every verdict comes from a local measurement on the 20-document parity corpus
- v0.1 defaults adopted overnight for the spec's open decisions, owner review pending: graph nodes filed by normalised name (alias merging is a revise concern); one generic `facts` table for SQL; `folio` ops allowed during bulk ingest under the sandbox rule; `doc_prefix` includes the chat-template system turn; `[EMB]`/`[RQ]` token ids chosen per model by spike 002 and recorded

## How to Build It

Normative sources: `.planning/spikes/001-score-io-model/SCORE-IO-SPEC.md` (v0.1) with `ops.schema.json` beside it, and the v0.2 evidence deviation in `.planning/spikes/003-op-emission-size-sweep/ops.v0.2.schema.json`. `.planning/spikes/CONVENTIONS.md` rules that later code imports the compiler (`score.py`) and Proof (`ops_validate.py`) from 001 instead of re-implementing them; a build session does the same, then applies step 9.

### Step 1: parse the Score (XML)

Wire format (spec section 3):

```xml
<score v="1" corpus="..." doc="..." provenance="chunker">
  <section id="s1" embed="isolated">text</section>
  <section id="s2" embed="off" respond="text">a command</section>
  <section id="s3" embed="isolated" respond="ops" file="graph,sql">text</section>
  <section id="s4" embed="rewrite:propositions" link="raw,graph">text</section>
</score>
```

| Attribute | Values | Default | Acted on by |
|---|---|---|---|
| `id` | unique in the Score, `[a-z0-9_-]+` | required | harness |
| `embed` | `isolated`, `context`, `off`, `rewrite:<style>` (styles `propositions`, `canonical`, `summary`) | `isolated` | harness (rewrite: model, then harness) |
| `respond` | `none`, `ops`, `text` | `none` | model |
| `file` | comma list from `graph`, `sql`, `folio`, `agent`, or `any` alone | `any` when `respond=ops`, else none | model + harness |
| `link` | comma list from `raw`, `graph`, `sql`, `folio` | `raw` | harness |

`<score>` accepts `v` (must be `1`), `corpus`, `doc`, and `provenance` (`chunker` or `frontier`; `model` or any other value is refused, which is D-MS-01/02 made mechanical). Parse with `xml.etree.ElementTree`: it unescapes entities and rejects malformed input; nested markup inside a section is refused by `len(el) != 0`. Every unknown attribute or value, duplicate or malformed id, `file` without `respond=ops`, `any` combined with other targets, duplicate `file` entry, unregistered rewrite style, and a Score with zero sections raises `CompileError`, never ignored. `parse_score` returns `{"corpus", "doc", "provenance", "sections": [{"id", "embed", "respond", "file", "link", "content"}]}` with `file` expanded to the full target tuple when `any`. Source: `parse_score` in `.planning/spikes/001-score-io-model/score.py`.

### Step 2: compile sections into a token plan

Per directive (spec section 4), `P` being the prefilled `doc_prefix` sequence, copied not recomputed:

| Directive | Steps |
|---|---|
| any section | `S0 += tokens(content)` |
| `embed=isolated` | `E_i = copy(P)`; `E_i += tokens(content) + [EMB]`; read vector at `[EMB]`; free `E_i` |
| `embed=context` | `S0 += [EMB]`; read vector there (`form=context`) |
| `embed=off` | nothing |
| `embed=rewrite:<style>` | `S0 += rewrite instruction`; decode text, cap 256, stop set; `S0 += [EMB]`; read vector (`form=rewrite:<style>`) |
| `respond=ops` | `S0 += ops instruction for the file set`; decode under `G(file set)`, cap 256; decoded tokens stay in `S0` |
| `respond=text` | `S0 += answer instruction`; decode free text, cap 512, stop set |
| `link=...` | no tokens; metadata assembled at dispatch |

Source `.planning/spikes/001-score-io-model/score.py` (isolated and ops branches shown; context, rewrite, and text branches follow the table):

```python
def compile_plan(spec: dict) -> dict:
    """Returns {"prefix": {...}, "steps": [...], "versions": {...}}.
    Step kinds: append, copy_prefix, read_vector, free, decode."""
    prefix_tokens = encode(DOC_PREFIX)
    steps: list[dict] = []
    s0_len = 0
    s0_exact = True          # False after the first decode step
    reads: list[tuple[str, int]] = []

    def s0_append(tokens: list[str]) -> None:
        nonlocal s0_len
        steps.append({"kind": "append", "seq": "S0", "tokens": tokens,
                      "pos_kind": "exact" if s0_exact else "cap_relative"})
        s0_len += len(tokens)

    for index, sec in enumerate(spec["sections"]):
        content_tokens = encode(sec["content"])
        s0_append(content_tokens)            # I2: every section enters S0 in order
        seq = f"E_{index}"
        if sec["embed"] == "isolated":
            steps.append({"kind": "copy_prefix", "seq": seq, "from": "P",
                          "tokens": list(prefix_tokens)})
            steps.append({"kind": "append", "seq": seq,
                          "tokens": content_tokens + [EMB_TOKEN]})
            pos = len(prefix_tokens) + len(content_tokens) + 1 - 1
            steps.append({"kind": "read_vector", "seq": seq, "at": pos,
                          "token": EMB_TOKEN, "form": "isolated",
                          "pos_kind": "exact", "section": sec["id"]})
            reads.append((seq, pos))
            steps.append({"kind": "free", "seq": seq})
        if sec["respond"] == "ops":
            s0_append(encode(ops_instruction(sec["file"])))
            steps.append({"kind": "decode", "seq": "S0", "what": "ops",
                          "grammar": f"G({','.join(sec['file'])})",
                          "stop": None, "cap": OPS_MAX_TOKENS,
                          "section": sec["id"], "s0_base": s0_len})
            s0_len += OPS_MAX_TOKENS         # cap bounds the generated tokens
            s0_exact = False

    if len(reads) != len(set(reads)):        # I5
        raise CompileError("duplicate vector read position")
    for st in steps:                          # I4
        if st["kind"] == "decode":
            if not st["cap"] or st["cap"] <= 0:
                raise CompileError("unbounded decode step")
            if st["grammar"] is None and not st["stop"]:
                raise CompileError("decode with neither grammar nor stop set")
    return {"prefix": {"name": "P", "version": DOC_PREFIX_V, "tokens": prefix_tokens},
            "steps": steps,
            "versions": {"doc_prefix": DOC_PREFIX_V, "instructions": INSTRUCTIONS_V,
                         "tokenizer": TOKENIZER_VERSION, "token_policy": "..."}}
```

Constants in `score.py`: `REWRITE_MAX_TOKENS = 256`, `OPS_MAX_TOKENS = 256`, `TEXT_MAX_TOKENS = 512`, `TEXT_STOP_SET = ["</score>", "\n\n\n"]`, `DOC_PREFIX_V = INSTRUCTIONS_V = "score-io-v0.1"`. `DOC_PREFIX` includes the chat-template system turn (open decision 4, adopted). The plan is a pure function of (Score bytes, `DOC_PREFIX_V`, `INSTRUCTIONS_V`, `TOKENIZER_VERSION`); compiling twice gives identical plan JSON.

Position accounting: `S0` positions continue across sections and generated tokens; `E_i` positions start at `len(P)`. After the first decode step the exact `S0` position is unknowable at compile time (the generated count is bounded by the cap, not known), so every later `S0` append and read carries `pos_kind: cap_relative` and the runtime resolves it from the actual decoded count. Spike 002 maps the steps onto the llama.cpp C API: `llama_memory_seq_cp` for `P` to `E_i`, one `llama_decode` per step with `embeddings=true`, `llama_get_embeddings_ith` at the marked read (it indexes the i-th output, not the position), `llama_get_logits_ith` at the last position for decode, `llama_memory_seq_rm` to free `E_i`.

### Step 3: record the token policy string

Every plan carries `versions.token_policy`. Spike 001's stand-in is `emb=toy-word-v1:[EMB];rq=toy-word-v1:[RQ];pooling=last`. Spike 002 replaced it per model: for MiniCPM5-2B the string is `emb=reserved:130080;rq=reserved:130081`, ids taken from the unused tail block `130072..130559` of the 130560-entry vocab (they detokenise to nothing, so they never occur in natural text; the fallback marker `⟦EMB⟧` costs 5 tokens, so the reserved single id wins). Pooling is `last` at the `[EMB]` position, no mean pooling. `[RQ]` follows the same policy with a distinct id. The policy string enters the `EmbeddingSpace` hash as `namespace_text_convention` (spec section 2), so changing it changes the space identity.

### Step 4: hold invariants I1 to I5

| Invariant | Mechanical meaning | Enforced by |
|---|---|---|
| I1 Isolation | `ei_tokens(plan, spec, id) == prefix_tokens + encode(content) + [EMB]`; the same section at position 1 and at position 4 of two different Scores yields byte-identical lists | test `I1.position-independent`; re-run on real ids in 002 |
| I2 Order | `s0_token_stream(plan, generated)` equals the in-order concatenation of `S0` appends and decode outputs; nothing dropped or reordered | tests `I2.in-order` (ops, text, rewrite decodes), `I2.pure-append-exact` |
| I3 No directive leakage | no tag, attribute, or instruction text in any `E_i`; the exact-shape equality above carries the weight, the vocabulary check is secondary | tests `I3.ei-exact-shape`, `I3.no-directive-text`, `I3.no-instruction-in-ei` |
| I4 Bounded decode | every decode step has `cap > 0` and a grammar or a stop set; `compile_plan` raises otherwise | compiler; test `worked-example.caps` (`[256, 512]`) |
| I5 One read per vector | the `(seq, pos)` of every `read_vector` is unique; `compile_plan` raises on a duplicate | compiler; test `I5.one-read-per-vector` |

Reads before the first decode are `pos_kind: exact`, reads after it `cap_relative` (test `reads.cap-relative-after-decode`).

### Step 5: the op list schema per file set

Source `.planning/spikes/001-score-io-model/ops.schema.json` (v0.1; v0.2 differences in step 9). Top level is exactly `{"ops": [...]}` with `additionalProperties: false` and `maxItems: 32`. Each op is one of four shapes selected by `target`:

| target | required | optional | limits |
|---|---|---|---|
| `graph` | `s`, `p`, `o`, `evidence` | `s_type`, `o_type` | `s`, `o` 1..512; `p` 1..128; `s_type`, `o_type` 0..64 |
| `sql` | `subject`, `attribute`, `value`, `value_type`, `evidence` | `unit`, `valid_from`, `valid_to` | `subject`, `value` 1..512; `attribute` 1..128; `value_type` in `text`, `number`, `date`; `unit`, `valid_from`, `valid_to` 0..32 |
| `folio` | `slug`, `kind`, `title`, `markdown` | `supersedes` | `slug`, `supersedes` match `^[a-z0-9]+(-[a-z0-9]+)*$`, max 64; `kind` in `procedure`, `doc`; `title` 1..128; `markdown` 1..4096 |
| `agent` | `ask`, `why` | none | `ask` 1..512; `why` 1..256 |

v0.1 `evidence` is `[start, end]`, two non-negative integers into the section content. A section's `file` set restricts which shapes are legal: 15 distinct subsets of the four targets (`any` is an alias for the full set). `{"ops": []}` is legal and means nothing to file. `graph` and `sql` may both be emitted for the same fact. `agent` is legal only when `agent` is in the `file` set. SQL is one generic table `facts(subject, attribute, value, value_type, unit, valid_from, valid_to, evidence_ref)`.

### Step 6: generate the GBNF grammar per file set

`grammar.py` builds the grammar by string assembly: a `root` rule, an `op` alternation restricted to the section's `file` set, one `<target>-op` rule per allowed target, and a shared prelude. It carries no length constraints: GBNF cannot count, so the 512/4096/32 caps live in Proof. Source `.planning/spikes/001-score-io-model/grammar.py`:

```python
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
```

Prelude rules: `space`, `string`, `char` (JSON escapes), `int`, `evidence ::= "[" space int "," space int "]"`, `comma`. Each `_TARGET_RULE[t]` spells the required keys in schema order with optional keys as `(...)?` groups and enum values as literal alternations. Run two checks on every generated grammar: `check_wellformed` (strip character classes, then string literals; quotes, parens, and brackets balanced; `root`, `op`, the prelude rules, and every referenced `<t>-op` defined) and `check_restriction` (the literal `\"<target>\"` present for every allowed target and absent for every disallowed one). Hand the text to llama.cpp through `LlamaGrammar.from_string` (spike 003 `student.py`) or `llama_sampler_init_grammar`.

### Step 7: run Proof on every op, in this order

Proof rejects an op, logs it, and continues; a rejected op never blocks the section's embedding. `validate_ops` never raises on model output, only on harness misuse. Source `.planning/spikes/001-score-io-model/ops_validate.py`:

```python
def prove_op(op: dict, file_set: tuple[str, ...], content: str,
             folio_slugs: set[str]) -> list[str]:
    """Proof checks for one op. Returns a list of rejection reasons ([] = pass)."""
    reasons: list[str] = []
    shape_err = _check_shape(op)          # 1 schema: fields, lengths, enums, evidence shape
    if shape_err is not None:
        return [f"schema: {shape_err}"]
    if op["target"] not in file_set:      # 2 permission: target in the file set
        reasons.append(f"permission: target {op['target']!r} not in file set")
        return reasons
    if op["target"] in ("graph", "sql"):
        # 3 non-empty after trim; 4 evidence: span inside content and containing
        #   s or o (graph), subject or value (sql), after _norm
        for label, err in (("non-empty", check_non_empty(op)),
                           ("evidence", check_evidence(op, content))):
            if err is not None:
                reasons.append(f"{label}: {err}")
        if op["target"] == "sql":         # 5 value type
            vt = check_value_type(op["value_type"], op["value"])
            if vt is not None:
                reasons.append(f"value-type: {vt}")
    elif op["target"] == "folio":         # 6 slug unique unless supersedes
        if op["slug"] in folio_slugs and "supersedes" not in op:
            reasons.append(f"slug: {op['slug']!r} already in Folios store "
                           "without supersedes")
    return reasons
```

Normalisation for the evidence check is `_norm(text) = " ".join(text.lower().split())`. `validate_ops(obj, file_set, content, folio_slugs)` wraps `prove_op`: the top level must be exactly `{"ops": [...]}`, a list of at most 32; it returns `{"ok", "verdicts": [{"index", "target", "pass", "reasons"}]}`. Effects per target in the contract's vocabulary (spec section 6): graph `writes_graph`; sql `writes_artifact`; folio `writes_kv` and `writes_vector` at scope `self_storage`; agent `calls_llm` through a machine client, never `net`; the section vector `writes_vector` in the declared `space_id`. Write one link record per vector: `{vector_id, space_id, chunk_ref, section_id, form, graph_ids[], sql_row_ids[], folio_slug?, doc_prefix_version, model_revision}`; graph nodes and SQL rows carry `chunk_ref` and `section_id` back.

### Step 8: recall-time I/O

Spec section 7, not exercised by spike code. One stream: `[query_prefix][query][RQ]`; read the `[RQ]` vector at its position before decoding; then one grammar-constrained decode of a recall list:

```json
{"recall": [
  {"source": "vector", "k": 8},
  {"source": "graph", "seeds": ["Ada Lovelace"], "hops": 1},
  {"source": "sql", "attribute": "birthday", "subject": "Ada Lovelace"},
  {"source": "folio", "slug": "find-people-by-birth-year"}
]}
```

The harness appends results as a fenced block the model treats as data; a second recall list is allowed after results, up to `max_hops` (budget-owned, not model-owned); the final answer is free text or `{"target": "agent", ...}` to hand a distilled context across the seam. Build the recall grammar the way step 6 builds the ops grammar: format only, cap from I4.

### Step 9: v0.2, quote evidence replaces character offsets

Spike 003 found that neither the frontier teacher nor any student size can emit exact character offsets (first item under What to Avoid). The v0.2 deviation lives in `.planning/spikes/003-op-emission-size-sweep/`:

- `ops.v0.2.schema.json`: in `graph` and `sql`, `evidence` is replaced by `quote` (`string`, `minLength 3`, `maxLength 256`, required). `folio` and `agent` carry no evidence and are unchanged; the spike's schema and grammar list only `graph` and `sql` because that was the sweep's `file` set.
- `v02_grammar.py`, `grammar_v02()`: same construction as step 6 with `quote` emitted as a plain `string` and the `int` and `evidence` prelude rules dropped; version `score-io-v0.2-spike003`.
- Instruction text (`common.py`, `INSTRUCTION`): the quote is a 3-to-256-character verbatim substring copied character-for-character from the section, it must contain the subject or the value, and when the value is normalised (ISO date, decimal) the model quotes a span containing the subject instead. `score.py`'s `ops_instruction` still says `[start,end] evidence span`; change that line and bump `INSTRUCTIONS_V` when adopting v0.2.
- `resolve.py`: the harness resolves the quote to offsets, then runs 001's `check_evidence` unchanged on the resolved span:

```python
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
        hay, origins = _norm_map(content)   # Proof's _norm, plus origins[i] = original index
    except ValueError as e:
        return f"quote: {e}"                # non-1:1 lowercase (U+0130): refuse
    at = hay.find(qnorm)                    # first occurrence
    if at < 0:
        return "quote: not found in section"
    start = origins[at]
    end = origins[at + len(qnorm) - 1] + 1
    return (start, end)
```

`prove_op_v02` order: v0.2 shape mirror, permission, non-empty, `resolve_quote`, then `check_evidence({**op, "evidence": [start, end]}, content)`, then value-type for sql. `validate_v02` returns `passed` ops carrying `_span` and `failed` ops carrying `_reasons`, which the teacher repair loop and dispatch consume. Resolver self-test on `ed_wood`: a verbatim quote resolves and passes, a paraphrase is `not found`, a quote on the wrong span fails the span check, a 2-char quote fails shape.

Spec sections v0.2 replaces: the `evidence` rule in section 5 (`[start, end]` character span, required for graph and sql) and the Evidence row in section 6 become quote-based; section 10 item 6 of `SCORE-IO-SPEC.md` records the candidate, and `reference/micro-harnesses/spike-results.md` states v0.2 should replace section 5. Owner review is pending on whether v0.2 replaces the spec or stays a spike-local deviation. Until that review, build against v0.2 and leave 001's `ops.schema.json` untouched.

## What to Avoid

- Character-offset evidence. With v0.1 `[start, end]` the frontier teacher failed 7/7 documents on the first attempt (reasoning-only replies), and when content did arrive 8/8 and 10/10 ops were Proof-rejected with "evidence span contains neither subject nor value". Small models fail the same way. Use the quote (step 9).
- Treating the empty op list as a pass. `{"ops": []}` is grammar-legal, and a 1B model takes it every time: MiniCPM5-1B emitted it on 20/20 documents (4 tokens, 0.09 s), raw prompt and chat template alike. Its `Proof-pass 1.000` is vacuous (0 ops emitted). Start at 2B-class (D-MS-05); a 1B revisit needs sampling or training, not prompting.
- Trusting the grammar to terminate. The grammar guarantees shape; only the token cap guarantees termination. MiniCPM5-2B looped one op about 66 times on `a_kiss_for_corliss` until the 1024 cap, and still looped at 2048. Keep an I4 cap on every decode step and report truncation as its own Proof category; six sweep decodes hit the 1024 cap mid-JSON (1 minicpm2b, 5 qwen8b). Raising the cap rescues parse, not accuracy (qwen8b at 2048: route 0.450 to 0.500, parse 0.75 to 0.95; `janet_waldo` parsed at 1039 tokens but only 2/20 ops passed).
- Repair prompts that re-emit passing ops. In the teacher pilot on `ed_wood`, round 1 passed 14/16; the repair reply fixed the 2 rejects but rewrote the passing ops with `...`-joined non-verbatim quotes, dropping to 4/16. Keep passing ops byte-identical in the repair prompt and accept the best round's passing set (best-round-wins fired on 9/20 documents).
- Scoring accuracy by string match across aliases. The teacher writes `Edward Davis Wood Jr.` and `1924-10-10`; students write `Ed Wood` and `October 10, 1924`. Subject/value recall and tuple F1 are strict lower bounds until a normaliser exists; compare arms on `routing_exact` (target-set match), which is alias-free.
- Putting length caps in the grammar. GBNF cannot count. A 513-char subject is grammar-admissible and Proof-rejected by design (test `split.grammar-format-proof-accuracy`); a 33-op list fails in `validate_ops`, not in the grammar.
- Importing spike code through the `databasise` package. `databasise/__init__` pulls `rfc8785`, absent from the spike venv; 001 path-loads `corpus.py` via importlib and registers it in `sys.modules` (dataclasses needs that). Keep spikes decoupled from the package import chain.
- Counting parens inside GBNF character classes. A `[...]` class containing a bare `"` broke 001's well-formedness checker until classes were stripped before string literals.
- Using the demo page for verdicts. `demo.html` is a display mirror; its XML path runs on the browser `DOMParser` and was verified by review only. The Python suite is normative.
- Prepending BOS for MiniCPM5, or tokenising prefix and section separately. The tokenizer emits no BOS (`tokenize(add_bos=True) == tokenize(add_bos=False)`), and `tok(a)+tok(b) != tok(a+b)` at the boundary. Tokenise `prefix+section` as one string (spike 002, `CONVENTIONS.md`).

## Constraints

- Op list: `maxItems 32`; top level exactly `{"ops": [...]}`; `additionalProperties: false` on every shape; one of four shapes selected by `target`.
- String limits: `s`, `o`, `subject`, `value`, `ask` 512; `p`, `attribute`, `title` 128; `why` 256; `s_type`, `o_type`, `slug`, `supersedes` 64; `unit`, `valid_from`, `valid_to` 32; `markdown` 4096; v0.2 `quote` 3 to 256.
- Value types: `date` parses with `date.fromisoformat` or `datetime.fromisoformat`, or is a 4-digit year in 1000..9999; `number` parses as a finite `Decimal`; `text` is unchecked.
- Decode caps in the compiler: rewrite 256, ops 256, text 512; text stop set `["</score>", "\n\n\n"]`. The 003 sweep decoded ops at 1024 (secondary re-decode at 2048).
- Proof categories, in check order: `schema`, `permission`, `non-empty`, `evidence`, `value-type`, `slug`; the runtime adds `truncation` (`CONVENTIONS.md`). In 003 the failure reasons came from the same Proof code that gates dispatch: evidence dominated (2b 28, 1.7b 8, 4b 51, 8b 15), then value-type (dates like "May 9, 1902", "1980s"), then truncation (8b: 5 outputs cut at exactly 1024 tokens).
- Acceptance: `.planning/spikes/001-score-io-model/run.sh` reports `95/95 checks passed`: 24 compile-refusal cases, I1 plus determinism, I2 over three decode kinds, I3, 15 grammar subsets each checked well-formed, restricted, allowed-pass, disallowed-refused, 9 fuzz mutations, Proof correct/empty/fabricated/mistyped, 11 value-type cases, evidence boundary and normalisation, folio slug lifecycle (first, duplicate, supersedes), permission, 32-vs-33 ops, schema mirror, and the spec section 8 worked example. Stdlib only, no model, no GPU lock; log in `logs/run-<utc>.jsonl`.
- Toy tokenizer caveat: 001's `encode` is a word-level stand-in (`TOKENIZER_VERSION = "toy-word-v1"`), so its I1 byte-identity is over token strings. Spike 002 re-ran I1 on MiniCPM5-2B real ids: byte-identical `E_i` lists with different neighbours, and the same string across generation history gives cosine 1.0.
- Token policy for MiniCPM5-2B: `emb=reserved:130080;rq=reserved:130081`; both ids detokenise empty and were fed live. Never prepend BOS for MiniCPM5. `llama_get_embeddings_ith` indexes the i-th output, not the position.
- Teacher labels under v0.2 (`teacher.json`): 20/20 documents accepted, 204 Proof-passing ops, 26 dropped, 47 rounds with 0 reasoning tokens (`"reasoning": {"effort": "none", "exclude": true}` merged with `OPENAI_LLM_EXTRA_BODY`, max_tokens 4096, temperature 0). Student Proof-pass on emitted ops: 2b 70/98, 1.7b 15/25, 4b 55/110, 8b 107/128 (30 to 50 percent lost, almost all on evidence and dates).
- Schema mirror: `ops_validate.py` mirrors `ops.schema.json` field-for-field and `test_spike.py` re-reads the schema from disk and asserts the mapping (`mirror.*` checks). Change one, change both, or the suite fails.
- Section content is real paragraphs from the 20 hash-verified parity documents (`databasise/tests/fixtures/corpus/`), never synthetic text; reject empty sections before embedding and enforce context limits chunker-side, since both llama.cpp paths truncate silently past `n_ctx`.

## Origin

Synthesized from spikes: 001, 003 (v0.2 deviation)
Source files available in: sources/001-score-io-model/, sources/003-op-emission-size-sweep/

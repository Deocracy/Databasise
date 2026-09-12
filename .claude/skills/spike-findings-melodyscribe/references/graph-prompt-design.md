# Graph Prompt Design

## Requirements

From the `melodyscribe` idea in `.planning/spikes/MANIFEST.md`:

- The model never authors Score directives; directives come from the chunker or the frontier skill
- Grammar constraints guarantee format only; accuracy comes from training and is measured on the rig
- No vendor benchmark settles anything; every verdict comes from a local measurement on the 20-document parity corpus
- Labelled data is teacher-generated with provenance and a fixed train/test split by document; nothing is hand-labelled and no spike trains on test documents

## How to Build It

Spike 003 measured op emission across model sizes with one schema-only zero-shot instruction (see `references/model-size-and-training.md`, step 1, and `references/score-io-contract.md`, step 9, for the v0.2 quote-evidence contract). Spike 008 kept every input byte and decode setting from 003 and varied only the prompt. This is the recipe it produced.

### Step 1: hold out the few-shot documents by a fixed rule

Few-shot examples come only from documents that are never scored. Sort the 20 teacher-labelled documents by (op count, doc id) and take the four middle entries; the other 16 are the scored set for every design, including the zero-shot baseline. From `.planning/spikes/008-graph-prompt-design/prompts.py`:

```python
def split_docs() -> tuple[list[str], list[str]]:
    """(EXAMPLE_DOCS, SCORED_DOCS) by the fixed median rule."""
    teacher = json.loads((SPIKE003 / "teacher.json").read_text())
    ranked = sorted(teacher["labels"], key=lambda d: (len(teacher["labels"][d]["ops"]), d))
    assert len(ranked) == 20
    examples = ranked[8:12]
    scored = [d for d in ranked if d not in examples]
    return examples, scored
```

On `teacher.json` (204 Proof-passing v0.2 ops over 20 docs) this yields example docs `shirley_temple` (9 ops), `adam_collis`, `deliver_us_from_evil_2014_film`, `scott_derrickson` (10 ops each). Each example block is the section text followed by its teacher ops:

```python
def example_block(doc_id: str, contents: dict[str, str]) -> str:
    ops_json = json.dumps({"ops": _teacher_ops(doc_id)})
    return f"Section:\n{contents[doc_id]}\n\nJSON:\n{ops_json}"
```

### Step 2: the eight designs

`INSTRUCTION` is imported unchanged from `.planning/spikes/003-op-emission-size-sweep/common.py`, so D0 is byte-identical to spike 003 by construction (verified on all 16 scored docs). The single-decode builder:

```python
def build_prompt(design, content, contents, examples) -> str:
    if design == "D0":
        return INSTRUCTION + "\n\nSection:\n" + content + "\n\nJSON:\n"
    if design == "D1":
        ex = example_block(examples[0], contents)
        return (INSTRUCTION + "\n\nExample:\n" + ex +
                "\n\nSection:\n" + content + "\n\nJSON:\n")
    if design == "D2":
        exs = "\n\n".join(example_block(d, contents) for d in examples[:3])
        return (INSTRUCTION + "\n\nExamples:\n" + exs +
                "\n\nSection:\n" + content + "\n\nJSON:\n")
    if design == "D4":
        return D4_INSTRUCTION + "\n\nSection:\n" + content + "\n\nJSON:\n"
    if design == "D5":
        return (INSTRUCTION + " " + vocab_hint(examples) +
                "\n\nSection:\n" + content + "\n\nJSON:\n")
    if design == "D6":
        return ("Section:\n" + content + "\n\n" + INSTRUCTION + "\n\nJSON:\n")
    if design == "D7":
        return (INSTRUCTION + " " + D7_PLAN_LINE +
                "\n\nSection:\n" + content + "\n\nJSON:\n")
```

- D0: spike 003's schema-only zero-shot instruction (baseline).
- D1: one-shot, `examples[0]` (`shirley_temple`) plus its teacher ops.
- D2: three-shot, `examples[:3]`.
- D3: two-step, entity list under its own grammar, then ops with that list in context (step 4 below).
- D4: a LightRAG-style extraction instruction adapted from `v1/lightrag/prompt.py` to emit v0.2 JSON under the same grammar: named entity types (Person, Organization, Location, Event, Content, Concept, Artifact, Other), "Extract ALL clearly stated entities first, then ALL direct binary relations", no pronouns, consistent title case. `D4_INSTRUCTION` in `prompts.py` holds the full text; the evidence and output rules are the same sentences as `INSTRUCTION`.
- D5: `INSTRUCTION` plus a predicate vocabulary hint built from the example docs' teacher ops, frequency ordered. Only 14 distinct predicates exist there (occupation (13), starring (5), role (4), down to singletons), so `most_common(30)` lists them all.
- D6: `INSTRUCTION` placed after the section instead of before it (the placement the one-pass design prefers, so the section prefix is shared across tasks).
- D7: `INSTRUCTION` plus `"Plan: list the entities, then the facts with dates, then the relations."`, thinking still disabled.

```python
def vocab_hint(examples: list[str]) -> str:
    c: Counter[str] = Counter()
    for d in examples:
        for op in teacher["labels"][d]["ops"]:
            c[op.get("p", op.get("attribute"))] += 1
    items = ", ".join(f"{k} ({v})" for k, v in c.most_common(30))
    return ("The most common predicates and attributes in labelled sections like "
            f"this one are: {items}. Prefer these spellings when they fit the "
            "section; use a new spelling only when none fits.")
```

### Step 3: the recommended prompt, D1 one-shot

Winner on the pre-registered bar and the only winner that keeps the one-pass property (one decode under the v0.2 grammar). Template from `.planning/spikes/008-graph-prompt-design/results/best-prompt.md`:

```text
<INSTRUCTION = spike-003 INSTRUCTION, byte-identical>

Example:
<example block below>

Section:
<section content>

JSON:
```

The example block (held-out doc `shirley_temple`):

```text
Section:
Shirley Temple

Shirley Temple Black (April 23, 1928 – February 10, 2014) was an American actress, singer, dancer, businesswoman, and diplomat who was Hollywood's number one box-office draw as a child actress from 1935 to 1938. As an adult, she was named United States ambassador to Ghana and to Czechoslovakia and also served as Chief of Protocol of the United States.

JSON:
{"ops": [{"target": "graph", "s": "Shirley Temple Black", "p": "date of birth", "o": "1928-04-23", "quote": "Shirley Temple Black (April 23, 1928"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "nationality", "value": "American", "value_type": "text", "quote": "was an American actress"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "occupation", "value": "actress", "value_type": "text", "quote": "American actress, singer, dancer"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "occupation", "value": "singer", "value_type": "text", "quote": "American actress, singer, dancer"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "occupation", "value": "dancer", "value_type": "text", "quote": "American actress, singer, dancer"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "occupation", "value": "businesswoman", "value_type": "text", "quote": "singer, dancer, businesswoman, and diplomat"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "occupation", "value": "diplomat", "value_type": "text", "quote": "businesswoman, and diplomat who was"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "role", "value": "United States ambassador to Ghana", "value_type": "text", "quote": "named United States ambassador to Ghana"}, {"target": "sql", "subject": "Shirley Temple Black", "attribute": "role", "value": "Chief of Protocol of the United States", "value_type": "text", "quote": "served as Chief of Protocol of the United States"}]}
```

`make_best_prompt.py` regenerates this file from the winning prompt bytes (no GPU). Numbers on Qwen3-4B: routing_exact 0.500 vs D0 0.375 (+0.125), Proof-pass 0.780 vs 0.360 (+0.420), evidence failures 22 vs 54, tokens per paragraph 523.9 vs 353.6. On MiniCPM5-2B: routing 0.562 vs 0.500 (+0.062, under the bar), Proof-pass 0.830 vs 0.754.

### Step 4: the D3 two-step variant

Step 1 decodes an entity list under a second format-only GBNF grammar (cap 256 tokens); step 2 decodes ops with that list in context (cap 1024). Combined prompt tokens, completion tokens, and seconds are reported.

```python
D3_STEP1_INSTRUCTION = (
    "List every distinct entity named in the text section below: people, "
    "works, places, organizations, events, and dates. "
    'Emit one JSON object {"entities":[...]} with each name spelled exactly '
    "as in the section. Output JSON only, no prose.")

def d3_step1_prompt(content: str) -> str:
    return D3_STEP1_INSTRUCTION + "\n\nSection:\n" + content + "\n\nJSON:\n"

def d3_step2_prompt(content: str, entities: list[str] | None) -> str:
    ent_line = ("Entities in this section: " + json.dumps(entities)
                if entities else
                "Entities in this section: (entity list unavailable)")
    return (INSTRUCTION + "\n\n" + ent_line +
            "\n\nSection:\n" + content + "\n\nJSON:\n")
```

The entity grammar is `prompts.entity_grammar()`, root `{"entities": [string, ...]}` with the same JSON string rule as the ops grammar. Step 1 parsed as a JSON entity list on 32/32 runs; the fallback line was never taken. D3 scores highest on the 4B (routing 0.562, Proof-pass 0.936, evidence failures 5) but needs two decodes and breaks the one-pass design. Choose it only when accuracy outweighs the extra pass; on the 2B it is below D0 on routing (0.250).

### Step 5: decode exactly as spike 003

From `.planning/spikes/008-graph-prompt-design/student8.py`: one GGUF loaded per process with `n_gpu_layers=-1`, `n_ctx=4096`; every load under `flock /tmp/melodyscribe-gpu.lock`; raw completion (no chat template); `temperature=0.0`, `seed=1234`, `max_tokens=1024` (256 for the D3 entity step); the v0.2 grammar from `v02_grammar.grammar_v02()`; every output scanned for `<think` and `<thinking` (0 hits on all decodes). `run.sh` runs the 2B in one process and the 4B in two halves of 8 docs (`--units`, `--suffix`), rejoined by `merge8.py`, so a kill loses at most half the arm.

### Step 6: metrics and the repeat probe

`evaluate8.py` reuses spike 003's metric definitions over the 16 scored docs only: `routing_exact` (set of target stores per section equals the teacher's, the alias-free comparator), `subjval_recall` and `op_p`/`op_r`/`op_f1` (normalised string match, strict lower bounds), `parse_rate`, `proof_pass_rate` (passed over emitted ops) with failure categories (`evidence`, `value-type`, `schema`, `unparseable-output`), tokens and seconds per paragraph, plus `d0_reproduction_vs_003` (byte equality of D0 outputs against spike 003's student files).

`probe_repeat.py` measures the noise floor: it re-decodes the D0 prompt once per named doc, compares byte-for-byte with this run's `D0_<arm>.json` and with spike 003's `<arm>.json`, and logs the first-divergence offset. Run it on the docs where D0 diverged from 003 (3 on the 2B, 7 on the 4B) before reading any design delta. Result: of 10 re-decodes, 3 matched this run and 3 matched 003; outputs diverge mid-string (first-divergence offsets 55 to 1055), near-tie flips cascading under GPU nondeterminism. Metric swing on identical prompts: 2B routing 0.438 (003) to 0.500 (rerun), Proof-pass 0.658 to 0.754; 4B routing 0.312 to 0.375, Proof-pass 0.433 to 0.360. Noise floor: about 0.06 routing_exact, about 0.10 Proof-pass.

### Step 7: results (16 scored docs, both models)

Source: `.planning/spikes/008-graph-prompt-design/README.md` Results table and `results.json` (the seconds column in `results.json` is the owner re-run; every other field is equal).

| design | arm | route | sv_rec | op_F1 | parse | proof | tok/para | s/para |
|---|---|---|---|---|---|---|---|---|
| D0 | minicpm2b | 0.500 | 0.018 | 0.000 | 0.938 | 0.754 | 285.1 | 8.58 |
| D1 | minicpm2b | 0.562 | 0.073 | 0.058 | 0.875 | 0.830 | 433.0 | 11.69 |
| D2 | minicpm2b | 0.312 | 0.243 | 0.107 | 0.875 | 0.812 | 471.6 | 13.62 |
| D3 | minicpm2b | 0.250 | 0.099 | 0.028 | 1.000 | 0.736 | 261.3 | 7.70 |
| D4 | minicpm2b | 0.000 | 0.000 | 0.000 | 1.000 | 1.000* | 5.0 | 0.19 |
| D5 | minicpm2b | 0.375 | 0.022 | 0.000 | 0.812 | 0.738 | 366.6 | 10.11 |
| D6 | minicpm2b | 0.250 | 0.052 | 0.021 | 0.875 | 0.448 | 259.9 | 7.14 |
| D7 | minicpm2b | 0.562 | 0.024 | 0.000 | 0.938 | 0.810 | 215.7 | 5.96 |
| D0 | qwen4b | 0.375 | 0.137 | 0.030 | 0.938 | 0.360 | 353.6 | 12.80 |
| D1 | qwen4b | 0.500 | 0.213 | 0.082 | 0.812 | 0.780 | 523.9 | 18.81 |
| D2 | qwen4b | 0.250 | 0.218 | 0.172 | 0.875 | 0.728 | 456.4 | 16.20 |
| D3 | qwen4b | 0.562 | 0.265 | 0.032 | 0.875 | 0.936 | 459.9 | 16.49 |
| D4 | qwen4b | 0.188 | 0.182 | 0.056 | 0.500 | 0.595 | 790.0 | 28.39 |
| D5 | qwen4b | 0.375 | 0.070 | 0.019 | 0.812 | 0.618 | 411.7 | 19.48 |
| D6 | qwen4b | 0.500 | 0.181 | 0.035 | 0.812 | 0.677 | 593.7 | 21.22 |
| D7 | qwen4b | 0.375 | 0.105 | 0.010 | 0.688 | 0.516 | 528.5 | 19.48 |

\* D4 on the 2B emitted `{"ops":[]}` on 16/16 docs, so Proof-pass 1.000 is vacuous.

Evidence failures per arm (`results.json` `fail_reasons`): 2B D0 17, D1 16, D2 18, D3 19, D5 15, D6 32, D7 11; 4B D0 54, D1 22, D2 25, D3 5, D4 34, D5 23, D6 25, D7 31. Stable-doc decomposition on the 4B (9 run-stable docs): D1 wins 6/9 vs D0 4/9, D3 5/9, D6 6/9, so the wins are not only unstable-doc flips.

### Step 8: the mechanism

Few-shot examples teach verbatim quoting. The 4B gains come almost entirely from collapsing evidence failures: 54 (D0) to 22 (D1) to 5 (D3). The 2B's evidence failures barely move with examples (17 to 16), which is why prompting helps the 4B and not the 2B. D2 lifts 2B subject/value recall from 0.018 to 0.243 and gives the 4B its best op_F1 (0.172) with its worst routing (0.250): more examples buy teacher-likeness, not routing. D5's vocabulary hint changes nothing on either model. D7's plan line costs 16 prompt tokens and mildly helps the 2B only (+0.062 routing, inside the noise floor).

### Step 9: placement is a per-model measurement

D6 (instruction after the section) is the placement the one-pass design prefers because the section prefix can then be shared across tasks. Its cost is not one number. 2B: routing 0.500 to 0.250, Proof-pass 0.754 to 0.448, evidence failures 17 to 32. 4B: routing 0.375 to 0.500 (+0.125), Proof-pass 0.360 to 0.677 (+0.317), value-type failures 3 to 6 (dates). Instruction-after-section breaks the 2B's quote grounding and improves the 4B's. Re-measure prefix-sharing cost for every model that enters the rig.

### Step 10: reproduction facts

- Owner re-run of `run.sh` (2026-09-12): all 274 student decodes (16 design-arm files plus both repeat probes) byte-identical to the agent run, every metric in `results.json` equal. Two runs of `run.sh` reproduce each other exactly.
- The divergence is elsewhere: D0 in this spike versus spike 003's D0 decodes agree on 13/16 docs (2B) and 9/16 (4B), and the in-process determinism self-check (D0's first scored doc decoded twice back-to-back) failed on the 2B (0/3 identical) and half the time on the 4B (1/2). The in-run repeat probe (step 6) sits between the two.
- Wall time on legion (RTX 3080 Laptop): 2B about 17 min for 128 decodes plus 16 step-1s plus 2 determinism checks; 4B about 33 min for 144 decodes (about 13.9 s mean); probes about 5 min; about 55 min end to end.
- Truncation at the 1024 cap hits every design (2B: 1 to 3 docs each; 4B D4: 8/16, D7: 5/16).

### Step 11: untested arms from the research recipe

`reference/micro-harnesses/deep-research-2/REPORT.md` section 5B lists the arms spike 008 did not run. They are candidates, not findings; each needs the same 16-doc scored set, the same bar, and the repeat probe before it is read.

- Schema-as-code annotation guidelines: op types as typed classes with docstrings and definitions in the prompt (GoLLIE 2310.03668), with instruction plus candidate options plus text as the alternative arm (InstructUIE 2304.08085).
- One gleaning re-prompt ("were entities missed"), capped at one (GraphRAG 2404.16130). A second decode, so it competes with D3 on cost.
- Open extraction with the schema outside the prompt, canonicalisation after (EDC 2404.03868).
- A cheap filter-after-extract pass over emitted ops, mapped onto Proof's evidence check (HippoRAG 2 2502.14802).
- Marker-token verbatim spans plus self-verification (GPT-NER 2304.10428), with Proof's substring check staying mechanical.
- Constraints derived from the incrementally built graph where attachable (DoG 2410.18415), with an unconstrained draft kept as a cross-check (BoostCD 2506.14901: constrained decoding alone substitutes wrong-but-valid entities, so grammar and Proof are non-substitutable layers).
- Training path: frontier-teacher distillation on broad unlabelled text with mission-focused instructions for entities (UniversalNER 2308.03279), reverse-direction synthesis from gold op sets for relations (SynthIE 2303.04132), mixed with real Score sections; extraction, schema conformance, and hallucination scored separately (Text2KGBench 2308.02357); soft-match scoring, never exact-match triples (Han et al. 2305.14450). Date normalisation and verbatim-quote adherence have no literature answer; spike 008 is the primary evidence.

## What to Avoid

- **LightRAG-style entity-first wording (D4).** On the 2B it collapses extraction to `{"ops":[]}` on 16/16 docs (5 completion tokens). On the 4B it explodes verbosity: 8/16 truncated at the cap, invented predicates (`is a`, `is`, `type`, `born`), `...`-joined non-verbatim quotes, 34 evidence failures. The wording does not transfer to grammar-constrained v0.2 op emission at 2 to 4B.
- **Reading three-shot recall gains as routing gains.** D2 triples 2B recall and gives the 4B its best op_F1 while routing drops to 0.312 and 0.250. Extra examples buy teacher-likeness, not routing.
- **A predicate vocabulary hint (D5).** Routing and Proof-pass stay within noise on both models. Do not spend prompt tokens on it.
- **Expecting any prompt to lift the 2B past the bar.** Best 2B deltas are D1 (+0.062 routing, +0.076 Proof-pass) and D7 (+0.062, +0.056), both inside the noise floor. The 2B's evidence failures do not move with examples; training is the path (see `references/model-size-and-training.md`).
- **Assuming one placement cost across models.** D6 costs the 2B 0.250 routing and 0.306 Proof-pass and gains the 4B 0.125 and 0.317. Measure per model.
- **Trusting single-run deltas under the noise floor.** Greedy seed-fixed decoding differs between separate harness runs on long docs (3/16 on the 2B, 7/16 on the 4B). Any delta under about 0.06 routing or 0.10 Proof-pass is not material; report it as such, never as a small win.
- **Ignoring the prompt-token cost of few-shot.** D1 raises prompt tokens from 340/353 to 874/919 per paragraph, D2 to 2308/2442 (8132 chars, inside `n_ctx` 4096 but not by much). Account for it in throughput before adopting.

## Constraints

- Pre-registered bar, stated before any run: a design is recommended only if it beats D0 by at least 0.10 routing_exact or 0.10 Proof-pass on a model. Only D1, D3, and D6 on the 4B clear it.
- Models: `MiniCPM5-2B-Q8_0.gguf` and `Qwen3-4B-Q8_0.gguf` from `.planning/spikes/.models`, full GPU offload, `n_ctx` 4096, one model per process under `flock /tmp/melodyscribe-gpu.lock`.
- Decode: raw completion (no chat template), temperature 0, seed 1234, cap 1024 tokens (256 for the D3 entity step), think tags scanned (0 hits on all 272 decodes plus 10 probe decodes).
- Grammars: the v0.2 ops grammar from `.planning/spikes/003-op-emission-size-sweep/v02_grammar.py` and the schema `ops.v0.2.schema.json`, reused read-only; the entity grammar for D3 step 1 is new in `prompts.py` (`spike008-entities-v1`) and format-only like the ops grammar. `evaluate.py`, `resolve.py`, `common.py`, and `teacher.json` are also imported read-only through `sys.path`; spike 003 was never edited.
- Prompt tokens per paragraph (2B/4B means over scored docs): D0 340/353, D1 874/919, D2 2308/2442, D3 564/610 combined, D4 465/476, D5 441/453, D6 equal to D0, D7 plus 16.
- Seconds per paragraph (agent run, README table): 2B D0 8.58, D1 11.69, D3 7.70; 4B D0 12.80, D1 18.81, D3 16.49, D4 28.39. Owner re-run timings in `results.json`: 2B D0 8.10, 4B D0 12.46.
- Scored set: 16 docs; example set: 4 docs (`shirley_temple`, `adam_collis`, `deliver_us_from_evil_2014_film`, `scott_derrickson`). Teacher labels: 204 Proof-passing v0.2 ops over 20 docs, corpus hash checked against the students and the teacher before scoring.
- Logs: one JSONL per run with ISO timestamps under `.planning/spikes/008-graph-prompt-design/logs/` (`student8-<arm>-<utc>`, `probe-repeat-<arm>-<utc>`, `score-<utc>`); student outputs under `students/D<0-7>_<arm>.json` and `D0_<arm>_rep2.json`.

## Origin

Synthesized from spikes: 008 (with 003's harness and labels); research: deep-research-2 REPORT.md sections 1 (Q4) and 5B
Source files available in: sources/008-graph-prompt-design/, sources/003-op-emission-size-sweep/

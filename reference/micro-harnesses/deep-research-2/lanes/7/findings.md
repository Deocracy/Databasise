# Lane 7 findings: Prompting small models for knowledge-graph extraction

Screened 25 candidates; admitted 24; 1 abstention (SciPhi Triplex, vendor-only).
All admitted PDFs are filed under `papers/` and start with `%PDF`.
Star/push/license facts were fetched 2026-09-12 from each repository's GitHub page
payload or commit feed (GitHub REST API was quota-exhausted from this egress IP).

## (a) Admitted items

**GraphRAG (arXiv 2404.16130; repo microsoft/graphrag, ~36k stars, MIT).**
What it is: Microsoft's pipeline that builds an entity knowledge graph from source
documents with an LLM extraction prompt (one-shot "gleaning" loop that re-prompts for
missed entities), then pre-generates community summaries for global QA. What
MelodyScribe should take: the extraction prompt pattern itself — entity/relationship
records with name, type, and description emitted in one pass per chunk, plus a second
gleaning pass that asks explicitly "were any entities missed" (diminishing returns after
one gleaning, which bounds cost). Be careful about: indexing cost and prompt size; the
maintainers now flag the project as largely in maintenance mode, and the extraction
prompts live in repo config files, not in the paper, so prompt specifics must be lifted
from the repo, not cited from the paper.

**LightRAG (arXiv 2410.05779; EMNLP 2025 Findings; repo HKUDS/LightRAG, 39594 stars, MIT).**
What it is: a graph-RAG framework whose indexing step prompts one LLM call per chunk to
emit entities, relations, and keywords, then profiles each into retrieval key-value pairs
and dedups incrementally against the existing graph. What MelodyScribe should take: the
single-pass-per-chunk discipline with an explicit dedup/merge step afterward — the
closest published analogue of Score-section in, ops out — and its lesson that keyword
profiling at write time is what makes small-model extraction retrievable later. Be
careful about: reported wins are measured with LLM-as-judge answer quality, not
extraction F1, so the extraction prompt itself is validated only indirectly.

**HippoRAG 2 (arXiv 2502.14802; ICML 2025; repo OSU-NLP-Group/HippoRAG, 3999 stars, MIT).**
What it is: a memory-flavoured retriever that runs OpenIE-style NER plus a
query-to-triple generation step, then uses an LLM triple-filtering prompt to drop
irrelevant triples before Personalized PageRank. What MelodyScribe should take: the
filter-after-extract pattern — a cheap second prompt that judges each emitted triple
against the source passage is an effective, measured substitute for trusting the first
emission, and maps directly onto Proof's evidence-quote check. Be careful about: the
reference runs use Llama-3.3-70B for extraction and NV-Embed-v2 for retrieval, so no
small-model extraction numbers can be read off; the pattern transfers, the scores do not.

**KGGen (arXiv 2502.09956; NeurIPS 2025; repo stair-lab/kg-gen, 1269 stars).**
What it is: a text-to-KG generator using two DSPy signature stages (entities from text,
then subject-predicate-object relations given text plus entities) followed by iterative
LM-based clustering that merges duplicate entities and edges, plus the MINE benchmark
for extraction fidelity. What MelodyScribe should take: everything about stage two —
entities-then-relations as separate prompts beats one-step emission, and the clustering
resolver is the concrete fix for the sparse, near-duplicate node sets that one-pass
extraction produces. Be careful about: the reference extractor is Gemini 2.0 Flash, so
replication needs a small-model rerun (Spike 008); MINE measures retrieval/information
retention, not triple F1, so it complements rather than replaces validator metrics.

**EDC (arXiv 2404.03868; EMNLP 2024; repo clear-nus/edc, 193 stars, MIT).**
What it is: Extract-Define-Canonicalize — few-shot open extraction with no schema in
the prompt, then a define step that writes relation definitions, then post-hoc
canonicalization to a target schema, with a trained Schema Retriever so large schemas
never enter the context window. What MelodyScribe should take: the core ordering
insight — do not put the schema in the extraction prompt; extract open, canonicalize
after — plus the schema-retriever trick as the fallback if the op vocabulary outgrows
the prompt. Be careful about: refinement (EDC+R) iterates with the LLM and multiplies
cost per section; measure whether one canonicalization pass suffices at 2B scale.

**iText2KG (arXiv 2409.03284; WISE 2024; repo AuvaLab/itext2kg, 965 stars, Apache-2.0).**
What it is: a zero-shot, topic-independent pipeline with four modules — Document
Distiller (blueprint-guided reformulation), incremental entity extractor, incremental
relation extractor, Neo4j integrator — where entities and relations are extracted by
separate prompts and matched incrementally with embedding similarity. What MelodyScribe
should take: the strongest published evidence for the two-step split (citing Carta et
al., separation "positively impacts performance") and the blueprint device, which is the
same idea as MelodyScribe's human-authored skill: a short user-defined schema steering a
zero-shot extractor. Be careful about: the follow-up ATOM paper reports that separate
extraction steps double LLM calls and strand isolated entities, so budget the second
pass and plan an orphan-sweep.

**ChatIE (arXiv 2302.10205; repo cocacola-lab/chatie, 826 stars).**
What it is: a two-stage multi-turn QA reformulation of zero-shot IE — stage one finds
which types appear, stage two chain-extracts per type with templated questions — gaining
~16.6 points average over single-turn prompting across six datasets. What MelodyScribe
should take: the measured value of decompose-before-extract, and the template-plus-prior-turns
prompt shape as the candidate Spike 008 condition against one-step emission. Be careful
about: multi-turn means many serial LLM calls per section, which fights the
one-forward-pass budget; treat ChatIE as the quality ceiling for staged prompting, not
the deployable shape.

**GoLLIE (arXiv 2310.03668; ICLR 2024; repo hitz-zentroa/GoLLIE, 443 stars, Apache-2.0; weights HiTZ/GoLLIE-7B/13B/34B).**
What it is: Code-LLaMA models fine-tuned to follow annotation guidelines rendered as
Python classes with docstrings, generalizing to unseen schemas and beating prior
zero-shot SoTA; ablations show detailed guidelines, not just label names, carry the
gain. What MelodyScribe should take: the single most transferable prompt discovery in
this lane — schema-as-code with definitions outperforms schema-as-list, and guideline
following must be fine-tuned in (even the largest models fail at it out of the box).
Be careful about: checkpoints are 7B–34B CodeLLaMA, too large for the 2B harness, so
MelodyScribe must distill the pattern down, not reuse the weights; training used
anti-memorization noise (class shuffling) that a small rerun should copy.

**UniversalNER (arXiv 2308.03279; ICLR 2024; repo universal-ner/universal-ner, 375 stars, MIT; UniNER-7B/13B).**
What it is: targeted distillation — ChatGPT labels diverse web text for NER,
instruction-tuning on LLaMA yields 7B/13B students that beat ChatGPT by 7–9 F1 points
and beat supervised multi-task systems, over a 43-dataset benchmark. What MelodyScribe
should take: the training recipe for the entity half of the harness — distill a
frontier teacher on broad unlabeled text with mission-focused instructions rather than
collecting labels — directly answering Spike 003's "accuracy is a training result."
Be careful about: it covers entities only; relations need the same treatment (see
SynthIE/InstructUIE), and the released data inherits ChatGPT-use restrictions.

**GPT-NER (arXiv 2304.10428; Findings of NAACL 2025).**
What it is: a bridge from sequence labeling to generation — entities are marked inline
with `@@entity##` special tokens, and a self-verification prompt asks the model whether
each extracted span really belongs to its tag, fixing the dominant failure (NULL inputs
over-confidently labeled as entities) to reach supervised parity. What MelodyScribe
should take: two mechanisms — marker-token extraction that keeps verbatim source spans
(the ancestor of evidence quotes) and self-verification as the cheapest validator
(ask-the-model-to-confirm, one extra pass). Be careful about: self-verification doubles
calls and can confirm its own hallucinations; Proof's substring check must stay
mechanical, not model-judged.

**MiniRAG (arXiv 2501.06713; ACL 2026; repo HKUDS/MiniRAG, 2013 stars, MIT).**
What it is: a graph-RAG system designed for small language models, replacing
abstraction-heavy indexing with a heterogeneous chunk-entity graph and
topology-enhanced retrieval, reaching 1.3–2.5x lightweight-baseline effectiveness at a
quarter of the storage. What MelodyScribe should take: the design rule that entity
extraction is the SLM-easy task while query abstraction is the SLM-hard one — so the
harness should spend the small model's capacity on entity/relation emission and lean on
graph topology at retrieval time. Be careful about: the paper's SLMs are used with
lightweight embeddings alongside; extraction-quality ablations by model size are thin,
so Spike 008 still has to measure the 2B point.

**Zep / Graphiti (arXiv 2501.13956; repo getzep/graphiti, 30832 stars, Apache-2.0).**
What it is: a temporal knowledge-graph memory layer — episodes ingested raw, then
entity/fact/temporal extraction, entity resolution against the live graph, edge dedup
scoped to same-entity-pair candidates, and bi-temporal invalidation when new facts
contradict old ones. What MelodyScribe should take: the production-grade resolution
playbook (scope dedup to candidate pairs to bound cost; invalidate rather than delete;
keep raw episodes for provenance) and the hard lesson documented on its own site that
small models without structured-output support break ingestion. Be careful about: it is
an agent-memory service, not a bulk document pipeline — throughput-per-section numbers
do not transfer, only the write-path discipline does.

**Text2KGBench (arXiv 2308.02357; ISWC 2023; repo cenguix/Text2KGBench, 92 stars, Apache-2.0; data CC BY 4.0).**
What it is: the benchmark for ontology-driven KG generation — 10 Wikidata-TekGen plus
19 DBpedia-WebNLG ontologies with aligned sentences, seven metrics split across fact
extraction, ontology conformance, and hallucination, with Vicuna-13B/Alpaca-LoRA-13B
baselines generated by automatic prompting. What MelodyScribe should take: the metric
split itself — Spike 008 should score extraction, schema conformance, and hallucination
separately, since the baselines show models fail these independently — and the
automatic-prompt-from-test-case harness as a template. Be careful about: baselines are
13B chat models with small-by-design ontologies; results say room-for-improvement, not
what a 2B model scores.

**GenIE (arXiv 2112.08340; NAACL 2022).**
What it is: the first end-to-end autoregressive closed-IE system — BART generating
linearized triplets under a bi-level constrained beam search (structure constraint plus
trie constraints over valid entity/relation identifiers from Wikidata). What
MelodyScribe should take: the original proof that schema constraints belong in the
decoder, not the prompt, when the schema is large — the direct precedent for enforcing
the op grammar mechanically while keeping the prompt small. Be careful about: closed
schema over Wikidata-scale KBs is the opposite of MelodyScribe's open per-section
extraction; lift the trie-constraint mechanism, not the closed-world assumption.

**SynthIE (arXiv 2303.04132; EMNLP 2023; repo epfl-dlab/SynthIE, 63 stars, MIT).**
What it is: asymmetric synthesis — prompt the LLM in the easy reverse direction
(triples to fluent text) to mint 1.8M pairs, then train 220M/770M T5-based extractors
that beat prior same-size SoTA by 57 micro-F1 points. What MelodyScribe should take:
the cheapest path to a trained 2B extractor — generate text from the harness's own gold
op-sets (reverse direction) rather than labeling extractions — plus the warning,
confirmed by BoostCD, that synthetic-only training degrades out of distribution, so mix
in real Score sections. Be careful about: the 220M/770M wins are in-distribution on
Wikidata-shaped data; expect a discount on MelodyScribe's domain until measured.

**InstructUIE (arXiv 2304.08085; repo BeyonderXX/InstructUIE, 396 stars, MIT).**
What it is: FlanT5-11B multi-task instruction tuning over IE-INSTRUCTIONS (32 datasets
unified to instruction+options+text in, natural-language structure out), with auxiliary
span-extraction and typing subtasks, beating GPT-3.5 zero-shot and matching BERT
supervised. What MelodyScribe should take: the instruction format (task instruction,
candidate options, text) as the tested alternative to GoLLIE's code format for Spike
008, and the auxiliary-task trick — train span-finding and typing separately to support
the relation pass. Be careful about: 11B backbone and 32-dataset mixture exceed a 16 GB
single-GPU budget in full; subsample the mixture or LoRA it (lane 2's recipes apply).

**BoostCD (arXiv 2506.14901).**
What it is: Boosted Constrained Decoding — decode twice (constrained and
unconstrained), then a learned autoregressive booster fuses the two drafts; documents
that constrained decoding alone makes models substitute wrong-but-valid entities
("Carol Douglas" for an out-of-KB mention) while fixing formatting errors, and BoostIE
beats both modes in and out of distribution. What MelodyScribe should take: the
error model for grammar-constrained ops — constraints trade validity for silent entity
corruption — which justifies Proof checking entity strings against source text and
suggests keeping the unconstrained draft as a cross-check signal. Be careful about: the
booster is a second trained model, i.e. a second forward pass, in tension with the
one-pass budget; use the finding diagnostically unless serving allows two passes.

**DoG (arXiv 2410.18415; ACL 2025).**
What it is: Decoding on Graphs — a training-free KGQA framework defining well-formed
chains (entity-linked triplet sequences from question to answer) and enforcing them with
a graph-topology-derived token mask plus beam search, beating prompting-only baselines
on identical inputs across open-source LLMs. What MelodyScribe should take: the
complement to GenIE-style static masks — constraints derived from the live graph being
built, so each emitted op must attach to a known entity; this is the decoding-side
version of Proof's evidence rule. Be careful about: it constrains reasoning over an
existing KG, not extraction of a new one; porting it to construction means masking
against the incrementally built graph, which no paper here measures.

**Papaluca et al. triplet extraction (arXiv 2312.01954; KaLLM 2024).**
What it is: a head-to-head of triplet-extraction prompts ("extract up to N triplets as
subject/predicate/object") across LLMs of different sizes in zero- and few-shot
settings. What MelodyScribe should take: the only direct size-vs-prompt study in the
lane — the few-shot-vs-zero-shot delta per model size is the prior Spike 008 needs for
its prompt-ablation design. Be careful about: it is a workshop study with a narrow
triplet prompt; entity typing, definitions, and canonicalization are all absent, so do
not read it as a full-pipeline result.

**Han et al. empirical IE study (arXiv 2305.14450; v1 titled "Is Information Extraction Solved by ChatGPT?").**
What it is: GPT-4 assessed on 17 datasets and 14 IE subtasks on performance,
evaluation criteria, robustness, and error types — finding a visible gap to SOTA,
proposing soft-matching evaluation, and naming "unannotated spans" the dominant error
plus weak subject-object relation understanding. What MelodyScribe should take: the
error taxonomy (unannotated-span dominance argues for recall-oriented validator
thresholds, not precision-only) and the soft-matching lesson — Spike 008 metrics must
not use exact-match triple scoring or they will understate a 2B extractor. Be careful
about: GPT-4-era prompting results; the gap sizes do not transfer to fine-tuned small
models, only the error categories do.

**Carta et al. iterative zero-shot KG (arXiv 2307.01128).**
What it is: a pipeline of per-component iterative zero-shot prompts (no examples, no
external resources) for domain KG construction, evaluated on one domain dataset. What
MelodyScribe should take: a minimal baseline condition for Spike 008 — iterative
zero-shot per component, no few-shot examples — to isolate what examples and
guidelines add. Be careful about: single-domain evaluation with no released artefact
found; treat as a prompt-shape reference, not an evidence-grade result.

**XGrammar (arXiv 2411.15100; MLSys 2025; repo mlc-ai/xgrammar, 1882 stars, Apache-2.0).**
What it is: a structured-generation engine — byte-level pushdown automaton over
context-free grammars with prechecked context-independent tokens, persistent execution
stack, and GPU-overlapped mask computation, reporting up to 100x speedups and
near-zero end-to-end overhead. What MelodyScribe should take: the enforcement engine
for the op grammar — if Proof's validator moves into the decoder, this is the
zero-overhead way to do it on one GPU. Be careful about: it guarantees syntactic
validity only (cf. BoostCD's corruption finding); semantic checks stay in Proof.

**JSONSchemaBench (arXiv 2501.10868).**
What it is: a 10K-schema benchmark of real-world JSON schemas plus the JSON Schema Test
Suite, evaluating six constrained-decoding frameworks (Guidance, Outlines, LlamaCpp,
XGrammar, OpenAI, Gemini) on efficiency, coverage, and output quality. What MelodyScribe
should take: the coverage dimension — grammar engines fail on different constraint
shapes, so the op grammar must be tested against the bench's failing classes before
committing the harness to one engine. Be careful about: JSON Schema is not an
extraction grammar; transfer the engine comparison, not the absolute scores.

**UIE (arXiv 2203.12277; ACL 2022; repo universal-ie/UIE, 955 stars).**
What it is: the unified text-to-structure framework — Structured Extraction Language
(SEL) linearizes entities/relations/events into one representation, and the Structural
Schema Instructor (spot/associate/generate control) with the
first large-scale text-to-structure pre-training. What MelodyScribe should take: SEL is
the template for the op linearization (one decodable span language for triples, rows,
and skill markdown headers) and SSI the template for the prompt's control tokens. Be
careful about: 2022-era encoder-decoder pre-training at small scale; the representation
idea transfers, the checkpoints do not compete with instruction-tuned SLMs.

## (b) Refutations

1. **"Triplex" is a paper we can cite.** No primary publication found. Triplex is a
vendor-released Phi-3-3.8B finetune for KG construction (SciPhi, via Hugging Face
`SciPhi/Triplex`, blog and R2R cookbook as secondary sources). Its "beats GPT-4 at
1/60th cost" claim is vendor-reported and unverified. Do not cite it as literature;
screen small-model extraction claims against Papaluca et al. (2312.01954) and MiniRAG
(2501.06713) instead.
2. **"A grammar constraint makes extraction output trustworthy."** Contradicted by
BoostCD (2506.14901): constrained decoding alone substitutes wrong-but-schema-valid
entities and can score worse than unconstrained generation on correctness. For
MelodyScribe's Proof validator this means syntax enforcement (XGrammar/GenIE-style)
and semantic verification (evidence quotes, date checks) are non-substitutable layers.
3. **"Prompting a frontier model suffices for extraction quality."** Contradicted by Han
et al. (2305.14450): GPT-4 shows a visible gap to supervised SOTA across 14 IE
subtasks, with relation understanding specifically weak — and by GoLLIE (2310.03668):
even the largest models fail to follow annotation guidelines out of the box.
Extraction accuracy must be trained in (UniversalNER, SynthIE, GoLLIE recipes), which
corroborates Spike 003's "accuracy is a training result."
4. **"The schema must be in the extraction prompt."** Contradicted by EDC (2404.03868):
open extraction followed by post-hoc canonicalization handles schemas far larger than
the context window, with no parameter tuning. MelodyScribe's op vocabulary can live in
Proof/grammar rather than in the prompt.

## (c) Unresolved ledger

- **SciPhi Triplex run details** — no paper, no training report; abstained (secondary sources only).
- **SciPhi R2R extraction prompts** — vendor cookbook/docs only; not screened as primary.
- **Full prompt texts of GraphRAG/LightRAG/HippoRAG2/KGGen** — papers describe the
stages; exact prompt files live in repos and were not individually opened. Prompt-shape
claims above rest on paper text, not prompt diffs.
- **Date normalisation for extraction** — no dedicated primary source screened; SUTime
and LLM date-canonicalization studies were out of lane budget. Gap for Proof's date-format
failures (Spike 003: 30–50% op failures include dates).
- **Prompt placement (instruction before vs after the document; marker position)** —
no direct study found in this lane; brief Q3/lane 5 owns instruction effects, Spike 007
owns measurement. Nothing admitted here answers it.
- **Evidence-quote failure rates** — only indirect evidence (MINE retention in KGGen,
hallucination metrics in Text2KGBench, NULL-hallucination in GPT-NER). No paper measures
verbatim-quote adherence of small extractors directly.
- **Per-size extraction numbers for ≤3B models** — Papaluca et al. span sizes but the
lane did not extract its tables; Spike 008 must re-read 2312.01954 Tables before
finalizing its size ablation.
- **Repo artefacts not located** — GPT-NER, BoostCD, DoG, Papaluca-TE, Han-study, Carta
state or imply code/data releases, but exact URLs were not captured (GitHub API
quota-exhausted); recorded as unverified in inventory.tsv.
- **KGGen/GoLLIE licenses** — kg-gen repo license badge not captured; recorded as
unverified. Check before vendoring.

## (d) Security findings (stated as requirements)

- **R7-1 Instruction/data separation.** Extraction prompts ingest untrusted document
text; the harness prompt must delimit instruction, schema/guidelines, and document
spans so document content cannot become extraction instructions. Rationale: all staged
pipelines here (ChatIE, EDC, KGGen) concatenate prior outputs into later prompts,
which compounds injection across stages.
- **R7-2 Mechanical evidence verification.** Every emitted triple/row must carry a
verbatim source quote checked by substring match, never by model self-judgment.
Rationale: GPT-NER shows models over-confidently confirm their own NULL-labels, and
BoostCD shows constrained-correct-looking output can be semantically wrong.
- **R7-3 Provenance-preserving resolution.** Entity/edge merges across sections must
record source spans and never silently rewrite earlier facts; contradictions require
explicit invalidation records (Graphiti bi-temporal pattern), because incremental
matchers (iText2KG, KGGen clustering) otherwise let later untrusted text corrupt the
graph without audit.

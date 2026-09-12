# Lane 6 findings: Extraction fine-tunes and their datasets

Screened 36 candidates; 33 admitted, 3 abstained. All admitted items were opened
at a primary source (arXiv abs page and usually the full text, the ACL Anthology
page, the repository, or the Hugging Face record) on 2026-09-12. All 33 PDFs are
in `papers/`. This lane bears on brief questions 1 (structured-output
fine-tuning) and 2 (fine-tuning datasets from documents).

## (a) Admitted items

**GenIE (2112.08340, NAACL 2022) — the template for grammar-constrained
extraction fine-tuning.** First end-to-end autoregressive closed IE: a BART
model generates relations and entities as text under a bi-level constrained
generation strategy so only schema-valid triplets can be produced. It beat
pipelines, generalized from fewer examples, and scaled to far larger schemas.
MelodyScribe should take the constrained-decoding-plus-training pattern:
constraints are not a post-filter but part of the training/inference contract,
exactly what Proof needs at the op-emission end. Careful: GenIE trains on
REBEL's distantly-supervised Wikipedia abstracts, so its alignment between
triples and text is weak — the same evidence-quote failure spike 003 sees.
Code + 27.7 GB data/models released (MIT; epfl-dlab/GenIE, 104 stars).

**SynthIE (2303.04132, EMNLP 2023) — the closest existing answer to "the
dataset question".** Exploits an asymmetry: generating fluent text from
triples is easy for an LLM, extracting triples from text is hard. So it
synthesizes 1.8 M text-from-triples points and fine-tunes small models (220 M
and 770 M parameters), beating equal-size prior SOTA by 57 absolute micro-F1
and 79 macro-F1 points, with human evaluation rating the synthetic data above
existing datasets. MelodyScribe should copy this direction (teacher writes
documents from gold ops, student learns ops-from-documents) for its joint
dataset. Careful: SynthIE itself does not generalize outside its training
distribution (shown by BoostCD), so the recipe needs the diversity/filtering
steps, not just volume. Code, data, models released (MIT; epfl-dlab/SynthIE).

**BoostCD / BoostIE (2506.14901, EMNLP 2025) — the most directly relevant
2025 result.** A boosted autoregressive model fuses one constrained and one
unconstrained decode of a base model into a final prediction; the two modes'
mistakes are complementary. BoostIE beats SynthIE by 17.05 micro-F1 points
in-distribution and ~11 points out-of-distribution, with a full error analysis
of vanilla constrained decoding's failure modes. Training data came from
running GenIE and SynthIE constrained, then letting GPT-4 pick the better
triplet set (discarding both-bad samples) — a teacher-judge pipeline
MelodyScribe can replicate with Proof as the judge instead of GPT-4. Careful:
inference costs three model runs, and the training entity distribution is
admitted to be skewed (Wiki-cIE Code centers triplets on one or two
entities). Code, models, data released (MIT; epfl-dlab/BoostCD).

**GoLLIE (2310.03668, ICLR 2024) — guideline-following as the harness
interface.** Fine-tunes LLMs to consume annotation guidelines written as
Python class definitions and follow them on unseen IE tasks; detailed
guidelines, not just labels, drive zero-shot gains. For MelodyScribe this is
the precedent for putting the op grammar and evidence rules in the prompt as
code-like guidelines and training the model to obey them. Careful: it is a
7B+ scale result and does not report 0.5–3 B numbers, so transfer to MiniCPM5
scale is unproven. Code released, Apache-2.0 (hitz-zentroa/GoLLIE, 443 stars).

**UniversalNER (2308.03279, ICLR 2024) — targeted distillation, the small-model
playbook.** Distills ChatGPT NER annotations on Pile passages (Pile-NER-type,
gpt-3.5-turbo-0301, CC-BY-NC-4.0) into 7B/13B students with mission-focused
instruction tuning: +7–9 F1 over the ChatGPT teacher, +30 over Alpaca/Vicuna,
across a 43-dataset/9-domain benchmark — and it beats the supervised
InstructUIE-11B without any direct supervision. The ablation that matters for
spike 011: supervised-only training reaches 57.2% F1, continual fine-tuning of
the distilled model reaches 60.0% — distillation first, supervision second,
stacks. Careful: the artefacts are research-only (CC-BY-NC-4.0, LLaMA/ChatGPT
license encumbrance), so MelodyScribe can copy the recipe but not ship the
weights. Recipe + data + models released (MIT code; universal-ner/universal-ner,
375 stars; Universal-NER/* on HF).

**REBEL (Findings of EMNLP 2021; no arXiv version) — the linearization all
later work inherits.** Frames RE as seq2seq with a triplet linearization on
BART covering 200+ relation types; a few epochs of fine-tuning transfer it to
most RE/RC benchmarks. MelodyScribe's op emission is the same idea with a
stricter grammar. Careful: distantly supervised, no negatives, exhausted
schemas — GenIE and SynthIE both had to fix its alignment problems, and spike
003's evidence-quote failures are this failure mode recurring. Code + rebel-large
checkpoint released (Babelscape/rebel, 576 stars; HF CC-BY-NC-SA-4.0).

**REDFM / mREBEL (2306.09802, ACL 2023) — how to fix REBEL properly.** NLI
model filters distant triples, a Triplet Critic removes bad ones, and the
resulting silver data trains mREBEL, the first end-to-end multilingual model
emitting typed triplets in 7 languages — with no further tuning needed on the
human-revised gold set. This is the filtering stage MelodyScribe's synthetic
pipeline needs between teacher generation and student training. Careful:
silver-data quality claims rest on their own critic; keep Proof (not a learned
critic) as the final gate. Data + checkpoints released per the paper.

**WebIE (2305.14293, ACL 2023) — negatives and faithfulness.**
Generative IE trained on C4 web text with negative examples (which WikiNRE
and REBEL lack), ~21 K crowdsourced triples plus a 4-language mWebIE, showing
better out-of-domain generalization; entity-linking auxiliary objectives
improve faithfulness. Two direct lessons: MelodyScribe's fine-tuning set
needs explicit negatives (sections with zero ops), and an auxiliary
verbatim-span objective is evidence that quote-faithfulness can be trained,
not just validated. Careful: reproduction needs a 350 GB C4 cache and the
released annotations are CC BY-NC-4.0. Annotations + scripts released
(amazon-science/webie, 8 stars).

**Re-DocRED (2205.12696, EMNLP 2022) — the false-negative warning for any
document-level fine-tune.** 64.6% of triples were missing from DocRED;
re-annotating 4,053 documents bought ~13 F1 points, plus finer metrics
(frequent vs long-tail, intra vs inter). Any MelodyScribe train/dev split on
sectioned documents must assume distantly-supervised labels are incomplete
and budget a human re-annotation pass on the eval split, or Proof-pass rates
will punish correct-but-unlabeled ops. Dataset + eval code released (MIT;
tonytan48/re-docred, 68 stars).

**DocRED (1906.06127, ACL 2019) — the document-level benchmark to reuse.**
132 K entities of human-annotated Wikipedia/Wikidata document RE plus distant
supervision. Useful as an external regression set for the entity/relation half
of MelodyScribe's ops; not a substitute for harness-specific eval.

**USM (2301.03282, AAAI 2023) — the non-generative alternative at small
scale.** Decomposes IE into structuring + conceptualizing via three directed
token-linking ops; a 356 M model beats UIE-large by 5.11 points few-shot and
matches GPT-3 175B-era zero-shot RE. Relevant as a fallback if autoregressive
op emission keeps failing Proof at 2 B: matching verbalized labels in one
pass is cheaper and more faithful than generating them. Careful: token-linking
cannot compose Folios or free-text evidence rationales, so it covers only the
triple half of the harness.

**ReLiK (2408.00103, Findings of ACL 2024) — retriever-reader closed IE on an
academic budget.** A retriever proposes candidate entities/relations and a
shared reader links spans and predicts relations in a single forward pass,
with SOTA EL+RE at tiny→XL sizes (tiny/small checkpoints on HF). This is the
existence proof that sub-billion extraction can be state-of-the-art when
retrieval narrows the decision space — the closest architectural cousin to
MelodyScribe's "one forward pass per section" constraint. Code + checkpoints
released (SapienzaNLP/relik, 518 stars).

**GLiNER (2311.08526, NAACL 2024) — small-model zero-shot NER that beats
ChatGPT.** Span/entity-type dot-product matching on a DeBERTa-v3 encoder,
trained on Pile-NER, parallel (non-autoregressive) extraction, deployable on
CPU with INT8/ONNX. If MelodyScribe splits entity mention detection from
relation assembly, GLiNER is the component to lift. Massively reused codebase
(urchade/GLiNER, 3641 stars, Apache-2.0). Careful: NER only — no relations,
no evidence discipline.

**GLiREL (2501.03172, NAACL 2025) — the relation half to pair with GLiNER.**
Classifies every entity pair against every candidate label in one forward
pass; SOTA on FewRel/WikiZSL zero-shot; contributes a synthetic-data
generation protocol with diverse relation labels. The entity-pair
enumeration cost is exactly what MelodyScribe should measure before adopting.
Code + data protocol released (jackboyla/GLiREL, 290 stars).

**GLiNER2 (2507.18546, 2025 preprint) and GLiDRE (2508.00757, 2025 preprint)
— the 2025 GLi-family extensions.** GLiNER2 adds multi-task IE behind a
schema-driven interface; GLiDRE extends the bi-encoder to document-level RE.
Watch these for a non-generative document-level baseline; neither's artefacts
were checked this round.

**KnowCoder (2403.07969, ACL 2024) — schemas as Python classes, the strongest
GoLLIE successor.** A 30 K-type code-style schema library from Wikidata, 1.5 B
tokens of code pretraining for schema understanding, then instruction tuning
for schema following: +49.8% few-shot over LLaMA2, +12.5% zero-shot and
+21.9% low-resource over SOTA, +7.5% supervised. The two-phase
(understand-then-follow) split maps directly onto spike 011's arms, and the
schema library is reusable for generating MelodyScribe's op-iztype
vocabulary. Careful: base models are 7 B+; the 1.5 B-token pretraining bill
is the cost to replicate. Code + schema + data + model released
(ICT-GoKnow/KnowCoder, 108 stars).

**InstructUIE (2304.08085, 2023 preprint) — multi-task instruction tuning at
scale.** IE INSTRUCTIONS unifies 32 datasets text-to-text; FlanT5-11B matches
BERT supervised and far exceeds GPT-3.5 zero-shot. Mostly a scale/datapoint
for the "instructions on the query side" finding (spike 007 agrees with its
format), and its benchmark is reusable. Careful: 11 B backbone — not a small-
model recipe.

**UIE (ACL 2022) and RexUIE (2304.14770, Findings of EMNLP 2023) — the
generation lineage.** UIE's structural schema instructor + structured
extraction language is the original text-to-structure harness; RexUIE makes it
recursive so n-ary schemas (quadruples/quintuples — MelodyScribe's multi-slot
ops) extract, with 3 M distantly-supervised JERE pretraining. RexUIE's
recursive-query framing is worth stealing for ops with more than
(subject, relation, object).

**PIVOINE (Findings of EMNLP 2023) — open-world instruction tuning.** Targets
open-world entity profiling rather than closed-schema extraction, the right
reference when MelodyScribe's schema meets unseen entity types.

**YAYI-UIE (2312.15548, 2023 preprint) — chat-then-extract two-step SFT.**
Dialogue fine-tuning first for instruction following, then IE instruction
tuning on a large Chinese benchmark plus English data, keeping both
languages. A concrete two-stage SFT ordering datapoint for spike 011's
schedule arm. Careful: no small-model (<7 B) ablation reported.

**ChatIE (2302.10205, 2023 preprint) — two-stage QA decomposition.**
Type-filtering then per-type chained extraction over RE/NER/EE, beating some
full-shot models. This is the inference-time analogue of spike 008's
entities-then-relations win — evidence the decomposition helps at train time
too. Careful: ChatGPT-dependent, no released fine-tune.

**GENRE (2010.00904) and mGENRE (2103.12528) — constrained generation for
linking.** Autoregressive entity-name generation with constrained beam search
(cross-encoding mention and entity) and its 100+-language multilingual
successor. The canonicalization step of MelodyScribe's ops (linking mentions
to entities) should use constrained decoding in this style rather than free
generation plus validation.

**KnowCoder-X (2411.04794, 2024 preprint) — cross-lingual IE alignment.**
Distills proprietary-model IE alignment, then Chinese+English instruction
tuning; evaluated on 64 benchmarks with +30% over ChatGPT cross-lingual and
coverage of 20 low-resource African languages. Relevant only if MelodyScribe
goes multilingual; otherwise a datapoint that alignment-transfer works.

**Text2KGBench (2308.02357, ISWC 2023) — the eval protocol to adopt.**
Ontology-conditioned fact extraction with seven metrics: P/R/F1 plus ontology
conformance plus subject/relation/object hallucination, over 10 Wikidata and
19 DBpedia ontologies (~18 k sentences), with Vicuna-13B/Alpaca-LoRA-13B
baselines. MelodyScribe should lift the conformance + hallucination metric
split for Proof-adjacent reporting: report extraction F1 and schema/quote
conformance separately instead of one Proof-pass number. Benchmark + code
released (cenguix/Text2KGBench).

**DREEAM (2302.08675, EACL 2023) and Eider (2106.08657, Findings of ACL 2022)
— evidence supervision for document RE.** DREEAM supervises attention heads
directly with sentence-evidence distributions (zero extra parameters) and
self-trains evidence retrieval on distant data; Eider jointly trains RE with
a lightweight evidence extractor on heuristic silver labels plus
inference-stage fusion. DREEAM's attention-supervision is the cheapest known
way to teach "which sentence supports this triple" — directly applicable to
MelodyScribe's verbatim-quote requirement as an auxiliary loss. DREEAM code
released (YoumiMa/dreeam).

**EDC (2404.03868, EMNLP 2024) — open-schema KGC with a schema retriever.**
Decomposes construction into extract, define, canonicalize, and trains a
retriever so large schemas never enter the LLM prompt. Two takeaways: the
define/canonicalize split is how to keep open-extracted relations from
fragmenting, and schema retrieval (rather than full-schema prompting) is the
fix if MelodyScribe's op vocabulary outgrows the section prompt.

**KGGen (2502.09956, 2025 preprint) — recent LLM KGC pipeline baseline.**
Included as a 2025 reference point for plain-text-to-KG extraction; no
artefacts verified this round.

**R1-RE (2507.04642), MR-UIE (2509.09082) — 2025 RL-for-extraction entries.**
RLVR for cross-domain RE and RL with multi-perspective reasoning for UIE.
Unassessed beyond abstracts here; they belong to lane 4's RL brief, noted for
the validator-as-reward question (Proof as reward needs exactly this
machinery).

## (b) Refutations

None. No primary source contradicted a brief claim. Two near-misses checked
and dismissed: (1) the brief implies small-model extraction fine-tunes are
under-surveyed — confirmed true, most SOTA numbers are 7 B+ with 0.5–3 B
results rare (SynthIE 220M/770M, ReLiK tiny/small, GLiNER sub-500M, NuExtract
0.5B-vendor-only are the exceptions); (2) BoostCD's claim that constrained
decoding hurts OOD extraction qualifies, but does not contradict, the
pro-constraint stance — it says combine both modes, not drop constraints.

## (c) Unresolved ledger

- **Triplex (SciPhi Triplex, HF SciPhi/Triplex, Ollama dog/triplex)** —
abstain: vendor pages only, no paper or technical report found; base model,
training data, and license undisclosed. Revisit if a report appears.
- **NuExtract family (numind/NuExtract*, numindai/nuextract)** — abstain as a
research claim (no paper; recipe undisclosed) but flag as a reusable
artefact: 0.5 B (Qwen1.5), 3.8 B (Phi-3-mini), 7 B, and 4 B VLM variants,
MIT/Apache-2.0, purely extractive JSON-template decoding, fine-tunable from
~30 examples per the vendor. Vendor claims only.
- **WikiNRE** — abstain: cited inside the WebIE paper as a no-negatives
distant baseline, but no primary source was located this round.
- **GENRE/mGENRE artefacts** — papers admitted; checkpoint/code release
status not verified (facebookresearch/GENRE not checked against live API
before the rate limit); treat as unverified.
- **UIE, InstructUIE, USM, RexUIE, PIVOINE, YAYI-UIE, ChatIE, EDC, KGGen,
GLiNER2, GLiDRE, R1-RE, MR-UIE, Eider, DocRED, mGENRE** — papers admitted;
code/checkpoint release status not individually verified. Do not cite them as
reusable artefacts without a follow-up check.
- **Small-model (<3 B) extraction numbers** remain sparse everywhere except
SynthIE, ReLiK-small/tiny, GLiNER sizes, and vendor-only NuExtract-tiny: the
literature measures 7 B+ and distills down, rarely training small from
scratch. This gap is real and should be stated in the main report.

## (d) Security findings

No prompt-injection or exfiltration content was encountered (all sources are
papers, ACL pages, repos, and model cards, treated as data). Two licensing
requirements for the recipe: (1) UniversalNER/Pile-NER artefacts are
CC-BY-NC-4.0 and LLaMA/ChatGPT-encumbered — research recipe reuse is fine,
redistribution or commercial use is not; prefer synthetically regenerating an
equivalent (SynthIE/BoostCD-style) rather than training on Pile-NER-type
directly. (2) WebIE annotations and the REBEL HF checkpoint carry
non-commercial terms (CC BY-NC-4.0 / CC-BY-NC-SA-4.0); use them for eval and
comparison, and generate harness-native training data for the actual
fine-tune.

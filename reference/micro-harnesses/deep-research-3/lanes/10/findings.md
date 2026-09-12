# Lane 10 findings: Generative retrieval and retrieval-generation co-training

Scope: DSI, NCI, generative-retrieval surveys, RAG end-to-end training (RETRO, Atlas,
RA-DIT), Self-RAG reflection tokens, retrieval-aware generation objectives, and evidence
about co-training retrieval and generation in one model below 3B. Screened 35, admitted 33.
All admitted PDFs are filed under `papers/` and start with `%PDF`.

## (a) Admitted items (ranked for MelodyScribe relevance)

1. **CorpusLM (2402.01176).** One model unifies generative retrieval, closed-book
generation and RAG in a single greedy DocIDs-References-Answer decode, with
ranking-oriented DocID-list training plus DocID-understanding auxiliaries (SIGIR 2024).
Take: this is the closest published architecture to MelodyScribe — one forward process
emitting both retrieval identifiers and the grounded answer — and its lesson is to train
on ranked *lists* of identifiers, not single query-docid pairs, plus auxiliaries that teach
DocID semantics. Careful: backbone and scale details were not re-verified here; treat it
as an architectural template, and note its DocIDs are corpus identifiers, not our
section/op grammar.

2. **RA-DIT (2310.01352).** Lightweight dual instruction tuning that retrofits any LLM
(7B/13B/65B tested): retrieval-augmented instruction tuning for the LM plus
LM-supervised retriever tuning, matching expensive pre-training approaches such as Atlas
and beating RePlug-style post-hoc fusion (ICLR 2024). Take: the strongest evidence that
no retrieval-specific pre-training is needed — fine-tune both sides lightly, with the LM
supervising the retriever. Careful: smallest tested LM is 7B, above our 2B; the
preservation result (parametric knowledge intact on 7/8 control tasks) must be re-tested
at 2B with our op-emission metric, not just QA accuracy.

3. **Self-RAG (2310.11511).** A single LM trained to emit retrieval/critique reflection
tokens, retrieving on demand and beam-searching segments against its own critique;
7B/13B beat ChatGPT and retrieval-augmented Llama2-chat on QA, reasoning, fact
verification and citation accuracy (ICLR 2024). Take: special control tokens emitted by
the *same* weights can govern retrieve-vs-generate decisions and self-critique — the
direct precedent for MelodyScribe's `[EMB]` marker plus Proof-checked op stream.
Careful: trained on 150k GPT-4-distilled instruction pairs with a frozen Contriever;
reflection-token reliability at 2B is unproven, and the critic/generator share could
reproduce our spike-006 collapse (retrieval training killing generation).

4. **RankRAG (2407.02485).** One instruction-tuned LLM does both context ranking and
answer generation; adding a small fraction of ranking data beats expert rankers and lifts
nine RAG benchmarks at 8B and 70B (NeurIPS 2024). Take: the cleanest proof that ranking
(retrieval-side) and generation co-train in one model with surprisingly little ranking
data — calibrate our joint loss toward a small contrastive fraction. Careful: 8B scale;
the "small fraction" ratio needs re-tuning at 2B where capacity is the binding constraint.

5. **Generative Retrieval as Dense Retrieval (2306.11397).** Analytic result that
DSI/NCI-style generative retrieval decomposes into query-document dot products, i.e. a
bi-encoder. Take: embedding training and generative-retrieval training optimize the same
object in different parameterization — this is the theoretical license for our joint
contrastive-plus-emission loss, and predicts interference comes from capacity/gradient
conflict, not objective incompatibility. Careful: it is an analysis of DSI/NCI
architectures, not of decoder-state embeddings at an `[EMB]` marker; the mapping to our
setup is suggestive, not proven.

6. **MiniRAG (2501.06713).** Heterogeneous chunk-entity graph plus lightweight topology
retrieval lets 1.5B-4B SLMs (including MiniCPM3-4B and Qwen2.5-3B) match LLM-based RAG at
25% storage; code and the LiHua-World benchmark are released MIT
(HKUDS/MiniRAG, 2014 stars). Take: the only system proving small-model RAG with a
MiniCPM-class generator — and its trick is architectural: delegate hard semantics to the
graph and give the SLM the easy subtask (entity extraction). For us: keep per-section
work decomposable so the 2B does easy extractions, hard composition left to structure.
Careful: it does not jointly train embedding and generation in one weights set; it is a
harness-design reference, not a training recipe.

7. **RAFT (2403.10131).** Domain fine-tuning on oracle-plus-distractor documents with
verbatim citation and chain-of-thought answers; large gains (up to ~35% on HotpotQA) and
distractor robustness (COLM 2024; code in ShishirPatil/gorilla). Take: training with
distractors plus a *verbatim-copy* requirement is the closest published analogue of
Proof-checked evidence-quote training — adopt the P%-with-oracle / (1-P)%-without-oracle
mixture and the cite-verbatim response format. Careful: base model is Llama2-7B and
evaluation is answer accuracy, not quote-exactness under a validator; our Proof-pass
metric is stricter.

8. **How Does Generative Retrieval Scale (2305.11841).** At MS MARCO 8.8M passages, only
synthetic-query document representations matter; PAWA/2D-IDs/consistency modifications
add nothing net of parameters, and naive parameter scaling can *hurt* (EMNLP 2023).
Take: independent confirmation of spike 003 (scale alone does not buy accuracy) and a
data prescription: budget goes to synthetic query-docid pairs, not architecture or size.
Careful: T5 encoder-decoder GR setup; the "scaling hurts" mechanism (docid-space
over-parameterization) may differ in our decoder-only + `[EMB]` setup.

9. **DSI (2202.06991).** The founding result: one Transformer maps queries to docids with
joint indexing-plus-retrieval training; semantic-string docids win; T5-Base (250M) often
beats larger variants per corpus slice (NeurIPS 2022). Take: joint training works from
250M up, and docid *design* (semantic strings) dominates scale — our section/op
identifiers should carry semantics, not atomic ids. Careful: no embedding objective and
no generation beyond docids; catastrophic-update behavior (new documents) is its known
weakness (see IncDSI, CorpusBrain++).

10. **NCI (2206.02743).** Seq2seq retriever with prefix-aware weight-adaptive decoder,
hierarchical-k-means semantic docids, query-generation augmentation and consistency
regularization; +21.4% Recall@1 on NQ320k over best baselines (NeurIPS 2022). Take: three
transferable techniques — QG augmentation (data), consistency regularization (stability),
position-aware decoding (identifier structure). Careful: the PAWA decoder's value
vanishes net of parameters at scale (per lane item 8); prefer its data/regularization
lessons over its architecture.

11. **SEAL (2204.10628).** Generates corpus-grounded n-gram identifiers under FM-index
constrained decoding; documents scored by aggregating identifier scores (code:
facebookresearch/SEAL). Take: the precedent for *constrained* generation as retrieval —
every emitted token provably occurs in the corpus — which is exactly the property our
grammar + Proof validator must enforce for verbatim quotes. Careful: FM-index
constraints at 2B-scale decoding add latency/complexity; treat as the inference-time
complement to RAFT-style training-time grounding.

12. **GENRE (2010.00904).** Autoregressive entity retrieval by generating names with
constrained beam search; memory scales with vocabulary, not entity count (ICLR 2021;
code: facebookresearch/GENRE, 801 stars). Take: generating *names* of things (entities,
and by analogy our graph-triple subjects/objects) beats classifying over them, with
tractable memory — relevant to emitting triples from a 2B model. Careful: entity names
are natural-language identifiers; our SQL facts and op syntax are less forgiving of
near-miss generation.

13. **REALM (2002.08909).** First unsupervised joint pre-training of retriever and LM via
backprop through MIPS over millions of documents with asynchronous index refresh (ICML
2020; code in google-research/language). Take: the canonical pattern for joint training
— stale-index refresh schedules and top-k marginalization — still the template for any
end-to-end run we attempt. Careful: BERT-scale masked-LM setting; refresh machinery is
heavy for one 16 GB GPU (prefer RA-DIT-style fine-tuning over REALM-style pre-training).

14. **RAG (2005.11401).** RAG-Sequence/Token joint fine-tuning of DPR retriever + BART
generator with documents as latents; hot-swappable index (NeurIPS 2020). Take: the base
joint fine-tuning recipe and the modularity lesson — keep the document store swappable
so corpus updates do not require retraining (cf. IncDSI). Careful: retriever initialized
from supervised DPR; cold-start joint training from our contrastive adapter is a harder
regime than RAG's warm start.

15. **FiD (2007.01282).** Fusion-in-Decoder fuses up to ~100 passages in the decoder with
monotone gains (EACL 2021; code: facebookresearch/FiD). Take: the generator side wants
*many* fused evidence spans — our retrieval payload assembly for the frontier consumer
should err toward recall, and FiD-style decoder fusion is the reader architecture to
match. Careful: encoder cost grows linearly in passages; at 2B the fusion budget
competes directly with embedding capacity.

16. **RETRO (2112.04426).** Frozen BERT retriever + chunked cross-attention matches
GPT-3-scale performance with 25x fewer parameters; any transformer can be RETROfitted by
training only retrieval pathways (ICML 2022). Take: the strongest alternative to joint
training — freeze retrieval, train only the interface — which bounds spike 011's
adapter-toggle arm: if joint training collapses, a frozen-embedder + trained-generator
split is a published-viable fallback. Careful: chunk-level retrieval granularity fits
language modeling, not necessarily section-level structured ops.

17. **Atlas (2208.03299).** Contriever + FiD jointly pre-trained with index refresh and
query-side fine-tuning ablations; 64-shot NQ beats a 540B model (JMLR 2023; code:
facebookresearch/atlas). Take: the fine-tuning-strategy ablations (full vs query-side,
retriever loss choices) are the closest published guide to scheduling our joint run.
Careful: 11B scale with full pre-training budget; our regime is fine-tuning a 2B on one
GPU — downscale the recipe, keep the ablations.

18. **REPLUG (2301.12652).** Black-box LM plus LM-supervised tunable retriever (LSR);
+6.3% GPT-3 likelihood, +5.1% Codex MMLU (NAACL 2024). Take: supervision can flow
*from* the generator *to* the retriever with the LM frozen — the mirror image of our
collapse (where retrieval training killed generation), suggesting an alternating or
generator-anchored schedule. Careful: official repo URL from the paper 404s on the
GitHub API as of 2026-09-12, so no code artefact could be verified; use the paper, not
the repo.

19. **In-Context RALM (2302.00083).** No-training prepend-retrieval baseline worth 2-3x
parameters down to 110M models, plus retriever re-ranking for the RALM objective (TACL
2023). Take: every spike-011 arm must beat this free baseline, and its small-model
results (110M+) are the only sub-3B retrieval-generation co-evidence in the lane that
required no training at all. Careful: it is a baseline, not a recipe; it says nothing
about preserving constrained generation.

20. **FLARE (2305.06983).** Confidence-gated forward-looking retrieval over long-form
generation (EMNLP 2023; code: jzbjyb/FLARE, MIT, 668 stars). Take: the retrieval *policy*
pattern — draft, check confidence, retrieve, regenerate — applicable to per-section
decisions and to the frontier-consumer payload loop. Careful: needs calibrated
token-confidence from the small model, which our 2B may not provide out of the box.

21. **CorpusBrain (2208.07652).** Generative-retrieval pre-training tasks
(inner-sentence/lead-paragraph/hyperlink-identifier prediction) then single-step
generative fine-tuning per KILT task (CIKM 2022; code: ict-bigdatalab/CorpusBrain,
Apache-2.0). Take: identifier-prediction pre-training tasks are a template for warming
the 2B toward section/op identifiers before joint training. Careful: its forgetting
behavior (see next item) warns that this pre-training is exactly what later collapses
under corpus shift.

22. **CorpusBrain++ (2402.16767).** Pre-trained CorpusBrain catastrophically forgets on
the continual KILT++ benchmark; rehearsal-plus-regularization continual pre-training
restores it. Take: the only direct measurement of catastrophic forgetting in a
generative-retrieval model — cite it for spike 011's KL-anchor and replay arms.
Careful: forgetting measured across corpus *updates*, not across embedding-vs-generation
task conflict; the transfer to our interference question is analogical.

23. **DSI-QG (2206.10128).** Fixes DSI's index/retrieve distribution mismatch by indexing
cross-encoder-filtered generated queries rather than document text (Gen-IR @ SIGIR 2023;
code: ArvinZhuang/DSI-QG, MIT, 129 stars). Take: our sections are long and our queries
short — the same mismatch — so index-side synthetic queries (or query-side bare
documents per spike 007) deserve a dedicated spike-011 data arm. Careful: adds a QG
model and cross-encoder filter to the data pipeline; cost must be weighed against simply
using bare sections.

24. **IncDSI (2307.10323).** New documents indexed in 20-50 ms via constrained
optimization over the added docid vector only, matching full-retrain quality (ICML 2023;
code: varshakishore/IncDSI, MIT). Take: parametric indexes *can* grow without
retraining — relevant to adding corpus sections after the joint fine-tune. Careful:
atomic-docid classifier setting; extension to semantic identifiers and to a model that
also generates structured ops is unproven.

25. **Ultron (2208.09257).** Semantic URL/title docids with three-stage
(general/search-oriented/supervised) training; beats DSI-style baselines on MS MARCO and
NQ. Take: a second independent staged-training recipe corroborating NCI/CorpusBrain that
general pre-training must precede retrieval-oriented training. Careful: repo evidence is
second-hand (smallporridge/WebUltron README cites it as its official repo while hosting
a follow-up); stage details come from the paper, not from run code.

26. **RIPOR (2311.09134).** Prefix-oriented ranking optimization plus multi-stage
distillation; first GR trained effectively on large standard benchmarks. Take:
ranking-aware sequence loss design — prefix-level credit assignment — directly informs
the joint contrastive-plus-emission loss (penalize early identifier-token errors more).
Careful: encoder-decoder GR setting; distillation stages assume a teacher retriever we
may not have.

27. **InstructRetro (2310.07713).** Continued retrieval-augmented pre-training (43B GPT,
100B tokens over 1.2T-token store) then instruction tuning; the Retro encoder ablates
away with no loss, and the 8B instruct checkpoint is released
(huggingface.co/nvidia/retro-8b-instruct-4k) (ICML 2024). Take: two transferable facts —
retrieval pre-training distills into the decoder weights (relevant to our single-weights
thesis), and an 8B retrieval-trained checkpoint exists that fits 16 GB for probing.
Careful: 100B-token continued pre-training is far outside our budget; use the checkpoint
as an analysis artefact, not a recipe to repeat.

28. **GAR (2009.08553).** Reverse direction: BART-generated query expansions plus BM25
match or beat DPR; fusing diverse generations helps (ACL-IJCNLP 2021). Take: the cheap
one-GPU recipe — generator expands, sparse index retrieves — is a viable fallback if
dense/parametric retrieval will not fit alongside generation in 2B weights. Careful:
English QA setting with heuristic contexts; structured-op emission is a stricter
consumer than BM25.

29. **DPR (2004.04906).** Dual-encoder with one BM25 hard negative plus in-batch
negatives; +9-19 top-20 points over BM25 (EMNLP 2020; code: facebookresearch/DPR, 1871
stars). Take: the negative-sampling and batch-composition recipe underlying every dense
side in this lane, including RAG's initializer. Careful: supervised pairs required;
pair with Contriever when labels are scarce.

30. **Contriever (2112.09118).** MoCo-style unsupervised contrastive retriever,
competitive with BM25, and the standard Atlas/Self-RAG starting point (TMLR 2022; code:
facebookresearch/contriever, 779 stars). Take: the no-label retriever recipe for cold
sections of our corpus. Careful: BEIR-generalist behavior differs from narrow-corpus
behavior; our spike-004 contrastive recipe already beats it in-domain after 147 s.

31. **GenIR survey Kuo (2406.01197).** DocID taxonomy (single-token, sequential,
text-based) and indexing-vs-retrieval training survey with learnable-DocID and
multi-task futures. Take: use the taxonomy to choose MelodyScribe section/op identifier
form; the multi-task-GR future direction is our problem statement. Careful: survey,
no new experiments; 2024 cutoff misses RIPOR-scale follow-ups (covered separately).

32. **GenIR survey Li (2404.14851).** Two-branch survey covering generative document
retrieval *and* reliable response generation with incremental-learning and evaluation
sections (TOIS 2025; collection: RUC-NLPIR/GenIR-Survey, MIT, 210 stars). Take: the only
survey spanning both halves of our problem, with entry points on dynamic corpora and
attribution. Careful: survey-level claims only; verify anything load-bearing in the
cited primary.

33. **RAG survey Gao (2312.10997).** Naive/Advanced/Modular RAG taxonomy with
pre/post-retrieval and evaluation frameworks. Take: reference vocabulary for the
payload-assembly half (Q6) and for evaluation design. Careful: LLM-era survey pitched at
large models; small-model and joint-training coverage is thin (which is this lane's
raison d'etre).

## (b) Refutations of claims in the brief

- *"Scale alone buys retrieval-generation quality."* Contradicted by Pradeep et al.
(2305.11841): at 8.8M passages, architecture modifications add nothing net of parameters
and naive parameter scaling can be detrimental — agreeing with spike 003 (flat 0.30-0.45
routing, 2B-8B) rather than contradicting it. The claim as a hope is refuted; spike 003
stands.
- *"Co-training retrieval and generation needs expensive retrieval-specific
pre-training."* Contradicted by RA-DIT (2310.01352: lightweight dual instruction tuning
matches Atlas-class pre-training), REPLUG (2301.12652: no LM training at all) and
In-Context RALM (2302.00083: no training, 2-3x param-equivalent gains). Joint training
is sufficient, not necessary, at each budget point.
- *"Generative retrieval obsoletes dense retrieval."* Contradicted from both sides:
Nguyen & Yates (2306.11397) show GR decomposes into bi-encoder dot products, and Pradeep
et al. show GR competitive only on small corpora with web-scale unsolved. Parametric and
dense retrieval are the same object in different clothes; keep both, and keep the dense
index swappable (RAG hot-swap, IncDSI real-time update).
- *"One model cannot rank and generate."* Contradicted by RankRAG (2407.02485): one
8B model with a small ranking-data fraction beats expert rankers and generates. The open
question is only the ratio at 2B, not the possibility.

## (c) Unresolved ledger

- DynamicRetriever (2203.00537): identified from a PDF search-result excerpt only; abs
page never opened, venue unconfirmed — abstained. Same-group successor Ultron admitted.
- Distilling Knowledge from Reader to Retriever (Izacard & Grave, ICLR 2021): no arXiv
id (OpenReview primary), so no PDF could be filed under lane rules — abstained; content
covered via Atlas and REPLUG-LSR.
- Repo resolution failures: swj0419/REPLUG (paper-claimed URL 404s on GitHub API),
RankRAG official repo (NVlabs/RankRAG 404; nvidia/RankRAG 404), Self-RAG org repo
(selfrag/self-rag 404; selfrag/selfrag 404; allenai/self-rag 404). Recorded as
unverified rather than invented; Self-RAG artefacts live behind the verified project
page https://selfrag.github.io (not re-verified).
- CorpusLM, GR-as-Dense, RIPOR, CorpusBrain++, Ultron-stage-details, RAG/FiD replication
code: no verified repo URL found in fetched sources; repo_url left blank rather than
guessed.
-arXiv export API (`export.arxiv.org/api/query`) returned `Rate exceeded` on first use;
Semantic Scholar API returned HTTP 429 throughout. All discovery therefore ran through
fetched arXiv abs/HTML pages, fetched GitHub pages/API, fetched Hugging Face pages, and
web-search excerpts of primary pages. Forward/backward citation chaining via the S2
citation graph was impossible under rate limits; chaining was done manually through
reference lists in fetched PDFs/pages (DSI <- NCI <- Ultron <- CorpusBrain <-
CorpusBrain++; REALM -> RAG -> FiD -> Atlas -> RA-DIT; RAG -> REPLUG -> RA-DIT;
Self-RAG -> FLARE/active-retrieval follow-ups).
- Sub-3B co-training evidence remains the gap: the smallest joint models in this lane
are In-Context RALM's 110M-66B no-training baselines and MiniRAG's 1.5B-4B
harness-level (not weights-level) results. No admitted paper co-trains embedding and
constrained generation in one 1B-3B weights set — that measurement is spike 011's to make.

## (d) Security findings

No lane-10 paper introduces a new attack surface for MelodyScribe beyond the already
known one: any retrieval-conditioned generator can be steered by poisoned corpus content
(REALM/RAG/Atlas all condition answers on retrieved text; Self-RAG's relevance critique
only partially mitigates it). Requirement: treat all corpus sections as untrusted input
to the generator during joint training — keep Proof validation of quotes and op syntax
as a hard gate (never a training-time-only check), and log retriever provenance per
emitted op so a poisoned section is attributable. No prompt-injection payload was
executed: every fetched page was treated as data per the brief.

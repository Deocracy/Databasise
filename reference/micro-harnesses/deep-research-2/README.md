# MelodyScribe deep research 2: embedding models, prompts, serving, pipeline (Muse Spark 1.3 lanes, 2026-09-12)

Ten research lanes run as separate `opencode-go/muse-spark-1.3-contributor` sessions through OpenCode (`run-lanes.sh`, two to four at a time, each in its lane folder with `BRIEF.md` attached and `LANE-PROMPT.md` plus its `lane.txt` as the prompt; a lane that stops early is nudged on its captured session id with `NUDGE.md`). A machine reboot cut lanes 1 to 4 during their first run; the runner resumed them on their session ids. A deterministic merge (`integrate.py`) deduplicated the ten inventories and staged PDFs; a final Muse Spark session (`INTEGRATOR-PROMPT.md`) wrote `REPORT.md` from the ten `findings.md` files and the merged inventory. Claude did not write any finding; it ran the lanes, merged, verified, and filed.

| File | What |
|---|---|
| `REPORT.md` | The ten-part report: verdicts on the six questions in the brief, top twenty, refutations, per-lane findings, the recipe (embedder on one 16 GB GPU; graph-extraction prompt and training; serving configuration), reusable artefacts, gaps, reading order, full inventory, method |
| `merged/SUMMARY.md` | Merge counts, admitted list by relevance, refutations, unresolved ledger |
| `merged/INVENTORY.tsv` | Every screened candidate, deduplicated across lanes, 16 columns plus `lanes` |
| `lanes/<n>/` | Each lane's `lane.txt`, `findings.md`, `inventory.tsv`, `method.md` |
| `merged/papers/`, `lanes/<n>/papers/` | Admitted PDFs, header-checked. On disk, not committed (root `.gitignore`); each is `<arxiv-id>_<title>.pdf` and re-downloadable from `https://arxiv.org/pdf/<id>` using the ids in `merged/INVENTORY.tsv` |

Counts: 287 rows screened across lanes, 191 unique, 153 admitted, 0 refuted, 38 unresolved; 150 PDFs staged.

| Lane | Subject | Screened | Admitted |
|---|---|---|---|
| 1 | Embedding model architectures. | 24 | 16 |
| 2 | Training recipes for embedders. | 29 | 20 |
| 3 | Small embedders and distillation into them. | 21 | 15 |
| 4 | Hybrid models: one small model that embeds and generates. | 33 | 28 |
| 5 | Prompts and instructions for embeddings. | 25 | 18 |
| 6 | Evaluating "best" and fixing anisotropy. | 32 | 22 |
| 7 | Prompting small models for knowledge-graph extraction. | 25 | 24 |
| 8 | Batched serving and KV sharing on one GPU. | 39 | 35 |
| 9 | Pipeline orchestration for extraction at scale. | 22 | 16 |
| 10 | High-speed retrieval and vector storage. | 37 | 23 |

Verification performed after the run: every lane inventory has exactly 16 columns; all 150 staged PDFs start with `%PDF`; all 179 arXiv ids cited in report parts 1 to 8 appear in the merged inventory or the brief.

Known limits: the same search constraints as round 1 (arXiv API and abs pages, Semantic Scholar, GitHub API; no search engine). Serving-throughput multiples in the report are datacenter-GPU figures and are flagged as such; the report names spikes 006 to 010 as the primary evidence for every number that the literature does not report at 0.3B to 2B scale on a 16 GB card.

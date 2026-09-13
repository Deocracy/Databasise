# MelodyScribe deep research 4: what the harness should look like (Muse Spark 1.3 lanes, 2026-09-13)

Ten research lanes run as separate `opencode-go/muse-spark-1.3-contributor` sessions through OpenCode (`run-lanes.sh`, four at a time, each in its lane folder with `BRIEF.md` attached and `LANE-PROMPT.md` plus its `lane.txt` as the prompt; a lane that stops early is nudged on its captured session id with `NUDGE.md`). A deterministic merge (`integrate.py`) deduplicated the ten inventories and staged PDFs. No Muse integrator ran this round: the owner's main session (Claude) assembled `REPORT.md` from the ten `findings.md` files and wrote the design note `.planning/notes/melodyscribe-harness-frameworks.md`. Claude wrote no finding; it ran the lanes, merged, read, assembled, and filed.

| File | What |
|---|---|
| `REPORT.md` | Verdict per lane question, 23 refutations of claims in or behind the brief, consolidated security requirements, cross-lane unresolved ledger, method and counts |
| `../../../.planning/notes/melodyscribe-harness-frameworks.md` | The design: requirements, seven research-forced corrections, three whole-system shapes and eight layers, the pre-alpha composite, the requirement matrix, contract updates, what the harness tells the fine-tune |
| `merged/SUMMARY.md`, `merged/INVENTORY.tsv` | Merge counts; every screened candidate deduplicated across lanes, 16 columns plus `lanes` |
| `lanes/<n>/` | Each lane's `lane.txt`, `findings.md` (ending with a "Harness implications" section), `inventory.tsv`, `method.md` |
| `merged/papers/`, `lanes/<n>/papers/` | Admitted PDFs, header-checked. On disk, not committed (root `.gitignore`); re-downloadable from `https://arxiv.org/pdf/<id>` using the ids in `merged/INVENTORY.tsv` |

Counts: 461 rows screened, 348 unique, 173 admitted, 1 refute row, 174 abstain (about 100 are lane 9's declared title-screen-only rows), 162 PDFs staged.

| Lane | Subject | Screened | Admitted |
|---|---|---|---|
| 1 | Micro-harness architectures for small models | 41 | 30 |
| 2 | Ingest-side routing to typed stores | 44 | 27 |
| 3 | Recall-side harnesses | 28 | 24 |
| 4 | Thinking modes for small models | 38 | 27 |
| 5 | Real-time co-processor next to a frontier model | 36 | 26 |
| 6 | Caching and parallel workload | 39 | 27 |
| 7 | Code graphs as a store | 23 | 18 |
| 8 | Learning graphs and procedural memory | 30 | 21 |
| 9 | Structured facts store | 144 | 26 |
| 10 | Evaluating harnesses and harness signals as rewards | 38 | 19 |

Known limits: the same search constraints as rounds 1 to 3 (arXiv API and abs pages, Semantic Scholar, GitHub API; no search engine), with Semantic Scholar rate-limited for lanes 1 and 9. The central gaps are that no admitted paper measures a 1B to 3B model routing across typed stores or gating its own retrieval, and no source reports capacity under a latency SLO for one model process serving embedding and generation on one 16 GB card.

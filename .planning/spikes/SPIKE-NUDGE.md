You stopped before the spike was complete. Nothing counts until it is on disk in your spike folder. Continue the same spike now, without asking questions.

Required before you stop again:
1. `README.md` with frontmatter `verdict:` set to VALIDATED, INVALIDATED, or PARTIAL (never PENDING), and Research, How to Run, What to Expect, Investigation Trail, and Results sections; every number traces to a line in `logs/`.
2. `run.sh` that reproduces everything from scratch, every model load under `flock /tmp/melodyscribe-gpu.lock`, one model per process.
3. If a step keeps failing, record the failure with its log line as evidence, pick the smallest change that unblocks it, note the change as a deviation in the README, and continue. A PARTIAL verdict with evidence beats no verdict.

Rules that still apply: never read or print secret files (source `v1/.env.parity` at runtime with `set -a; source v1/.env.parity; set +a` if the spike needs the teacher endpoint); never edit another spike's folder; follow `.planning/spikes/CONVENTIONS.md`. If an earlier retry of this spike needed a specific fix, it is in `SPIKE-NUDGE-NNN.md` next to this file.

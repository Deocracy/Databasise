"""Training-free controls on the untrained 2B marker state (CPU, numpy).

Usage: controls.py <run_name>
Reads results/vecs_E_<run>.json (untrained MiniCPM5-2B) and
results/bias_<run>.json, writes three transformed vecs files in the same
schema (identical doc/query order, so eval_recall.py scores them as arms):

- Cmean:   subtract the 20-doc mean, renormalize (all-but-the-top-1 slice).
- Cwhiten: PCA-whiten fit on 20 docs + 86 train queries (centered by the
           fit mean, eigenvalue floor at 1% of max), renormalize.
- Cbias:   subtract the marker-only bias probe mean, renormalize
           (marker-only template bias, PromptBERT pattern).

Pre-registered rule: if any control reaches within 0.05 test MRR of the
0.6B embedder, the training arms stop early and the control is the
recommendation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_eval import RESULTS, emit  # noqa: E402


def load_vecs(run_name):
    v = json.loads((RESULTS / f"vecs_E_{run_name}.json").read_text())
    b = json.loads((RESULTS / f"bias_{run_name}.json").read_text())
    return v, b


def write_arm(base, label, doc_vecs, query_vecs, gold_vecs, run_name, note):
    import numpy as np

    def normed(v):
        v = np.asarray(v, dtype=np.float64)
        return (v / np.linalg.norm(v)).tolist()

    out = dict(base)
    out["arm"] = label
    out["model"] = base["model"] + f"+{note}"
    out["doc_vecs"] = [normed(v) for v in doc_vecs]
    out["query_vecs"] = [normed(v) for v in query_vecs]
    out["gold_vecs"] = [normed(v) for v in gold_vecs]
    out["ms_per_doc"] = 0.0
    out["ms_per_query"] = 0.0
    (RESULTS / f"vecs_{label}_{run_name}.json").write_text(json.dumps(out) + "\n")
    emit(run_name, "control_scored", arm=label)


def main() -> None:
    import numpy as np

    run_name = sys.argv[1]
    base, bias = load_vecs(run_name)
    D = np.asarray(base["doc_vecs"], dtype=np.float64)
    Q = np.asarray(base["query_vecs"], dtype=np.float64)
    G = np.asarray(base["gold_vecs"], dtype=np.float64)
    is_train = np.asarray([s == "train" for s in base["query_split"]])

    # Cmean: subtract the 20-doc mean.
    mu = D.mean(axis=0)
    write_arm(base, "Cmean", D - mu, Q - mu, G - mu, run_name, "mean-centered")

    # Cwhiten: PCA-whiten fit on docs + train queries.
    fit = np.vstack([D, Q[is_train]])
    fmu = fit.mean(axis=0)
    C = np.cov((fit - fmu).T)
    vals, vecs = np.linalg.eigh(C)
    floor = 0.01 * vals.max()
    inv = vecs @ np.diag(1.0 / np.sqrt(np.maximum(vals, floor))) @ vecs.T
    write_arm(base, "Cwhiten", (D - fmu) @ inv.T, (Q - fmu) @ inv.T,
              (G - fmu) @ inv.T, run_name, "pca-whitened")
    emit(run_name, "whiten_fit", n_fit=int(fit.shape[0]),
         eig_max=float(vals.max()), eig_min=float(vals.min()))

    # Cbias: subtract the averaged marker-only probe.
    b = np.asarray(bias["vecs"], dtype=np.float64).mean(axis=0)
    write_arm(base, "Cbias", D - b, Q - b, G - b, run_name, "bias-subtracted")

    print("controls written: Cmean Cwhiten Cbias", flush=True)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env bash
# Spike 007: embedding-prompt-sensitivity. Reproduces everything from scratch.
# GPU loads run under the lock; build/eval run without it. One model per process.
set -u
cd "$(dirname "$0")"
source ../env.sh
D=.
mkdir -p inputs results logs

echo "== build inputs =="
$MELODYSCRIBE_PY $D/build_inputs.py build

A=Qwen3-Embedding-0.6B-Q8_0.gguf
B=MiniCPM5-2B-Q8_0.gguf
LOCK="flock /tmp/melodyscribe-gpu.lock"

echo "== embedder: 3 reps =="
for r in 1 2 3; do
  $LOCK $MELODYSCRIBE_PY $D/embed_run.py emb_rep$r $A native inputs/emb_texts.json results/vecs_emb_rep$r.json
done

echo "== generative 2B: 3 reps =="
for r in 1 2 3; do
  $LOCK $MELODYSCRIBE_PY $D/embed_run.py gen_rep$r $B last inputs/gen_texts.json results/vecs_gen_rep$r.json
done

echo "== evaluate rep1 (+ determinism rep1 vs rep2) =="
$MELODYSCRIBE_PY $D/evaluate.py head2head results/vecs_emb_rep1.json results/vecs_gen_rep1.json \
  --det results/vecs_emb_rep2.json results/vecs_gen_rep2.json

echo "== timing summary =="
$MELODYSCRIBE_PY -c "
import json, glob
for run in ['emb_rep1','emb_rep2','emb_rep3','gen_rep1','gen_rep2','gen_rep3']:
    for line in open(f'logs/{run}.jsonl'):
        r = json.loads(line)
        if r['event'] == 'embedded':
            print(run, 'n=%d' % r['n'], 'per_text_ms=%.2f' % r['per_text_ms'])
"

echo "== done =="

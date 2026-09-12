#!/usr/bin/env bash
# Spike 004: self-embedding-parity. Reproduces everything from scratch.
# GPU loads run under the lock; training/eval/analysis run without it.
set -u
cd "$(dirname "$0")"
source ../env.sh
D=.
mkdir -p inputs results logs

echo "== build inputs =="
$MELODYSCRIBE_PY $D/eval_common.py --build

echo "== query/chunk input lists =="
python3 -c "
import json
from pathlib import Path
p = Path('inputs')
gold = json.load(open(p/'queries_gold.json'))
selfq = json.load(open(p/'queries_self.json'))
chunks = json.load(open(p/'chunks.json'))
q = {'ids': [x['id'] for x in gold] + ['self:'+x['id'] for x in selfq],
     'texts': [x['question'] for x in gold] + [x['question'] for x in selfq]}
json.dump(q, open(p/'queries_all.json','w'), ensure_ascii=False)
json.dump({'ids':[c['id'] for c in chunks],'texts':[c['text'] for c in chunks]},
          open(p/'chunks_in.json','w'), ensure_ascii=False)
print(len(q['ids']), 'queries,', len(chunks), 'chunks')
"

A=Qwen3-Embedding-0.6B-Q8_0.gguf
B=MiniCPM5-2B-Q8_0.gguf
B2=Qwen3-1.7B-Q8_0.gguf
LOCK="flock /tmp/melodyscribe-gpu.lock"

echo "== arm A (dedicated embedder) =="
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armA_docs $A native "" none inputs/docs.json results/armA_docs.json
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armA_q $A native "" none inputs/queries_all.json results/armA_q.json
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armA_ch $A native "" none inputs/chunks_in.json results/armA_chunks.json

echo "== arm B (MiniCPM5-2B untrained last-token + marker) =="
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armB_docs $B last "" emb inputs/docs.json results/armB_docs.json
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armB_q $B last "" emb inputs/queries_all.json results/armB_q.json
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armB_ch $B last "" emb inputs/chunks_in.json results/armB_chunks.json

echo "== arm B2 (Qwen3-1.7B untrained last-token + marker) =="
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armB2_docs $B2 last "" emb inputs/docs.json results/armB2_docs.json
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armB2_q $B2 last "" emb inputs/queries_all.json results/armB2_q.json
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armB2_ch $B2 last "" emb inputs/chunks_in.json results/armB2_chunks.json

echo "== arm Bplain (MiniCPM5-2B, no marker) =="
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armBplain_docs $B last "" none inputs/docs.json results/armBplain_docs.json
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armBplain_q $B last "" none inputs/queries_all.json results/armBplain_q.json
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armBplain_ch $B last "" none inputs/chunks_in.json results/armBplain_chunks.json

echo "== determinism re-run (arm A docs) =="
$LOCK $MELODYSCRIBE_PY $D/arm_embed.py armA_redo $A native "" none inputs/docs.json results/armA_redo_docs.json

echo "== head-to-head eval (CPU) =="
$MELODYSCRIBE_PY $D/evaluate.py head2head armA,armB,armB2
$MELODYSCRIBE_PY $D/evaluate.py ablation1 armB,armBplain
$MELODYSCRIBE_PY $D/diagnose.py diag1
$MELODYSCRIBE_PY $D/controls.py ctrl1

echo "== trained heads (CPU) =="
$MELODYSCRIBE_PY $D/train_head.py headB_lam1 armB armA --lam 1
$MELODYSCRIBE_PY $D/evaluate.py headBeval_lam1 armB --head results/headB_lam1_head.json
$MELODYSCRIBE_PY $D/train_head.py headBplain_lam1 armBplain armA --lam 1
$MELODYSCRIBE_PY $D/evaluate.py headBplainEval armBplain --head results/headBplain_lam1_head.json

echo "== edge cases (GPU, one model per process) =="
$LOCK $MELODYSCRIBE_PY $D/edge.py edge3 part1 A
$LOCK $MELODYSCRIBE_PY $D/edge.py edgeB part1 B || true   # empty-B hard-errors (llama_decode -1); expected, see README
$LOCK $MELODYSCRIBE_PY $D/edgeB.py edge4                  # trunc + escape on a fresh B process
$LOCK $MELODYSCRIBE_PY $D/edge.py edge2 part2

echo "== done =="

#!/usr/bin/env bash
# MelodyScribe sources: shallow-clone code into <name>/code (git-ignored) and fetch papers as PDFs.
# Re-runnable. Writes manifest.tsv (name, kind, url-or-arxiv-id, commit-or-title, date).
# Line format below: name|git repo url or -|comma-separated arXiv ids or -
# name "_" means a paper with no code: it lands in this folder, not a subfolder.
set -u
cd "$(dirname "$0")"
TODAY=$(date -I)
: > manifest.tsv
clone_one() {  # name url
  local name=$1 url=$2 dir="$1/code"
  mkdir -p "$1"
  if [ -d "$dir/.git" ]; then git -C "$dir" pull -q --ff-only 2>/dev/null || true
  else git clone -q --depth 1 "$url" "$dir" 2>>sync.log || { echo "CLONE FAILED $name $url" >> sync.log; return; }; fi
  printf '%s\tcode\t%s\t%s\t%s\n' "$name" "$url" "$(git -C "$dir" rev-parse --short HEAD 2>/dev/null)" "$TODAY" >> manifest.tsv
}
paper_one() {  # name arxiv_id
  local name=$1 id=$2 dest title slug existing
  dest=$( [ "$name" = "_" ] && echo "." || echo "$name" ); mkdir -p "$dest"
  # title from the abs page (the export API rate-limits hard); one retry
  for _try in 1 2; do
    title=$(curl -sL --max-time 30 "https://arxiv.org/abs/$id" | python3 -c 'import sys,re,html; t=sys.stdin.read(); m=re.search(r"<title>\s*\[[^\]]+\]\s*(.*?)</title>",t,re.S); print(html.unescape(m.group(1)).strip().replace("\n"," ") if m else "")')
    [ -n "$title" ] && break; sleep 5
  done
  slug=$(printf '%s' "$title" | sed -E 's/[^A-Za-z0-9]+/_/g; s/^_+|_+$//g' | cut -c1-70)
  [ -z "$slug" ] && slug=unknown_title
  existing=$(ls "$dest"/"${id}"_*.pdf 2>/dev/null | head -1)
  if [ -n "$existing" ] && [ "$existing" != "$dest/${id}_${slug}.pdf" ] && [ "$slug" != unknown_title ]; then mv "$existing" "$dest/${id}_${slug}.pdf"; existing="$dest/${id}_${slug}.pdf"; fi
  if [ -z "$existing" ]; then curl -sL --max-time 120 "https://arxiv.org/pdf/$id" -o "$dest/${id}_${slug}.pdf" || echo "PDF FAILED $id" >> sync.log; fi
  printf '%s\tpaper\t%s\t%s\t%s\n' "$name" "$id" "$title" "$TODAY" >> manifest.tsv
}
export -f clone_one paper_one; export TODAY
: > sync.log
grep -vE '^\s*(#|$)' <<'LIST' > .sources.list
minicpm|https://github.com/OpenBMB/MiniCPM|2506.07900,2602.09003,2509.24663
gritlm|https://github.com/ContextualAI/gritlm|2402.09906
llm2vec|https://github.com/McGill-NLP/llm2vec|2404.05961
qwen3-embedding|https://github.com/QwenLM/Qwen3-Embedding|2506.05176
llama-cpp|https://github.com/ggml-org/llama.cpp|-
prompt-cache|https://github.com/yale-sys/prompt-cache|2311.04934
cacheblend|https://github.com/LMCache/LMCache|2405.16444
mem-alpha|https://github.com/wangyu-ustc/Mem-alpha|2509.25911
a-mem|https://github.com/agiresearch/A-mem|2502.12110
memorag|https://github.com/qhjqhj00/MemoRAG|2409.05591
self-rag|https://github.com/AkariAsai/self-rag|2310.11511
dense-x-retrieval|https://github.com/chentong0/factoid-wiki|2312.06648
knn-lm|https://github.com/urvashik/knnlm|1911.00172
mirix|https://github.com/Mirix-AI/MIRIX|2507.07957
hindsight|https://github.com/vectorize-io/hindsight|2512.12818
letta|https://github.com/letta-ai/letta|2310.08560
sleep-time-compute|https://github.com/letta-ai/sleep-time-compute|2504.13171
voyager|https://github.com/MineDojo/Voyager|2305.16291
evaporate|https://github.com/HazyResearch/evaporate|2304.09433
graphiti|https://github.com/getzep/graphiti|2501.13956
cognee|https://github.com/topoteretes/cognee|-
mem0|https://github.com/mem0ai/mem0|2504.19413
memori|https://github.com/GibsonAI/memori|-
memos|https://github.com/MemTensor/MemOS|2507.03724
search-r1|https://github.com/PeterGriffinJin/Search-R1|2503.09516
_|-|2508.19828
LIST
# clones in parallel, papers sequentially (arXiv rate limits)
awk -F'|' '$2!="-"{print $1" "$2}' .sources.list | xargs -P 6 -n 2 bash -c 'clone_one "$0" "$1"'
awk -F'|' '$3!="-"{n=split($3,a,","); for(i=1;i<=n;i++) print $1" "a[i]}' .sources.list | while read -r n id; do paper_one "$n" "$id"; sleep 3; done
rm -f .sources.list
sort -o manifest.tsv manifest.tsv
echo "done: $(grep -c . manifest.tsv) manifest rows; $(wc -l < sync.log) log lines"

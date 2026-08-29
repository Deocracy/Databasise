#!/usr/bin/env bash
# Spike 004 Q7: cost of the three lifecycle operations Nix would perform
# in a branch -> A/B -> promote cycle. 256 MB synthetic index artifact.
set -u
cd "$(dirname "$0")"

ms() { echo $(( ($2 - $1) / 1000000 )); }

echo "--- Q7a: hash only, no store residency (nix hash path, nar/sha256) ---"
for i in 1 2; do
  t0=$(date +%s%N); nix hash path --mode nar --type sha256 blob.bin >/dev/null; t1=$(date +%s%N)
  echo "  run$i: $(ms "$t0" "$t1") ms"
done

echo "--- Q7b: register into store (nix store add) ---"
t0=$(date +%s%N); SPATH=$(nix store add --mode nar blob.bin); t1=$(date +%s%N)
echo "  first add: $(ms "$t0" "$t1") ms -> $SPATH"
t0=$(date +%s%N); SPATH2=$(nix store add --mode nar blob.bin); t1=$(date +%s%N)
echo "  re-add identical bytes: $(ms "$t0" "$t1") ms -> $SPATH2"
echo "  same path: $([ "$SPATH" = "$SPATH2" ] && echo yes || echo no)"

echo "--- Q7c: atomic alias repoint (symlink swap, 1000x) ---"
mkdir -p gen-a gen-b
t0=$(date +%s%N)
for i in $(seq 1 1000); do ln -sfn gen-a cur.tmp; mv -Tf cur.tmp cur; done
t1=$(date +%s%N)
echo "  1000 repoints: $(ms "$t0" "$t1") ms total"

echo "--- cleanup ---"
nix store delete "$SPATH" 2>&1 | tail -2
rm -f cur
rmdir gen-a gen-b
echo "done"

#!/usr/bin/env bash
# Spike 004 amendment: evalModules as wiring validator — behavior + latency.
set -u
cd "$(dirname "$0")"
NI="nix-instantiate --eval --strict --json"

echo "=== T1: valid wiring accepted ==="
$NI eval.nix --argstr wiringFile "$PWD/wiring.json" 2>&1 | head -5

echo "=== T2: type violation (bad semver) fails at eval ==="
sed 's/"1.0.0"/"not-a-version"/' wiring.json > bad-type.json
$NI eval.nix --argstr wiringFile "$PWD/bad-type.json" 2>&1 | grep -E "error|version" | head -4

echo "=== T3: undeclared capability fails at eval ==="
sed 's/"retrieve"/"telepathy"/' wiring.json > bad-cap.json
$NI eval.nix --argstr wiringFile "$PWD/bad-cap.json" 2>&1 | grep -E "error|telepathy|one of" | head -4

echo "=== T4: broken dependency caught by assertion ==="
sed 's/"chunker", "to"/"ghost", "to"/' wiring.json > bad-dep.json
$NI eval.nix --argstr wiringFile "$PWD/bad-dep.json" 2>&1 | grep -E "INVALID|undeclared" | head -3

echo "=== T5: swap embedder v2.1.0 -> v3.0.0 via JSON overlay + mkForce ==="
cat > swap.json <<'EOF'
{ "components": { "embedder": { "version": "3.0.0", "config_hash": "dddd4444", "capabilities": ["build-index"], "dependencies": ["chunker"] } } }
EOF
$NI eval.nix --argstr wiringFile "$PWD/wiring.json" --argstr overlayFile "$PWD/swap.json" --arg forceSwap true 2>&1 | head -5

echo "=== T6: latency (10 runs, valid wiring) ==="
t0=$(date +%s%N)
for i in $(seq 1 10); do $NI eval.nix --argstr wiringFile "$PWD/wiring.json" >/dev/null 2>&1; done
t1=$(date +%s%N)
echo "  mean: $(( (t1 - t0) / 10000000 )) ms per validation (cold process each time)"

rm -f bad-type.json bad-cap.json bad-dep.json swap.json
echo "done"

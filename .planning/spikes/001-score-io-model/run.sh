#!/usr/bin/env bash
# Spike 001 repro: compiler + schema + grammar + Proof + demo checks.
# No model, no GPU, no lock needed (nothing loads a model here).
# Everything runs on the shared venv interpreter with stdlib only.
set -u
D="$(dirname "$0")"
export LD_LIBRARY_PATH=/run/opengl-driver/lib:${LD_LIBRARY_PATH:-}
PY="$D/../.venv/bin/python"

echo "== python suite (acceptance 1-6, invariants, fuzz, schema mirror) =="
"$PY" "$D/test_spike.py" || exit 1

echo "== demo.html embedded JS syntax =="
"$PY" - "$D/demo.html" <<'PY'
import re, sys, subprocess, tempfile, os
html = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"<script>(.*)</script>", html, re.S)
assert m, "no <script> block found"
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
    f.write(m.group(1))
    js = f.name
r = subprocess.run(["node", "--check", js], capture_output=True, text=True)
print(r.stdout.strip() or "node --check: syntax OK")
if r.returncode != 0:
    print(r.stderr); sys.exit(1)
os.unlink(js)
PY
[ $? -eq 0 ] || exit 1

echo "== demo.html JS logic smoke (proveOp/TOK/opsInstr, stubbed DOM) =="
"$PY" - "$D/demo.html" <<'PY' > /tmp/spike001-demo-smoke.js
import re, sys
html = open(sys.argv[1], encoding="utf-8").read()
js = re.search(r"<script>(.*)</script>", html, re.S).group(1)
# full script loads untouched: stub DOM absorbs the two onclick registrations
stub = '''const document = { getElementById: (id) => ({ set onclick(v){}, innerHTML: "", value: "", }) };
'''
print(stub + js + '''
const assert = (n, c, d="") => { if (!c) { console.error("FAIL " + n + " " + d); process.exitCode = 1; } else console.log("ok " + n); };
assert("tok-words", JSON.stringify(TOK("a  b")) === JSON.stringify(["a","  ","b"]));
const C = "Ed Wood was born on 1924-10-10 in Poughkeepsie.";
assert("demo-prove-graph", proveOp({target:"graph",s:"Ed Wood",p:"born_on",o:"1924-10-10",evidence:[0,44]},["graph","sql"],C,new Set()).length === 0);
assert("demo-prove-fabricated", proveOp({target:"graph",s:"Ed Wood",p:"born_on",o:"1924-10-10",evidence:[30,44]},["graph","sql"],C,new Set()).length > 0);
assert("demo-prove-agent-denied", proveOp({target:"agent",ask:"x",why:"y"},["graph"],C,new Set()).length > 0);
assert("demo-prove-empty-ok", proveOp({target:"graph",s:" ",p:"p",o:"o",evidence:[0,1]},["graph"],C,new Set()).length > 0);
assert("opsInstr-names", opsInstr("graph,sql").includes("graph,sql"));
''')
PY
node /tmp/spike001-demo-smoke.js || exit 1

echo "SPIKE-001 ALL GREEN"

# Phase 6 eval-corpus snapshot

A second, independent corpus fixture for the eval bundle (06-04-PLAN.md Task 1, MACH-02). Built
by the same `databasise.parity.build_corpus_fixture` module as the Phase 3 parity corpus
(`tests/fixtures/corpus/`), at a larger question count and a row offset that shares no question
with the Phase 3 fixture — so the eval bundle has n=30 paired per-question differences to work
with (an A/A calibration needs n questions to produce n paired per-question differences; the
Phase 3 corpus is fixed at two questions deliberately, sized to what makes one v1 index
affordable, not to what a statistical floor needs — see `03-GATE-AMENDMENT.md`).

Regenerating the Phase 3 fixture at a larger n would change its `corpus_hash` and orphan the v1
index Phase 3 built and imported against it, so this is a second, disjoint fixture set, not a
resize of the first.

## Source

30 questions drawn from the **HotpotQA distractor-setting validation split**
(`hotpotqa/hotpot_qa`, config `distractor`, split `validation`), fetched from HuggingFace's public
datasets-server API, **offset 2** (rows 2-31 — the two rows `tests/fixtures/corpus/` already took
are rows 0-1). Each question's full distractor context (10 paragraphs: the gold supporting
document(s) plus 8-9 distractor paragraphs) is included, giving 291 unique documents total.

MACH-02's own text asks the eval bundle to be bootstrapped from a public benchmark corpus — this
fixture is exactly that: HotpotQA's distractor validation split, fetched through the same public
datasets API the Phase 3 fixture already uses. `RIG.md §EV.1`'s own sequencing clause bounds what
that satisfies, though: a benchmark supplies the instrument, never the decision — only local
measurement on this project's own corpus settles anything. Phase 7's HARD-04 is where the owner's
own corpus layers in; this fixture is the instrument the eval bundle mints against until then.

## Contents

- `MANIFEST.json` — per-document id, title, and SHA-256; a corpus-level SHA-256 over the sorted
  per-document digests; the source dataset name/config/split; the 30-query set (each paired with
  its gold supporting document ids per HotpotQA's own `supporting_facts`, query ids `q3`-`q32` —
  offset-anchored, not `q1`-`q30`, so no id collides with the Phase 3 corpus's own `q1`/`q2`) and
  its own SHA-256.
- `documents/<id>.txt` — one plain-text file per document (`<title>\n\n<paragraph text>`), the id
  being a filesystem-safe slug of the HotpotQA title.

## Regenerating

```bash
cd databasise && SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt uv run python -m databasise.parity.build_corpus_fixture --num-questions 30 --offset 2 --fixture-dir tests/fixtures/eval-corpus
```

(`SSL_CERT_FILE` is only needed because the `uv`-managed interpreter's bundled OpenSSL does not
pick up this host's CA bundle by default; harmless to set unconditionally.) The HotpotQA
validation split is a fixed, versioned public dataset, so re-running this regenerates
byte-identical output — it is not a fresh random draw. The bare, no-argument invocation
(`python -m databasise.parity.build_corpus_fixture`) still regenerates the Phase 3 corpus at
`tests/fixtures/corpus/`, byte-identically, unaffected by this fixture's own build.

## Reading it

Use `databasise.parity.corpus.load_snapshot(Path("tests/fixtures/eval-corpus"))` — never read
`MANIFEST.json` or the `documents/` files directly. The loader recomputes every digest from disk
and raises `CorpusDriftError` naming the first mismatched document id if anything here has
drifted from what the manifest declares.

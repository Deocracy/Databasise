# Phase 3 parity corpus snapshot

Fixed corpus fixture for the Phase 3 parity comparison (03-02-PLAN.md Task 2, D-06/D-14). Both the
v1 original arm and the decomposed v2 query side read the **same** index, built exactly once from
this snapshot — see `v1/README-PARITY.md`.

## Source

2 questions drawn from the **HotpotQA distractor-setting validation split**
(`hotpotqa/hotpot_qa`, config `distractor`, split `validation`), fetched from HuggingFace's public
datasets-server API (rows 0-1, offset 0). Each question's full distractor context (10 paragraphs:
the gold supporting document(s) plus 8-9 distractor paragraphs) is included, giving 20 unique
documents total with no overlap between the two questions.

Size is deliberately small — "sized to what makes one v1 index affordable rather than to what a
statistical floor would need" (03-02-PLAN.md; D-10 is not calibrated in this phase).

## Contents

- `MANIFEST.json` — per-document id, title, and SHA-256; a corpus-level SHA-256 over the sorted
  per-document digests; the source dataset name/config/split; the 2-query set (each paired with
  its gold supporting document ids per HotpotQA's own `supporting_facts`) and its own SHA-256.
- `documents/<id>.txt` — one plain-text file per document (`<title>\n\n<paragraph text>`), the id
  being a filesystem-safe slug of the HotpotQA title.

## Regenerating

```bash
cd databasise && SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt uv run python -m databasise.parity.build_corpus_fixture
```

(`SSL_CERT_FILE` is only needed because the `uv`-managed interpreter's bundled OpenSSL does not
pick up this host's CA bundle by default; harmless to set unconditionally.) The HotpotQA
validation split is a fixed, versioned public dataset, so re-running this regenerates
byte-identical output — it is not a fresh random draw.

## Reading it

Use `databasise.parity.corpus.load_snapshot()` — never read `MANIFEST.json` or the `documents/`
files directly. The loader recomputes every digest from disk and raises `CorpusDriftError` naming
the first mismatched document id if anything here has drifted from what the manifest declares.

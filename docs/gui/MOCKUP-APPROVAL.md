# Operator Console Mockup Approval

variant: console-a
path: mockups/operator-console.html
sha256: 3ac0e278c929ba41179249a47606edb910ae4b6032b1d0acb9fc19a739c0c837
approved_commit: a9a3a24a351d3a1b7d877aff9b123459f8310d7b
approved: 2026-10-30 by the owner, file:// click-through (D-11)
refrozen: 2026-11-01 by the owner (freeze-variant console-a)
ids: 623

## Re-freeze 2026-11-01

The owner rebuilt the mockup with `python3 mockups/build.py` and re-ran `freeze-variant --variant console-a`. The only change is the embedded refusal catalogue, which gained `NonEncodableTextError` (422, attribute `field`) from the 2026-11-01 security fixes. Screens, controls and the 623 ids are unchanged: `scripts/mockup-id-check.py` exits 0 and the Phase 17 suite passes 68/68. The previous approved digest was `bf98e79e0a0312940963efae9028e708a012021bfc62f51ebdbca57918034d20`.

## Owner approval text (verbatim)

> approved

Given 2026-10-30, after the owner opened the mockup from file:// and walked the six screens (D-11, D-12). Nothing was published.

## Phase 18 handoff (D-13)

Phase 17 does not write `mockup_freeze`. The first plan of Phase 18 does this, in order:

1. Check that `sha256sum mockups/operator-console.html` equals the digest above. A changed digest means the owner approves again before the freeze.
2. Run `python3 scripts/ledger-amend.py freeze-variant --variant console-a --path mockups/operator-console.html`.
3. From then on `scripts/mockup-id-check.py` requires every frozen id in the built UI or in MOCKUP-PORT.md (LIVE-09).

`mockups/build.py --check` proves the approved bytes are reproducible from `mockups/src/`.

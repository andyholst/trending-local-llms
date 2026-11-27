# Tasks

- [x] 1. Tracked change created before any edit.
- [x] 2. Measured the README-only case: `make render-readme` removed the sentence (grep 1 -> 0) and restored README byte-for-byte; documented on issue #1850 comment 7229162957.
- [x] 3. Added the one-sentence bridge to the generator's intro string in `scripts/update_trending.py` (prose literal only) and regenerated `README.md` with `make render-readme` — no hand-edited generated table.
- [x] 4. Verified two consecutive renders are idempotent; README diff is exactly one paragraph; no table row, number or badge changed.
- [x] 5. `findings/1850.md` records the template constraint and the residual rulebook row.
- [x] 6. `OPENSPEC.md` regenerated from `openspec/changes/**`.

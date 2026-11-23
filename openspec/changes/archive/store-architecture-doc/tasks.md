# Tasks: store-architecture-doc

- [x] Create the tracked change before any edit (proposal + capability spec + task checklist)
- [x] Correct `ARCHITECTURE.md` §2 to the shipped three-file store and add the `<!-- arch:dataflow -->` anchor
- [x] Add `docs/store.md` (shape, budgets, flatten seam, per-run footprint variants)
- [x] Extend `scripts/architecture_check.py` with `store_file_findings` (names-only) and register the anchor
- [x] Add the `tests/test_architecture.py` guard tests and update the fixture anchor set
- [~] Carry the declared `AGENTS.md` §7b wording + rule-3c note and the §8 regression row — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Run `make lint`, `make architecture-check` and the focused guard
- [x] Write `findings.md`, push the branch and open a non-draft PR whose title and body both carry `Closes #1395`; record/archive the change on that branch

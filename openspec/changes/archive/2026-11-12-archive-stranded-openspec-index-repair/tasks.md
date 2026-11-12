# Tasks: archive-stranded-openspec-index-repair (#864)

- [x] Open the OpenSpec change (proposal, spec, tasks) and land the first unique commit
- [x] `make openspec-archive NAME=openspec-index-repair` — moved under `openspec/changes/archive/`, delta promoted (never deleted, rule 3b)
- [x] `make openspec-index` regenerates `OPENSPEC.md`
- [x] PR opened with the five-section pattern and the single `closes #864` claim
- [x] `PR:` recorded on this change, then `make openspec-archive NAME=archive-stranded-openspec-index-repair` in the same branch — the repair archives its own record (#780/#851 pattern)
- [x] `make openspec-index` regenerated again; CI green on the PR head (archive-check, openspec-check, unit tests) and auto-merge lands it

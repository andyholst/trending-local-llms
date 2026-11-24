# Tasks: auto-merge-rebase-architecture-block

- [x] Add `regenerate_architecture(wt)` beside `regenerate_index(wt)` and refresh both in `rebase_and_push`
- [x] Resolve a generated-pair-only rebase conflict by taking the branch side and continuing
- [x] Name both artifacts in `scripts/auto_merge_rebase.py`'s verdict text
- [x] Add the RED-first guards in `tests/test_auto_merge_rebase.py` and prove them against `origin/master`'s seam
- [x] Regenerate `ARCHITECTURE.md` (§10 inventory) and `OPENSPEC.md` for this change
- [x] Run the focused test module and `make lint`

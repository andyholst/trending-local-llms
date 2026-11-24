# Tasks: auto-merge-rebase-current-bot-regen

- [x] `scripts/pr_health.py`: shared `sync_branch(cwd, head, *, rebase)` core with the optional rebase, both regenerators, no-op short-circuit and lease push; `rebase_and_push` stays the `rebase=True` wrapper, `regenerate_current` is the `rebase=False` entry point; `_git` identity and the PAT/CI-proof seam reused unchanged
- [x] `scripts/auto_merge_rebase.py`: the `current` branch runs `regenerate_current` and reports `verdict=regenerated` + the existing `rebased=true` squash-skip key; an already-current pair stays `current`; docstring/argparse description updated
- [x] `tests/test_auto_merge_rebase.py`: four real-git scenarios (stale current index, already-current, both-artifacts-stale, human-owned stale) registered in `main()`; RED-verified against `origin/master`'s scripts (7/7/2 new FAILs)
- [x] Rulebook (rule 3c, review-required): §6e and the §8 `tests/test_auto_merge_rebase.py` row gained the current-bot-head case; §6s left byte-identical
- [x] `ARCHITECTURE.md` target / job / script rows updated and the §10 inventory block regenerated; `make architecture-check` green
- [x] Fast offline gates: Python syntax, `make lint`, the targeted test modules (`test_auto_merge_rebase.py` 155/0, `test_pr_health.py` 121/0, `test_agents_rows.py` 124/0, `test_agents_store_rows.py` 13/0, `test_architecture.py` 111/0)
- [x] OpenSpec change (proposal, capability spec with Given/When/Then + resolving Test lines, tasks), index regenerated; PR opened ready with `Closes #1645` in title and body

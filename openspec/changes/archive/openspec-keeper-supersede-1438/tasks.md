# Tasks: openspec-keeper-supersede-1438

- [x] Add the pure `archived_count()` parser and `classify_superseded()` to `scripts/keeper_pr.py`
- [x] Close a SUPERSEDED keeper with its count evidence BEFORE the live/tombstone/unmergeable dedupe, so it neither suppresses a fresh repair nor lingers
- [x] Extend `tests/test_keeper_pr.py`: the stale/CURRENT pair, the close-and-still-land behaviour, and the RED-on-base proof
- [x] Update `ARCHITECTURE.md` script rows and regenerate the §10 inventory (`make architecture-refresh`) — measured: `keeper_pr.py`'s docstring is unchanged so no row moved; `make architecture-check` green at the head
- [~] Extend the `AGENTS.md` §8 row for `tests/test_keeper_pr.py` to name the SUPERSEDED classifier — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Write `findings.md`, run the focused module, `make lint`, `make architecture-check`, `make openspec-check` and `make test`
- [x] Open the PR against `master` carrying `Closes #1438`, archive this change on the head, and hand over to `tll-reviewer`

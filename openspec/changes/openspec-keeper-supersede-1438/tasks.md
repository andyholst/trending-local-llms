# Tasks: openspec-keeper-supersede-1438

- [ ] Add the pure `archived_count()` parser and `classify_superseded()` to `scripts/keeper_pr.py`
- [ ] Close a SUPERSEDED keeper with its count evidence BEFORE the live/tombstone/unmergeable dedupe, so it neither suppresses a fresh repair nor lingers
- [ ] Extend `tests/test_keeper_pr.py`: the stale/CURRENT pair, the close-and-still-land behaviour, and the RED-on-base proof
- [ ] Update `ARCHITECTURE.md` script rows and regenerate the §10 inventory (`make architecture-refresh`)
- [~] Extend the `AGENTS.md` §8 row for `tests/test_keeper_pr.py` to name the SUPERSEDED classifier — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [ ] Write `findings.md`, run the focused module, `make lint`, `make architecture-check`, `make openspec-check` and `make test`
- [ ] Open the PR against `master` carrying `Closes #1438`, archive this change on the head, and hand over to `tll-reviewer`

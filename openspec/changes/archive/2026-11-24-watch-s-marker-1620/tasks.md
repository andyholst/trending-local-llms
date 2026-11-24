# Tasks: watch-s-marker-1620

- [x] Add `S:` to `MARKER_PREFIXES` and the offline `--check` contract in `scripts/watch_monitor.py`
- [x] Document `S:` in the module docstring marker list
- [x] Guard both in `tests/test_watch_monitor.py::test_offline_check_mode`
- [~] Extend AGENTS.md §6w/§6j with the `S:` marker and its `<claim-id>` dedup key — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Update ARCHITECTURE.md rows and regenerate `OPENSPEC.md`
- [x] Run the focused module, `make lint`, `make architecture-check`, `make openspec-check`
- [x] Write `findings/1620.md` and push the branch for review

# Tasks: refresh-fixture-generated-paths-1828

- [x] Add the recorded channel fixture to `GENERATED_PATHS` and `KEEP_PATHS` in `scripts/refresh_base.py`
- [x] Add RED-first guards for acceptance, payload survival and Makefile-derived path coverage to `tests/test_refresh_base.py`
- [x] Prove the guards RED on the fetched base and GREEN on the change
- [x] Run the focused test module and `make lint`, write `findings/1828.md`, regenerate `OPENSPEC.md`
- [x] Push the branch, open the PR closing #1828, archive the tracked change on the head and hand over to tll-reviewer

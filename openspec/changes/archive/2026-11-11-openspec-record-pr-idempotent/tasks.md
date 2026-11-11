# Tasks

- [x] 1. The tracked change exists (this directory) before any code lands
- [x] 2. Measured the gap: `record()` in `scripts/openspec_record_pr.py` iterates
  ACTIVE changes only, so a re-run on an already-archived change raised
  `NoSuchChange` rather than the `AlreadyThere` the docstring promised (#754)
- [x] 3. `scripts/openspec_record_pr.py`: added the `AlreadyThere` exception and a
  second prong — when no active change matches, an ARCHIVED change for the same
  `Issue:` is the already-recorded state, raised `AlreadyThere`
- [x] 4. `scripts/openspec_record_pr.py`: `main()` catches `AlreadyThere` and exits 0,
  naming the change as already recorded and editing nothing; the unmatched-issue
  refusal still exits 2
- [x] 5. `tests/test_openspec_record_pr.py`: added
  `test_rerun_on_an_already_archived_change_is_a_noop` (re-run exits 0, no active
  change re-created, archive unedited, names the change); the unmatched-issue
  test still exits 2
- [x] 6. `python3 tests/test_openspec_record_pr.py` green on the tree
- [x] 7. `OPENSPEC.md` regenerated (`python3 scripts/openspec_index.py --write`) and
  `python3 scripts/openspec_index.py --check` green
- [x] 8. `make lint` shape green (every tracked file ends with a newline) and the
  diff holds no secret

# Tasks: missing-gh-fixture-host-path (issue #895)

- [x] `_run` gains `bare_path` (PATH replaced by the fixture bindir) with prepend kept as the default — verified: patch applied, module lint clean
- [x] `test_a_missing_gh_is_loud` runs with `bare_path=True` — verified: `python3 tests/test_openspec_archive_check.py` on a host WITH gh: `PASSED ... | FAILED 0`
- [x] Sibling suites audited for the same missing-tool-through-prepend shape — verified: grep `not installed|missing gh|empty-path` across `tests/*.py` found only SKIP-when-absent guards, no second exit-2 contract to fix
- [x] New behavior RED against the pre-change module (rule 6c) — verified: `git show origin/master:tests/test_openspec_archive_check.py` swapped in reproduces `FAIL missing gh: exits 2 [1]` + `FAIL missing gh: names the tool` on this host
- [ ] AGENTS.md §8 row extended with the #895 host-portability guarantee, same branch
- [ ] Gates green on the branch head (`make lint`, module suite, `make openspec-check`); PR opened for #895 (never draft), one `Closes` bound to #895

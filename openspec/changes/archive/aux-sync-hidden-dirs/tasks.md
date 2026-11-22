# Tasks: aux-sync-hidden-dirs

- [x] Skip dot-directories in `collect_targets()`'s `--all-profiles` enumeration — verified by the new guard on a scratch home
- [x] Keep explicit `--profile .deleted` refused (exit 2) — verified by the new guard
- [x] Add `test_all_profiles_skips_hidden_directories_but_explicit_hidden_name_still_refused` to the module and its runner — verified green in the test image (`PASSED 47 | FAILED 0`) and RED on `origin/master` (3 failures)
- [x] Add the AGENTS.md §8 row and keep lint / architecture / openspec gates green
- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks) and index regenerated
- [x] Full local gate run green (`make test`, `make lint`, `make architecture-check`, `make openspec-check`, `make findings-check`)

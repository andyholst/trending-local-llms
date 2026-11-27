# Tasks: merge-tree-index-race-verdict-1822

- [x] Add the pure classifier `scripts/merge_tree_index.py::classify` with its two verdicts
- [x] Add `make merge-tree-index-classify` (host `_` recipe + docker wrapper via `python-env-image`)
- [x] Extend the #1239 merge-tree step additively with capture → classify → one fresh-master retry, keeping every existing clause and the unchanged index check
- [x] Extend `tests/test_openspec_merge_tree_check.py` with the five RED-first named guards and wire them into `main()`
- [x] Prove the two RED-first tests fail on the pre-change base revision while the two preserved-clause tests stay green
- [x] Add the `ARCHITECTURE.md` target/script rows and regenerate its §10 block
- [x] Generate and archive this OpenSpec change bound to #1822; regenerate `OPENSPEC.md`
- [x] Run the focused module and the fast offline checks, push and hand the PR to `tll-reviewer`

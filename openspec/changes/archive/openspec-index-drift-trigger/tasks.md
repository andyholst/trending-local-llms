# Tasks: openspec-index-drift-trigger

- [x] Create the tracked change before any edit (`proposal.md` + Given/When/Then capability spec + this checklist).
- [x] `scripts/openspec_index.py`: add `--drift` beside `--check`, reusing the ONE measure `index_drift()` — prints exactly `drift=<n>` on stdout, exits 0 for any drift, reasons on stderr; a missing/unreadable `OPENSPEC.md` is stderr + exit 2 with no stdout. `MAX_OPENSPEC_INDEX_DRIFT` and the WARN branch are untouched.
- [x] `Makefile`: new `openspec-index-drift` target beside `openspec-index-check`, same `python-env-image` wrapper, declared `.PHONY`.
- [x] `.github/workflows/qa-validate.yml`: validate publishes the allowlisted `index_drift` key from a step that runs `make openspec-index-drift` and parses only `drift=`; `index-repair`'s `if:` widens to `(failure() || needs.validate.outputs.index_drift != '0')` on a push to `master` — `failure()` stays.
- [x] `scripts/master_alarm.py::GATES`: additive `"openspec-index-drift": ("alarm", "master-alarm")` (required — `validate_gates_from_trees()` reads every `make X` in the validate job).
- [x] New `tests/test_openspec_index_drift.py` driving the REAL CLI (a byte-identical copy of the script inside a tempdir fixture shaped like `cb139e7c`) plus the workflow/Makefile/registry wiring; every `test_*` called from `main()`. RED on pristine `origin/master` (`PASSED 10 | FAILED 14`, exit 1 — argparse rejects `--drift`), GREEN on this head (`PASSED 24 | FAILED 0`).
- [x] `tests/test_workflows.py`: the `index-repair` test gains the drift-clause assertion and the `validate` output-key assertion.
- [x] `AGENTS.md` §6q, the §6b `index-repair` row and one §8 row for the new guard — **rule 3c review-required**: the architect declared the sections on #1634 (issuecomment-7139758319) and `tll-reviewer` signs off the diff. Landed under the owner-authorized #1591 mechanism (`security.protected_instruction_files: false`, backups kept); no box is left bare or blocked.
- [x] `ARCHITECTURE.md`: the new public-target row, the corrected §4 `index-repair` job row, and `make architecture-refresh` in the same change (rule 6h).
- [x] `findings/1634.md` written; `OPENSPEC.md` regenerated; `make lint`, `make architecture-check`, the targeted module and the message-pattern/closure checks green.
- [x] Open the READY PR carrying `Closes #1634` in BOTH title and body, `make openspec-record-pr` archives this change, and the signed `pr #1634 · handover tll-reviewer` comment is posted on the issue.

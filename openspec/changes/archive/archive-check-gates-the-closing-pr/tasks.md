# tasks: archive-check-gates-the-closing-pr

- [x] `scripts/openspec_archive_check.py` gains the closing-PR prong (`--pr`, closing issues parsed through `scripts/pr_closure.py`; unreadable PR is exit 2) — verified by `python3 tests/test_openspec_archive_check.py` (16 tests, all pass)
- [x] `make openspec-archive-check PR=<n>` forwards the flag and `qa-validate.yml`'s lifecycle step passes the event's PR number on `pull_request` — asserted by `tests/test_openspec_archive_check.py::test_the_workflow_passes_the_pull_request_number`
- [x] New tests in `tests/test_openspec_archive_check.py` lock every scenario (fixture tree + stub `gh`, rule 6m) and the suite stays discovered by `scripts/run_tests.sh` (`wired()` green)
- [x] The stranded change `ban-pytest-imports-in-tests` is recorded (`make openspec-record-pr ISSUE=768 PR=778` — PR #778, commit `8567925`, is the PR that merged its work) and archived, and `make openspec-index` regenerated — `make openspec-archive-check` green against the real tree
- [x] `AGENTS.md` §6f and §8 carry the closing-PR row (rule 3c: announced in the issue's owed-row comment)
- [x] `ARCHITECTURE.md` regenerated (`make architecture-refresh`) and `make architecture-check` green (rule 6h)
- [x] `make openspec-check`, `make lint` and the test suite green on the branch; `make secret-scan` clean before push
- [~] This change is recorded and archived by its own landing PR (`make openspec-record-pr ISSUE=779 PR=<pr>`) before the final push — blocked: the PR number does not exist until this PR is opened; the record + archive land in this PR's final commit

# Tasks: auto-merge-closure-proof-token

- [x] Measure the success/failure auto-merge env difference and confirm `closingIssuesReferences` never carries `state`
- [x] Move the closure proof into its own `auto-merge` step under `github.token`, with `issues: read` + `pull-requests: read` on the job
- [x] Keep the squash command, owner PAT and `--match-head-commit` gate byte-identical
- [x] Add the RED-first wiring guard in `tests/test_verify_closure.py` and the per-issue analysis `findings/1677.md`
- [~] Add the `AGENTS.md` §8 guard row for `tests/test_verify_closure.py::test_the_merge_job_proves_closure_with_a_credential_that_can_read_issues` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)

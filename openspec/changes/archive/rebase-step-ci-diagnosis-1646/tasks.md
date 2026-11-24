# Tasks: rebase-step-ci-diagnosis-1646

- [x] Capture the rebase seam's exit status and print its own output before failing (.github/workflows/qa-validate.yml)
- [x] Add the pure push-identity classifier and the GitHub-run identity read (scripts/pr_health.py)
- [x] Carry the matched run id + proven identity through verify_rebased_ci/rebase_and_push and the pr-health sweep
- [x] Print the proven and intended identities plus `push_identity_proved=` (scripts/auto_merge_rebase.py)
- [x] RED-first guards: the shipped step shell on a planted failing seam, the label selection, the real read, and the end-to-end PR #1631 shape (tests/test_auto_merge_rebase.py)
- [x] RED-verify all four new guards against `origin/master` (8 failures) and green on this head (141 passed, 0 failed)
- [~] Land the §8 regression-guard row for this fix in AGENTS.md, naming `make auto-merge-rebase`'s failure output and the actor-derived push identity — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg). The exact row text is carried in findings/1646.md as an owed row.
- [x] Run `python3 tests/test_auto_merge_rebase.py`, `make lint` and `make architecture-check`
- [x] Write `findings/1646.md` with the owed rulebook row and regenerate `OPENSPEC.md`

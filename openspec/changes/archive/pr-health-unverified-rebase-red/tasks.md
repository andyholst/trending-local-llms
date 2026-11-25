# Tasks: pr-health-unverified-rebase-red

- [x] `scripts/pr_health.py`: pure `unverified_rebases(outcomes)` (exactly the rows carrying
      `ci_verified is False`, the mirror of `failed_rebases`) + the named
      `UNVERIFIED_REBASE_REASON` — verified: `python3 tests/test_pr_health.py`
      (129 passed / 0 failed)
- [x] `scripts/pr_health.py::main`: consults that verdict after the rebaser half prints and
      REDS the round (`exit 1`) naming every affected PR and head, leaving a verified rebase,
      an already-current branch and a refused/failed rebase untouched; the module docstring's
      exit-code contract states the second red — verified: the new guard drives the REAL script
- [x] `tests/test_pr_health.py::test_an_unverified_rebase_reds_the_sweep_and_a_verified_one_stays_green`:
      REAL bare origin + clone, github-shaped configured origin with an `insteadOf` transport,
      stub `gh` only (rule 6m); plants the ZERO-jobs run for the pushed sha and asserts
      exit 1 + the named PR + the reason + `0 silent`, then the real-jobs shape stays GREEN —
      verified: RED-first proven against `origin/master`'s `scripts/pr_health.py`
      (PASSED 5 | FAILED 3), GREEN on this head (PASSED 8 | FAILED 0)
- [x] No workflow, Makefile or schedule change: `pr-health.yml` already runs
      `make pr-health REPO=… COMMENT=1 REBASE=1`, so the exit code propagates — verified:
      `git diff --name-only` names no `.github/workflows/` path
- [x] OpenSpec change created (proposal + Given/When/Then capability spec + tasks) and the index
      regenerated — verified: `make openspec-index` + `make openspec-check`
- [x] `findings/1647.md` authored and `make findings-check-for-pr` green

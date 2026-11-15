# Tasks: queued-alarm-diagnosis-half-runs-anyway

- [x] Patch `.github/workflows/queued-alarm.yml`: `if: ${{ !cancelled() }}` on every
      detector/diagnosis step of the `alarm` job (queued-run report, sweep-alarm's siblings:
      freshness-alarm, master-alarm, pipeline-failure-issue, ledger landing, owed-rows-check,
      check-branch-protection)
- [x] Add `test_every_alarm_step_runs_whatever_a_sibling_decided` to
      `tests/test_queued_run_alarm.py`: one verifier over the shipped workflow AND a planted
      copy with the `if:` lines removed (proves the guard goes red on the old shape, rule 6c)
- [x] Verify the verifier is red against the pre-change workflow text (`git show
      origin/master~0` before the patch is applied — run against the file's HEAD version)
- [x] `python3 tests/test_queued_run_alarm.py` green end to end
- [x] `make openspec-check` green for this change (proposal, spec scenarios each name their
      test, every box ticked)

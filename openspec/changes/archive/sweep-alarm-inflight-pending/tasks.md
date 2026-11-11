# Tasks — sweep-alarm-inflight-pending (#801)

- [x] `scripts/sweep_alarm.py`: one in-flight state set (`IN_FLIGHT_CONCLUSIONS`), the PENDING
      verdict inside the fresh branch, `--inflight-cap-hours` (default 3), hung-past-the-cap FAIL.
      Verified: `python3 tests/test_sweep_alarm.py` → PASSED 33 | FAILED 0.
- [x] `tests/test_sweep_alarm.py`: fresh `in_progress`/`queued` → PENDING, exit 0 — the pure
      decision AND the real CLI through the stub `gh` (the measured 15:19Z `in_progress` row).
      Verified by the same run.
- [x] `tests/test_sweep_alarm.py`: `in_progress` PAST the cap → exit 1 naming HUNG — pure AND
      CLI. Verified by the same run.
- [x] The #498 fresh-red scenarios (concluded `failure`) and the dropped-slot scenarios are
      byte-unchanged — Verified: the two pre-existing fresh-red tests still pass, and the diff
      touches only the in-flight branch, the new flag, and the new prints.
- [x] Old code goes RED on the new tests (rule 6c). Verified: `origin/master`'s `stale()` has no
      cap argument (TypeError), and its fresh branch prints the FAIL for the 14-min
      `in_progress` delivery the new tests feed it.
- [x] `AGENTS.md` §8 guard row extended (issue #801, the PENDING/HUNG failure modes) and the
      rule-3c comment declaring exactly that section posted on #801
      (`issues/801#issuecomment-6807481801`).
- [x] Findings recorded in `findings.md` and filed (`make findings-check` + `make file-findings`)
      — the `MAX_AGE_HOURS ?= 3` hourly-era legacy against the weekly cadence, found while
      reading the #86/#87/#88 logs.

# Tasks — hermes-pin-freshness (issue #1091)

- [x] Register `hermes-pin-drift-signature` in `scripts/bot_markers.py` (`DEDUP_KEYS`; acceptance +
      canonical examples derive from the key) and keep `tests/test_bot_markers.py` green
- [x] Implement `scripts/hermes_pin_freshness.py`: read both pins (Makefile/Dockerfile), refuse a
      disagreement (exit 2) before the channel read; compare against the release channel via the real
      `gh` client or `--from-file`; OK/newer-drift/ahead/unreadable verdicts with exits 0/1/0/2; file
      ONE marker-deduplicated `tech-debt` issue naming the #218 remedy
- [x] Record the real channel payload in `tests/fixtures/hermes_releases_latest.json`
- [x] Wire the Makefile: `_hermes-pin-freshness` internal recipe + public `hermes-pin-freshness`
      target (`REPO=`/`FROM_FILE=`/`DRY=1`), registered in `.PHONY`
- [x] Add the `make hermes-pin-freshness` report-and-file step to `queued-alarm.yml`'s alarm job
      (default token, `!cancelled()`, alarm-step pattern)
- [x] Write `tests/test_hermes_pin_freshness.py`: planted-fixture suite driving the REAL script
      through a stub `gh` (equal/newer+file+remedy/dedup+closed/ahead/unreadable/pin-split/recorded
      payload) and the wiring guard (missing step REFUSED, makeless step REFUSED, marker registration)
- [x] Update `ARCHITECTURE.md`: target row, script row (§6), queued-alarm job-step line, and
      regenerate the §10 block via `make architecture-refresh` in the same change
- [x] Gates green: targeted tests, `bash scripts/run_tests.sh`, `make lint`, `make architecture-check`,
      `make openspec-check`, `make secret-scan`, `make secret-scan-self-test`,
      `make findings-check` + `make file-findings`
- [x] Open the ready PR closing #1091 and monitor its checks to green

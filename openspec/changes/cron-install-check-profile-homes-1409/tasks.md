# Tasks: cron-install-check-profile-homes-1409

- [x] Add `hermes_homes()` — `$HERMES_HOME`, `~/.hermes`, then `~/.hermes/profiles/*` sorted, never repeated
- [x] Add `discover_jobs()` — the first candidate carrying jobs wins, an empty jobs file is skipped, `(None, [])` when none
- [x] `main()` discovers the jobs file and the matching home's `scripts/`, keeping the `--jobs` / `--wrappers` / `CRON_JOBS` overrides
- [x] A host with no jobs fails with the existing watchdog refusal, never a traceback
- [x] `tests/test_cron_install_check.py` covers the order, the empty-file skip, the clean no-jobs failure and the overrides
- [x] Regenerate `OPENSPEC.md` and run the gates

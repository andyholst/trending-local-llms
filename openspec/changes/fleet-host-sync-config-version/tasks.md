# Tasks: fleet-host-sync-config-version

- [x] Cut `ci/fleet-host-sync-config-version-1389` from the fetched `origin/master` `f2b3db89` in its own worktree, leaving the caller's checkout untouched
- [x] `scripts/fleet_host_sync_check.py` drops the host's own `_config_version:` scalar from a lane `config.yaml` before the byte compare (that key, that file only)
- [x] `tests/test_fleet_lifecycle.py::test_real_seam_tolerates_hermes_config_version` proves both halves (planted `_config_version` tolerated; planted stale `model:` red) and that `SOUL.md` is not covered
- [x] Register the new guard in the module's hand-rolled `main()`
- [x] RED-prove the guard: swap `origin/master:scripts/fleet_host_sync_check.py` in, confirm `FAIL a planted _config_version scalar is tolerated` (1 divergence), then restore
- [x] `make lint`, `make architecture-check`, `make findings-check` green on the branch
- [~] Extend the `AGENTS.md` §8 row for `tests/test_fleet_lifecycle.py` to name `test_real_seam_tolerates_hermes_config_version` and the one-key `_config_version`-on-`config.yaml` tolerance — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Write `findings.md` (owed-row declaration), regenerate `OPENSPEC.md`, run the full `make test`

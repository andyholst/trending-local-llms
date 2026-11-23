# Tasks: fleet-host-sync-runtime-stamps

- [x] Cut `fix/fleet-host-sync-hermes-stamps-1401` from the freshly fetched `origin/master`
      `e5e52714edec6c5a1166c31d0bc13413a42a4cbd` in its own worktree, leaving the caller's checkout
      untouched
- [x] `scripts/fleet_host_sync_check.py` compares a lane `config.yaml`'s OWNED blocks against the
      fetched base blob through the ONE drift verdict, so any Hermes runtime stamp is tolerated
- [x] `tests/test_fleet_lifecycle.py::test_real_seam_tolerates_hermes_runtime_stamps` proves the
      tolerance (`_config_version`, `onboarding.seen`, a novel stamp), the teeth (a stale
      `model:` / `model_aliases:` / `fallback_providers:` byte reds naming
      `tll-implementer/config.yaml`), and that `SOUL.md` + the lane skill stay byte-exact
- [x] Register the new guard in the module's hand-rolled `main()`
- [x] `make fleet-host-sync-check BASE=origin/master` answers 0 divergences on the real host, and
      the same seam accepts a copy of that home with `onboarding.seen` planted
- [x] `make lint`, `make architecture-check`, `make test` green on the branch
- [x] Regenerate `OPENSPEC.md` and run the full `make openspec-check`

# Tasks: provision-fleet-profile-homes (issue #1142)

- [x] `scripts/agent_profile_provision.py` — the ONE provisioning seam (rule 6d): lanes from
      `agent_model_chain.fleet_lanes`, bytes from `agent_model_chain.render_text`, credential check
      through `scripts/require_env.py` (issue #357); refuses (exit 2, writing nothing) an absent
      credential, a lane config that drifted from the chain, an unreadable chain, an unknown lane,
      and an unnamed run; `--dry-run` proves without writing
- [x] Rule 3b: a lane home's existing `config.yaml` is kept as `config.yaml.bak-<UTC>` beside the
      new file — never destroyed, never re-written
- [x] Rule 3e: credential NAMES only — `key_env` checked for presence, values never read, printed or
      measured; every provisioned config carries `key_env`, never a credential field
- [x] `Makefile`: `_agent-profile-provision` (the seam) + `agent-profile-provision` (public;
      `LANE=<lane>` / `ALL=1` / `PROFILES_HOME=<dir>`)
- [x] `qa-validate.yml` `live-smoke`: `make agent-profile-provision ALL=1
      PROFILES_HOME="$RUNNER_TEMP/hermes-profiles"` so the seam is executed by the pipeline (rule 6m)
      against a temp home, never a real profile home
- [x] `tests/test_agent_profile_provision.py` — 37 assertions across 7 tests, standalone module, real
      seam against a scratch tree + scratch profile home (rule 6m): copy + backup, refuse-without-key
      writes nothing, refuse-drift, names-not-values, never-a-default + unknown lane + dry run,
      `--all` over the tree-derived fleet, wiring — all green
- [ ] `ARCHITECTURE.md`: the `agent-profile-provision` target row and the
      `scripts/agent_profile_provision.py` §6 row, then `make architecture-refresh` for the inventory
      block and `make architecture-check` green (rules 6h/6c)
- [ ] `make openspec-index` regenerated and `make openspec-check` green (backlog cap + binding included)
- [ ] `make test`, `make lint`, `make secret-scan` + `make secret-scan-self-test` and
      `make check-secret-output` green on this branch (rules 3d/6c/6m)
- [ ] `AGENTS.md` §8 row for `tests/test_agent_profile_provision.py` (rule 6c) and `findings.md` in
      this change (rule 6g)

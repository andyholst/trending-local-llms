# Tasks — profile-drift-check (issue #1204)

- [x] `scripts/agent_profile_provision.py`: `check_one` (whole-copy lanes vs owned-block merges) + `--check` mode (exit 1 stale / 0 CLEAN / 2 missing, read-only, no credential), write paths unchanged
- [x] Makefile: `CHECK ?=` + `$(if $(CHECK), --check,)` in PROVISION_ARGS; target help names it; expansion proved with `make -n`
- [x] `tests/test_agent_profile_provision.py`: stale/clean report, no-write/no-credential, green-after-provision, missing-home exit 2, CHECK wiring — PASSED 66 | FAILED 0
- [x] Rule 6c red-on-old-seam proof: `git show origin/master:scripts/agent_profile_provision.py --check` → `error: unrecognized arguments: --check`
- [x] Live host proof: `make agent-profile-provision CHECK=1 ALL=1 PROFILE=<22 non-lane homes>,default` → `CLEAN: 30 home(s) match the rendered chain byte-for-byte`
- [x] OpenSpec change: proposal, capability spec with Test lines, this checklist
- [x] ARCHITECTURE.md rows + `make architecture-refresh`; AGENTS.md §8 row (rule 3c comment on #1204)
- [x] `findings.md` + `make findings-check` (0 findings); `make lint` + `make architecture-check` + `make openspec-check` green
- [~] Full suite (`make test`) green on the PR head — blocked: qa-validate runs it after push; on the host the affected module is green (66 checks)
- [x] PR opened (#1211, five-section body, single `closes #1204`), `make pr-message-check` green, `make openspec-record-pr ISSUE=1204 PR=1211` so the archive sits at the PR head

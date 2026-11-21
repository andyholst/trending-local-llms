# Tasks: fleet-aux-local-sync (issue #1198)

- [ ] T1: `scripts/agent_aux_local_sync.py` — chain-driven local-id sync for `custom_providers[strata]` + `moa:` with byte-preservation, backup, idempotence, `--check`/`--dry-run`, refusals (no local tier; ambiguous ids; multi-key models map).
- [ ] T2: `tests/test_agent_aux_local_sync.py` — house-pattern standalone tests (scratch repo + profiles home).
- [ ] T3: Makefile `agent-aux-local-sync` target (PROFILE= comma list, ALL_PROFILES=1, CHECK=1, DRY_RUN=1, PROFILES_HOME=).
- [ ] T4: agents/README.md documents the seam beside agent-profile-provision.
- [ ] T5: run the seam on the host (all profiles + default), re-audit verify.
- [ ] T6: PR opened, `make pr-message-check`, `make openspec-record-pr ISSUE=1198 PR=<pr>` at the PR head.

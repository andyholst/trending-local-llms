# Tasks: fleet-aux-local-sync (issue #1198)

- [x] T1: `scripts/agent_aux_local_sync.py` — chain-driven local-id sync for `custom_providers[strata]` + `moa:` with byte-preservation, backup, idempotence, `--check`/`--dry-run`, refusals (no local tier; ambiguous ids; multi-key models map).
- [x] T2: `tests/test_agent_aux_local_sync.py` — house-pattern standalone tests (scratch repo + profiles home): PASSED 42 | FAILED 0 (incl. the CI-fixture guard that reads the live-smoke leg's own printf payload; sabotage-proven red when the moa rewrite is disabled); regressions chain 84/84, provision 55/55.
- [x] T3: Makefile `agent-aux-local-sync` target (PROFILE= comma list, ALL_PROFILES=1, CHECK=1, DRY_RUN=1, PROFILES_HOME=); expansion proved with `make -n`.
- [x] T4: ARCHITECTURE.md rows (target + script tables) + regenerated §10 inventory, AGENTS.md §8 guard row, and a qa-validate live-smoke leg wire the seam (rules 6h/6m/3c).
- [x] T5: run the seam on the host (all profiles + default): 23 homes synced (22 profiles + default), 7 lanes clean, `CHECK=1` → 0 drifted / 30 clean; independent yaml re-audit + byte-comparison vs the run's backups (23/23 non-owned blocks byte-identical, 172 changed lines all model/models-key/context_length).
- [x] T6: PR #1200 opened, `make pr-message-check` OK, `make openspec-record-pr ISSUE=1198 PR=1200` archived the change at the PR head; pr-closure CI green.

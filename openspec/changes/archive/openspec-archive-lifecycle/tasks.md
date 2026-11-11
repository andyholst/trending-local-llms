# Tasks

- [x] 1. `scripts/openspec_archive_check.py` fails an ACTIVE change whose `PR:` names a merged PR, skips a change with no `PR:` line, ignores archived changes, and exits 2 (loud) when the GitHub read fails
- [x] 2. `make openspec-archive-check` exists and `qa-validate`'s `validate` job runs it with `pull-requests: read` + `GH_TOKEN` (rule 6d)
- [x] 3. `ARCHITECTURE.md` says when a change is archived (§8, `make openspec-archive` + `make openspec-index` in the PR that completes it) and names the new target, the script and the pipeline step (rule 6h)
- [x] 4. The six active changes whose PR is already merged (#173, #180, #189, #374, #379, #384) are archived, and `OPENSPEC.md` is regenerated so the archived table is no longer empty
- [x] 5. `tests/test_openspec_archive_check.py` locks each scenario with a stub `gh` on PATH and a real temp tree, and runs in `make test`
- [x] 6. `findings.md` records what this change found but did not fix, and `make findings-check` passes
- [x] 7. `make validate`, `make validate-mapped`, `make test`, `make architecture-check` are green and `make openspec-index` is current
- [x] 8. The `AGENTS.md` rule-6f sentence this change needs is quoted verbatim in `proposal.md` (the environment refuses writes to that protected file, so a human applies it)

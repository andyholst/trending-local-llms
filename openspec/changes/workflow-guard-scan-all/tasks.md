# Tasks

- [ ] 1. `scripts/check_workflow_guards.py`: scanner of ALL `.github/workflows/*.yml` — guard shape, caller-class execution of the real guard scripts, trigger-appropriate admission, `environment:` ban.
- [ ] 2. Makefile: `_check-workflow-guards` internal + public `check-workflow-guards`, bundled into the `lint:` recipe (wired where CI runs it).
- [ ] 3. `tests/test_workflow_guards.py`: real tree green + planted fixture trees red for every refusal shape.
- [ ] 4. `tests/test_workflows.py` rewired to import the scanner's GUARD_CALLERS/harness (one implementation, no second copy).
- [ ] 5. OpenSpec spec delta `specs/agents-guard-registry/spec.md` with one pinned test per scenario.
- [ ] 6. AGENTS.md §6j no-human-approval clause + stage naming; §8 guard row (rule 3c, declared on #816).
- [ ] 7. ARCHITECTURE.md §6 script row + `make architecture-refresh`; `make architecture-check` green.
- [ ] 8. Host suites covering the change green (`test_workflow_guards`, `test_workflows`, `test_makefile_only`, `test_architecture`, `make lint`, `make openspec-check`).
- [ ] 9. secret-scan + authorship green; PR opened with the five-section body closing #816; pipeline monitored to green.

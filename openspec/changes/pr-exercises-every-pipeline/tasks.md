# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `workflow_triggers()` reads `on:` (including YAML 1.1's bare `on` -> True)
- [x] 3. `coverage_problems()` refuses an uncovered pipeline, a stale entry and a missing module
- [x] 4. `DISPATCH_ONLY_COVERAGE` names all seven dispatch/schedule-only pipelines and their test
- [x] 5. The guard proves it can fail (unclassified + stale cases executed)
- [x] 6. Its first run found two gaps the issue had not named (publish-agent-image, refresh-bot)
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test` and `make openspec-check` green

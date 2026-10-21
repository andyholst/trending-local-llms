# Tasks

- [x] 1. The owner's ruling is recorded on #494 (both labels, re-check against the base, hourly, one issue)
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `QUEUE_LABELS` = data-gap-analysis + tech-debt; `_issues()` unions by number, oldest first
- [x] 4. `--label` accepts a comma/space list; ONE issue per run unchanged
- [x] 5. The reviewer keeps its own default (no silent switch-on for tech-debt bodies)
- [x] 6. The implement prompt requires the re-check against the fetched base
- [x] 7. `issue_verdict.parse` refuses prose-only `EVIDENCE:`
- [x] 8. Tests: three mock issues (implement / refine / close) + two refused-prose cases
- [x] 9. Tests: the two-label queue (both asked, deduped, one head)
- [x] 10. `make test`, `make lint`, `make architecture-check`, `make openspec-check` green; `OPENSPEC.md` regenerated
- [x] 11. `findings.md` written; the owed AGENTS.md rows filed as their own issue (protected file)

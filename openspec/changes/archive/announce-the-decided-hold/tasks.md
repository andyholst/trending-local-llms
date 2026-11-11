# Tasks

- [x] 1. The owner's ruling is recorded on #449 (human decision, announce — never expire)
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `bot_markers`: `issue-bot/verdict` registered (+ `WRITTEN`), parser learns the `<field>` shape
- [x] 4. The parser still reads `issue-bot-start` / `issue-bot-skip` / `issue-review` unchanged
- [x] 5. `issue_queue`: `decided_since` from the verdict marker, on the row and in the output
- [x] 6. `post_skip_note`: announces the decided hold, one comment per round, naming the human action
- [x] 7. `AGENTS.md` §6j table + prose
- [x] 8. Tests: the decided note (7 checks) plus the existing verdict-note suite
- [x] 9. `make test`, `make lint`, `make architecture-check`, `make openspec-check` green; `OPENSPEC.md` regenerated
- [x] 10. `findings.md` written (rule 6g)

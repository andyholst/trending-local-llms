# Tasks

- [x] 1. File issue #771 from the message pattern itself; write the OpenSpec change (`proposal.md` / `specs/message-pattern-enforcement/spec.md` / `tasks.md`).
- [x] 2. `scripts/pr_body.py`: `MESSAGE_SECTIONS`, `section_problems()`, `render()` emits the five sections before `Closes #<n>`, and `main()` gains `--check-body-file`/`--event`.
- [x] 3. `Makefile`: host `pr-message-check` target (mirrors `pr-closure`, `@`-silenced, `-n "$(PR_EVENT)"` guard).
- [x] 4. `.github/workflows/pr-closure.yml`: the `closure` job runs `make pr-message-check` after `make pr-closure`.
- [x] 5. `tests/test_pr_message.py` (standalone, no pytest import): composer matches the pattern; a body skipping/emptying/out-of-ordering a section is refused; `title()` is a Conventional-Commit naming the issue; the `--check-body-file` CLI refuses non-conforming and accepts conforming bodies.
- [x] 6. AGENTS.md message-pattern behavior (rule-3c note on issue #771) + `ARCHITECTURE.md` target row + regenerated §10 (`make architecture-refresh`).
- [x] 7. Gates green (host standalone tests, `make architecture-check`), `make openspec-index` + `make openspec-check`, then commit, push, open the PR (`closes #771`) — reviewable, never a draft, never merged here.

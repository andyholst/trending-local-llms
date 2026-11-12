# Tasks: agents-md-blocked-box-rule

- [x] 1. §6f names the blocked state beside "no unticked box" (`AGENTS.md` §6f sentence edited; verified: the sentence contains `- [~] … — blocked: <who/why>` and "never counted as done")
- [x] 2. §8's `tests/test_check_openspec_tasks.py` row names the annotation rule (blocked-with-reason passes and is reported; blocked-without-reason fails) — verified: the row carries both halves
- [x] 3. `make openspec-check` passes with the new change on disk (verified: openspec-check green in this branch's CI validate)

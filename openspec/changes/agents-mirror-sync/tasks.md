# Tasks

- [x] 1. Write the proposal + GWT capability spec for issue #696 (`agents-mirror-sync`: re-copy the in-tree fleet mirror from current host profiles, add the two new lanes).
- [x] 2. `agents/tll-planner/` — re-copy host `SOUL.md` + `skills/tll-planner/SKILL.md` from `/home/asimov/.hermes/profiles/tll-planner`.
- [x] 3. `agents/tll-architect/` — re-copy host `SOUL.md` + skill from `/home/asimov/.hermes/profiles/tll-architect`.
- [x] 4. `agents/tll-tester/` — NEW dir: add host `SOUL.md` + `skills/tll-tester/SKILL.md` from `/home/asimov/.hermes/profiles/tll-tester`.
- [x] 5. `agents/tll-reviewer/` — re-copy host `SOUL.md` + skill from `/home/asimov/.hermes/profiles/tll-reviewer`.
- [x] 6. `agents/tll-security/` — re-copy host `SOUL.md` + skill from `/home/asimov/.hermes/profiles/tll-security`.
- [x] 7. `agents/tll-implementer/` — re-copy host `SOUL.md` + skill from `/home/asimov/.hermes/profiles/tll-implementer`.
- [x] 8. `agents/tll-pr-rebase/` — NEW dir: add host `SOUL.md` + `skills/tll-pr-rebase/SKILL.md` from `/home/asimov/.hermes/profiles/tll-pr-rebase`.
- [x] 9. `agents/README.md` — fleet table gains the `tll-tester` (tests PRs against issue acceptance criteria, reports evidence) and `tll-pr-rebase` (rebases a conflicting PR onto master, does not merge) rows; all seven lanes listed.
- [x] 10. Verify each copied file byte-matches its host source modulo the repo-mandated final newline (`tll-tester` files lack a host trailing newline — the tree adds it, one-byte diff, content-identical); every copied file ends in a newline (`make lint-fix` last); `OPENSPEC.md` regenerated with `agents-mirror-sync` active; `make openspec-check` green.

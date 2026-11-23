# Tasks: pr-rebase-skill-push-verify-1427

- [x] Cut `fix/pr-rebase-skill-push-verify-1427` from the freshly fetched `origin/master` in its own worktree
- [x] Rewrite step 10 of `agents/tll-pr-rebase/skills/tll-pr-rebase/SKILL.md` as change/rebase locally, fast offline checks only, PUSH, confirm CI registered on the new SHA
- [x] Name the full `make validate`, the whole `make test`, closure and guard CI-ONLY, and keep the red-head rule as "CI red at your head means the rebase is not done"
- [x] Add `tests/test_fleet_lifecycle.py::test_pr_rebase_skill_is_push_and_verify` and wire it into the module's `main()`
- [x] Leave every `agents/*/SOUL.md` (including `agents/tll-pr-rebase/SOUL.md:53`) and `AGENTS.md` §7b/§8 untouched — rule 3c owns those halves
- [x] Regenerate `OPENSPEC.md` and keep the OpenSpec checks green (`openspec-index-check`, tasks, spec-test lines, binding, duplicate)
- [x] Run the fast offline checks (targeted module, `make lint`, `pr_body.py --check-body-file`) before pushing; the containerised `validate`/`test`/`live-smoke` stay in CI

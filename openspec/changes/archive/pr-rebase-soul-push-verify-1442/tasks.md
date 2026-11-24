# Tasks: pr-rebase-soul-push-verify-1442

- [x] Cut `fix/pr-rebase-soul-push-verify-1442` from the freshly fetched `origin/master` (`a73e448ab5e538da617e2a180a6a022ace2d092d`) in its own worktree
- [x] Declare the protected line (`agents/tll-pr-rebase/SOUL.md:53`) with its current text and intended replacement on issue #1442 BEFORE the write (rule 3c)
- [x] Rewrite `agents/tll-pr-rebase/SOUL.md:53` as the push-and-verify rule matching AGENTS.md §7b and the lane SKILL step 10 — fast offline checks only, PUSH, CI-registered confirmation
- [x] Name the full `make validate`, the whole `make test`, closure and guard CI-ONLY, keeping the red-head rule as "CI red at your head means the rebase is not done"
- [x] Leave every other `agents/*/SOUL.md`, AGENTS.md §7b/§8 and every schedule untouched
- [x] Add `tests/test_pr_rebase_soul_push_verify.py::test_pr_rebase_soul_is_push_and_verify` pinning the bullet
- [x] Regenerate `OPENSPEC.md` and keep the OpenSpec checks green (`openspec-index-check`, tasks, spec-test lines, binding, duplicate)
- [x] Run the fast offline checks (the targeted module and `make lint`) before pushing; the containerised `validate`/`test`/`live-smoke` stay in CI
- [x] Push with `--force-with-lease`, verify `headRefOid`, and report the head sha on issue #1442

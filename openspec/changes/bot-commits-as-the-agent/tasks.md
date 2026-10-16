# Tasks

- [x] 1. File the issue (#323) with the measured four `git config` sites and the canonical agent identity, and the rule-3c comment naming the `AGENTS.md` sections that change.
- [x] 2. Write the proposal + spec for the bot-commit identity.
- [x] 3. `.github/workflows/{fix-bot,issue-bot,refresh-bot}.yml`: all four committing sites set `git config user.name "Asimov Agent"` / `user.email "support@docondee.com"`.
- [x] 4. `scripts/check_commit_authorship.py`: `support@docondee.com` is an explicitly allowed identity (email) and the docstring names it.
- [x] 5. `tests/test_workflows.py`: the fix-bot assertion checks the identity's VALUE, and `test_every_committing_bot_job_commits_as_the_agent` pins every committing job in every workflow (and fails when it finds none).
- [x] 6. `tests/test_commit_authorship.py`: the agent's own identity is allowed by itself.
- [x] 7. Verified RED on the pre-change tree (13 failures in `test_workflows`, 1 in `test_commit_authorship`) and green with the change (625/0 and 29/0) — rule 6c.
- [x] 8. `make test`, `make openspec-check`, `make architecture-check`, `make lint`, `make secret-scan`, `make findings-check` green.
- [x] 9. The `AGENTS.md` wording (§2 rule, §8 row, §6b bullets) recorded in the proposal + PR body; filed as its own issue if the protected file refuses the write.
- [x] 10. Commit, push, open the PR (never merged by the agent).

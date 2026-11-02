# Tasks

- [x] 1. The tracked change exists (this dir) before any tree edit
- [x] 2. `agents/README.md` gains the `tll-tester` and `tll-pr-rebase` fleet-table rows
- [x] 3. `agents/tll-tester/{SOUL.md,skills/tll-tester/SKILL.md}` added, byte-copied from the host `tll-tester` profile (`cmp` verified)
- [x] 4. `agents/tll-pr-rebase/{SOUL.md,skills/tll-pr-rebase/SKILL.md}` added, byte-copied from the host `tll-pr-rebase` profile (`cmp` verified)
- [x] 5. Six existing lanes (`tll-planner`, `tll-architect`, `tll-security`, `tll-reviewer`, `tll-implementer`) re-synced byte-for-byte from their current host profiles (`cmp` verified each), replacing stale pre-#690 copies
- [x] 6. Docs-only, additive, non-breaking: no code, schema, data, workflow, cron, README, or GitHub Actions `schedule:` change
- [x] 7. `make openspec-check` green; change dir listed in `OPENSPEC.md` (index regenerated via `scripts/openspec_index.py --write`)
- [x] 8. `make lint-fix` run before commit; commit authored `Andy Holst <andy.holst@protonmail.com>`; commit-authorship OK; branch `fix/agents-mirror-696` ends `-696`
- [x] 9. PR title AND body carry `Closes #696` (single closing ref; refs #703/#704); `scripts/pr_closure.py --branch fix/agents-mirror-696` binds only #696; opened ready for review; never self-merge (qa-validate merges when validate + live-smoke are green at the head)

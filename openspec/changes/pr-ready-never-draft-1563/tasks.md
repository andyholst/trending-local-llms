# Tasks: pr-ready-never-draft-1563

- [x] 1. RED-first: add the draft tests to `tests/test_pr_health.py` and prove they FAIL on the
      fetched base `scripts/pr_health.py` (no `draft_findings`, no `--draft-only`, no wiring/rule)
- [x] 2. Extend `scripts/pr_health.py` (no rewrite) with pure `bound_issues`/`draft_findings`,
      the READY reason, `--draft-only`, the live draft verdict in both modes, and
      `closingIssuesReferences` in the `gh pr list` fields; keep findings/rebase/classify intact
- [x] 3. Wire `make pr-draft-check` through the Makefile and call it from the existing
      `pr-health.yml` `sweep` job before the full sweep; add no `schedule:` trigger
- [x] 4. State "Open every PR READY (never draft)" in both `agents/tll-planner/skills/tll-planner/SKILL.md`
      and `agents/tll-implementer/skills/tll-implementer/SKILL.md`
- [x] 5. Describe `pr-draft-check` and the new workflow step in `ARCHITECTURE.md` and regenerate
      its §10 inventory with `python3 scripts/architecture_bot.py --write`
- [x] 6. Register this change in `OPENSPEC.md` (`python3 scripts/openspec_index.py --write`)
- [x] 7. Fast offline checks green on the exact head: `python3 tests/test_pr_health.py`,
      `make lint`, `python3 tests/test_workflows.py`, `python3 tests/test_auto_merge_rebase.py`,
      `python3 scripts/architecture_check.py`, `python3 scripts/architecture_bot.py --check`,
      `python3 scripts/check_openspec_tasks.py`, `python3 scripts/openspec_index.py --check`
- [x] 8. Write `findings.md`, author as Andy Holst, commit, and push the branch; CI verifies

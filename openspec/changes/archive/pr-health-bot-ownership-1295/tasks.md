# Tasks: pr-health-bot-ownership-1295

- [x] Add `is_bot_owned()` with author-is-authoritative and prefix fallback to `scripts/pr_health.py`
- [x] Request `author` in the live `gh pr list` / `gh pr view` fields in both scripts
- [x] Use author-based ownership in `rebase_plan()` and `auto_merge_rebase.classify()`
- [x] Add pure RED-first guards for both directions, the fallback and the conflict rule
- [x] Replace the false prefix invariant in AGENTS.md §6s with the author contract
- [x] Regenerate `ARCHITECTURE.md` / `OPENSPEC.md` and run the focused tests, lint and gates

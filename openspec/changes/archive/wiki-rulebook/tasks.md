# Tasks: wiki-rulebook

- [x] Add the §7b bold-led bullet naming the architect's wiki-maintenance duty (daily CI check, weekly host cron, update false claims, archive obsolete with a dated marker, file an evidence issue, no invented values, generated artifacts untouched, ONE scheduled pipeline).
- [x] Append the ONE `Rule 3c note:` clause at the END of that line, re-read immediately before writing so no sibling clause is overwritten.
- [x] Add the §8 row before the closing prose, naming `tests/test_wiki_rulebook.py` and all three guard functions with the two-cell shape intact.
- [x] Write `tests/test_wiki_rulebook.py` with `test_architect_wiki_role`, `test_wiki_maintenance`, `test_wiki_rulebook`, each registered in `main()` and discovered by the `test_*.py` runner glob.
- [x] RED-first proof: run the three functions verbatim against the pristine base `AGENTS.md` (3 failures), then green on the landed tree (3 passes).
- [x] Write `findings/1773.md` with Evidence / Why / Done when.
- [x] Run `python3 tests/test_wiki_rulebook.py`, `make lint`, `python3 scripts/openspec_index.py --write`, `python3 scripts/check_openspec_tasks.py`, `python3 scripts/check_openspec_test_lines.py` and `python3 scripts/architecture_check.py`.
- [x] Push the branch and open the PR READY with `Closes #1773` in BOTH the title and the body; verify CI registered jobs on the head.

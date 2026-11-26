# Findings — #1767 (tll-planner lane)

## The §8 guard registry does not name the new parallel-dispatch source guard

- **Signature:** planner-parallel-dispatch-owed-section-8-row
- **Evidence:** this change adds `tests/test_parallel_planner_dispatch.py`, whose `test_the_guard_is_green_on_the_working_tree` passes on this head and whose `test_the_guard_is_red_on_the_fetched_base` reports all 10 contract clauses absent on the fetched `origin/master` `37c6d88150fdb73fd0583a59099aee0b418d7927`. `AGENTS.md` §8 carries no row for that module or for the up-to-3-concurrent-lanes/per-lane-bookend contract. AGENTS.md is rule-3c protected and is owned by the sibling lane on this issue, so this head does not write it.
- **Why:** §8 is the reviewer's map of what each guard proves. Without a row, a later edit could drop the parallel-dispatch contract from the planner skill while every registered guard stays green.
- **Done when:** the AGENTS.md owner extends the §8 guard row for `tests/test_parallel_planner_dispatch.py` so it names `test_the_guard_is_green_on_the_working_tree` and the "up to 3 concurrent lanes on DISTINCT open issues, each with query file / claim / worktree / lease-checked branch and a board-visible bookend" rule, citing #1767; `make owed-rows-check` then reports the row LANDED.
- **Owed-row:** <!-- owed-row: section=8 needle=test_the_guard_is_green_on_the_working_tree -->

## The planner SOUL mirror still teaches a single serial dispatch lane

- **Signature:** planner-soul-parallel-dispatch-mirror-owed
- **Evidence:** `agents/tll-planner/SOUL.md` on this head still carries `- Dispatch one lane at a time. The comment names the profile, ...` while the skill now carries the full `### Parallel implementer dispatch (owner directive, issue #1767)` contract. A write to the SOUL path was refused by the harness: `BLOCKED: write to protected agent-instruction file(s) (SOUL.md) was denied by the user ... Do NOT retry it or attempt the same edit via another path`. Issue #1767's body grants rule-3c sign-off for this change, but a headless lane cannot satisfy the harness approval prompt on its own.
- **Why:** a planner that reads its SOUL first and the skill second sees a serial rule above a parallel one, and may dispatch one lane at a time even though the operational skill permits three. The mirrors must say the same thing.
- **Done when:** an attended run, or the owner, lands in `agents/tll-planner/SOUL.md` the same parallel-dispatch section already present in `agents/tll-planner/skills/tll-planner/SKILL.md` (verbatim: the "up to 3 implementer lanes CONCURRENTLY against DISTINCT open issues" rule, the five one-per-lane clauses, the tech-debt/protected-rulebook owner-sign-off gate and the no-merge/no-master-push line), and replaces the stale serial bullet; the guard test in this PR then passes against the SOUL mirror too.

# Tasks — architect-wiki-role (issue #1773, architect role + guard slice)

- [x] Fetch `origin/master` immediately before the worktree cut; record sha `37c6d88150fdb73fd0583a59099aee0b418d7927` in the finding, guard and proposal
- [x] Add the wiki-freshness duty to `agents/tll-architect/SOUL.md` and `agents/tll-architect/skills/tll-architect/SKILL.md`, retaining the existing 'no cron / no workflow' sentences with an explicit amendment scoped to this duty
- [x] Apply the same duty to the two host profile copies under `~/.hermes/profiles/tll-architect/` (owner-directed host change; no other profile or host file touched)
- [x] Add `tests/test_architect_wiki_role.py` wired into `main()`: RED on the pinned base role text (exit 1), GREEN on the head (exit 0), host/tree halves agree
- [x] Write `findings/1773-architect-role.md` with Evidence / Why / Done when and a §8 Owed-row; `AGENTS.md` stays owned by the sibling rulebook lane (rule 3c)
- [x] OpenSpec change with proposal bound to `Issue: #1773`, capability spec with resolvable `- **Test:**` lines, and every task ticked
- [x] Regenerate `OPENSPEC.md` with `python3 scripts/openspec_index.py --write` and verify `--check` is current — never hand-edit the generated index
- [x] Compose the five-section PR body and check it with `scripts/pr_body.py`; both title and body carry `Closes #1773`
- [x] Fast offline gates green locally; containerised `make validate` / `live-smoke` are CI-only, checked on the pushed head

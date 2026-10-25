# Proposal — pr-fix names the OpenSpec gate

Issue: #560

## Why

fix-bot run 40177729642 burned all three rounds on one failure and pushed nothing:

```
[fix-loop] checks RED — failures:
[openspec-tasks] FAIL search-call-from-the-terminal: unchecked task checkbox(es) at lines [3, 4, …]
[agent] Input required; detached without cancelling. Resume this session interactively.
[agent] make: *** [Makefile:637: _fix] Error 3
[fix-loop] still RED after 3 fix round(s) — leaving for manual review
```

The `pr-fix` skill covers validation, contracts, links and the engine registry — and says nothing
about the OpenSpec gate, which is what the implementer's PRs fail on. Handed a failure it has no
instruction for, the agent asks, and asking detaches the run (rc=3). Before the skill seam the same
loop went `GREEN after 1 fix round(s)` (runs 40089753497, 40131596694); since then it has not
completed a round.

## What changes

`.hermes/skills/pr-fix/SKILL.md` gains a section naming each OpenSpec failure and its remedy — an
unticked checkbox (tick only what is genuinely done; otherwise say so in the PR body), a stale index
(`make openspec-index`), a change that does not validate (fix the spec), `openspec-archive-check`
(`make openspec-archive` + index) — plus the general rule: the check's own output IS the instruction,
and a check that names nothing actionable is reported, never turned into a question.

## Impact

- `.hermes/skills/pr-fix/SKILL.md` (the leg's contract — no make target, script, job or image moves).
- `tests/test_agent_skills.py::test_the_fixer_skill_names_the_openspec_failures` pins the text.

## What is NOT covered

- The model can still ask a question; the structural answer to that is the salvage path (#554) and
  the unattended contract (#549). This change removes the reason it had to ask about THIS failure.
- The loop's 3-round budget is unchanged.

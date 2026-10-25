# Proposal — agent-leg skills

Issue: #549
PR: #550

## Why

Every agent leg (four searches, the implementer, the two reviewer paths, the fixer) carried its
whole contract as one inline `hermes -z` string in the `Makefile`, and **nothing in it told the
model that nobody was watching**. `--yolo` approves shell commands and `--accept-hooks` approves
hooks; neither answers the agent's own `clarify` tool, so a run that asked a question printed

```
Input required; detached without cancelling. Resume this session interactively.
```

and exited **3** with the tree untouched. Measured on the issue-bot sweep: **three of five runs on
2026-10-24/25** (40151801003, 40144059829, 40139121556) died this way, and the pipeline could only
report "produced no implementation" — a wrong diagnosis that sends the reader to the data, the key
or the model alias, three things that were fine.

Two more costs of the inline shape:

- the same rules were restated per leg (and the search rules ×4), so a fix landed in one copy and
  not the others;
- a leg's contract could be deleted without any gate noticing, because nothing asserted it.

## What changes

1. **The contracts become Hermes project skills** — `.hermes/skills/<name>/SKILL.md`:
   `bot-unattended` (the shared unattended paragraph, written ONCE), `data-search`,
   `issue-implement`, `issue-review`, `pr-fix`. Each has `## Inputs` / `## Output` / `## Rules`,
   and its frontmatter `name` equals its directory (or `-s` cannot resolve it).
2. **Every leg preloads its skill and the unattended contract**: `-s <skill>,bot-unattended`. The
   inline prompt becomes a pointer plus that run's parameters (`issue.md`, `qa-report.txt`, the
   backend keywords, `$(ENGINE_ASK)`, `$(MODEL_QUERIES)`, the `--write-raw` command).
3. **The directory is registered, and the registration is proved**: `_setup` runs
   `scripts/hermes_skills_register.py` (through the Hermes CLI, because the repo's Python has no
   PyYAML) and reads it back with `--check`; a container where `-s` resolves nothing would run
   every leg with NO contract and still report success.
4. **`make check-agent-skills`** (`scripts/check_agent_skills.py`, part of `make lint`) fails a leg
   that preloads nothing, names a skill that does not exist, whose skill lost a required section or
   whose frontmatter name disagrees with its directory, a leg that inlines the unattended contract,
   a leg whose prompt grew past its pointer budget, and a `Makefile` that lost the seam or its
   registration target.
5. **Every workflow that runs a leg names rc=3** as "the agent asked for input", before its generic
   failure text — `issue-bot.yml`, and both `issue-review-bot.yml` paths.
6. The three tests that pinned the old inline text (`test_workflows`, `test_architecture`,
   `test_engine_registry`) now assert the SAME requirements against the skill the leg preloads,
   plus the preload itself.

## Impact

- `Makefile`: the seam block, `_hermes-skills-register` / `_hermes-skills-check` /
  `hermes-skills-register` / `check-agent-skills` / `agent-skills-report`, `_setup` registration,
  `lint` running the gate, and eight legs preloading a skill.
- `.hermes/skills/` (new), `scripts/check_agent_skills.py`, `scripts/hermes_skills_register.py`,
  `tests/test_agent_skills.py` (new).
- `.github/workflows/issue-bot.yml`, `.github/workflows/issue-review-bot.yml`: the rc=3 branch.
- `ARCHITECTURE.md`: two script rows, the new targets, the skills, and the regenerated §10 block.

## What is NOT covered

- **The `AGENTS.md` rule text is owed.** `AGENTS.md` is write-protected in this repo (the owner
  applies rule text), so rule **6p** — "every agent leg runs from a project skill, never from an
  inline rulebook — and an unattended leg never asks a question" — is written out in the PR body
  and must be applied by the owner. The gate therefore enforces the seam's own documented block in
  the `Makefile` (which this change can write) and `make agent-skills-report` prints whether
  `AGENTS.md` already states it.
- The search legs keep their keyword lists and the `$(ENGINE_ASK)` / `$(DIM_ASK)` expansions inline
  as parameters; only the shared rules moved into `data-search`.
- No change to what the legs are asked to DO — this is where the contract lives, not what it says,
  plus the one rule (never ask) that was missing from all of them.

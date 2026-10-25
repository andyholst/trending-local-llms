# Proposal — issue-bot salvage

Issue: #554

## Why

The unattended contract (`bot-unattended`, preloaded into every leg) forbids asking a question, and
that closed the measured rc=3 class — but a model can still call `clarify` **once**, and on the first
run after the seam landed it did so ~30 minutes in, AFTER implementing (run 40168796244):

```
[agent] Input required; detached without cancelling. Resume this session interactively.
[agent] make: *** [Makefile:1064: _implement-issue] Error 3
[verdict] implement
##[error]issue-bot produced no implementation for #362 (make implement-issue rc=2).
```

The job read any non-zero exit as "no implementation", so a finished change was discarded: `Commit +
push the branch` was **skipped**, no PR, no artifact. That is the same loss the repo already fixed
for a rejected push (#500) — 30 minutes of agent work thrown away with the ephemeral runner.

## What changes

- `issue-bot.yml` gains a **salvage** step after the implement leg: it reads the tree
  (`git status --porcelain`, which ignores the gitignored scratch files) and reports `dirty`.
- The commit/push step runs when the leg exited 0 **or** the tree is dirty; the "Fail loudly" step
  skips a salvaged run, so a detached run that left work behind is a reviewable PR, not a red run.
- The salvage step prints a notice naming the exit code, so the run page says why the work was kept.

## Impact

- `.github/workflows/issue-bot.yml` — one new step and two conditions.
- `tests/test_workflows.py` — a guard that reads the shipped step and EXECUTES it against a real git
  repo in both shapes (clean → `dirty=false`, changed → `dirty=true`).
- No make target, script, job or image changes, so `ARCHITECTURE.md` is unchanged.

## What is NOT covered

- A detached run whose tree is CLEAN stays red ("the agent asked for input"): there is nothing to
  salvage, and a green no-op over no work would be a lie.
- The salvage does not judge the change's completeness — CI and the fix loop do, and a human reviews
  the PR. A half-implemented salvage is a reviewable half, which is strictly better than a discarded
  whole.

# Proposal: tasks-gate-before-pr-open

Issue: #658
PR: #902

## Why

`make openspec-tasks-check` fails an ACTIVE change whose `tasks.md` still carries an
`- [ ]` box — but the implementer bot only meets that gate AFTER the PR is open, inside
qa-validate's `openspec-check`. Measured on PRs #654-#657: four bot PRs, each red on
`FAIL <change>: unchecked task checkbox(es)` for every box of the change they added,
while their `git diff --stat origin/master...HEAD` showed the change directory ONLY —
zero code, zero doc, zero test. No task in such a PR could have been true when it was
opened, the first CI run spent 19+ minutes discovering bookkeeping the author could have
measured for free, and `dispatch-fixbot` burned an LLM round on it. The gate already has
the right semantics (a NAME naming no active change FAILS, no NAME checks every active
change, `- [~] … — blocked:` is review-required not red); what is missing is WHERE it runs.

## What Changes

- `issue-bot.yml`'s implement job gains a step **after the agent implements and before
  Commit + push / Open the PR**: `make openspec-tasks-check` (no NAME — every active
  change on the branch). A change still carrying `- [ ]` boxes fails the step, which
  skips commit/push/PR-open and lands the red on the ISSUE through the existing
  always() outcome comment (rule 6e's "ready for review or red on the issue, never a
  silent skip").
- The gate is gated exactly like the push step (`verdict == 'implement'`), so a refine
  or close run — which opens no PR and adds no change — is unaffected.
- `tests/test_workflows.py` proves the step exists, sits after `make implement-issue`
  and before the commit step, calls the target through `make` (rule 6m), and shares the
  push step's implement gating.
- `tests/test_check_openspec_tasks.py` adds the vacuity proof: `NAME=<ghost>` (no such
  ACTIVE change) FAILS — an explicit NAME cannot pass by matching nothing.
- `.hermes/skills/issue-implement/SKILL.md` states the tick rule the gate enforces: a
  box is ticked only when the tree proves the step; an owed step is written
  `- [~] … — blocked: <who/why>` at creation (rule 6f), never left `- [ ]`.

## Impact

- Pipelines: `issue-bot.yml` (implement job step order; no new job, no new secret).
- Tests: `tests/test_workflows.py`, `tests/test_check_openspec_tasks.py`.
- Skill: `.hermes/skills/issue-implement/SKILL.md`.
- Data: none. Contracts: none. No new make target (`openspec-tasks-check` already
  exists and is already wired into `openspec-check`).

## Not covered

- The owner ruling for issue #650's shipped misattributed rows (a data decision, not a gate).
- The consent-seam behaviour issue #659 describes (a refine-held issue of its own).
- Any change to `scripts/check_openspec_tasks.py` semantics — they are already correct.

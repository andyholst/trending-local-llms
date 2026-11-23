# Proposal: land-host-ahead-skill-notes-1462

Issue: #1462
PR: #1463

## Why

`make fleet-host-sync-check BASE=origin/master` compares each host lane's skill bytes against the
fetched base. On the 2026-11-23 20:15 CET `M:` wake (master `bd2cc85d`) four lanes diverged on
`asimov@mac`: planner, reviewer, implementer and pr-rebase. Diffing each host file against the base
blob proved all four carry genuine forward experience notes absent from master, with no open PR to
land them. Wiping them to force the gate green would destroy forward work: the rulebook requires
landing such notes through a reviewed PR.

## What Changes

- `agents/tll-planner/skills/tll-planner/SKILL.md`: add the serialise-shared-files and
  don't-idle-in-prose notes, keeping every existing master rule.
- `agents/tll-reviewer/skills/tll-reviewer/SKILL.md`: add the emitted-recipe-stdout-poisoning note.
- `agents/tll-implementer/skills/tll-implementer/SKILL.md`: add the `git commit -F` comment-stripping
  and re-read-before-push notes, keeping the delivery-procedure and OpenSpec-lifecycle master rules.
- `agents/tll-pr-rebase/skills/tll-pr-rebase/SKILL.md`: add the 0-job `action_required`, owner-PAT
  measurement and §3 row-union notes.
- `tests/test_fleet_lifecycle.py`: register
  `test_second_batch_host_ahead_notes_are_landed` to pin the landed needles, kept master rules and
  the no-duplicate property.

## Impact

Mirror/docs only. The gate is unchanged; once merged and the host copies are re-synced,
`make fleet-host-sync-check` reports zero divergences on the four lanes. No make target, stage,
workflow, contract, image, data or AGENTS.md behaviour change.

## Not covered

- The pre-existing duplicate bullets on master's planner mirror (issue #1456) — a separate fix.
- Re-syncing the host profile home — the owner/planner runs it after this merges.

# Proposal: host-ahead-lane-skills-1745

Issue: #1745
PR: #1852

## Why

The three fleet lane skill mirrors in the repo lag the live host copies on `asimov@omarchy`. The owner authorised landing those host-ahead bytes in-thread (issue #1745, comment 7229469094), waiving the rule-3c approval wait for this one delivery. Until the exact text is tracked, `make fleet-host-sync-check BASE=origin/master` stays red on three files, and any re-provision from master would silently overwrite legitimate forward work with the shorter base text.

## What Changes

- Land the host bytes of `agents/tll-planner/skills/tll-planner/SKILL.md`: CI-only/render-readback, sha-measurement, bounded-RESUME, DIRTY re-cut, parallel-lane, chat-status, pr-closure invocation and PR-rebinding clauses, plus the recorded host notes that accompany them. The CI-only rule deliberately supersedes the base's local `--render-only --dry-run` probe.
- Land the host bytes of `agents/tll-implementer/skills/tll-implementer/SKILL.md`: the `master_alarm.py::GATES` registration clause and the cherry-pick replay clause. The branch-rename and PR-rebind paragraphs are relocated within the same file, not deleted.
- Land the host bytes of `agents/tll-reviewer/skills/tll-reviewer/SKILL.md`: the lane-SKILL-rewrite/cross-module guard clause and the escaped-backtick rule-3c clause.
- Restore the base's `#1115` issue reference in the planner's "no checks reported" pitfall, which the host rewrite dropped incidentally. No other base reference is removed.
- Add `test_host_ahead_lane_skill_clauses_are_landed` to `tests/test_fleet_lifecycle.py`, pinning one representative needle per landed clause family; it fails 13 checks on the base mirrors and passes on this head.
- Add this change, `findings/1745.md`, and regenerate `OPENSPEC.md`.

## Impact

Prose and one test only. No `SOUL.md` change (all eight already byte-match the base); no `AGENTS.md`, workflow, schedule, cron, data, README, schema or label change. The only supersession is the planner step-5 local render probe replaced by the CI-only readback rule; every other base line is preserved and the two implementer paragraphs are moved, not lost. Existing guards that read these skills stay green.

## Not covered

- No host profile provisioning — that is planner host maintenance after this PR merges.
- No merge, no master push, no CI dispatch, no collaborator grant, no Hermes cron and no GitHub Actions schedule.
- No other issue is touched; this PR closes only #1745.

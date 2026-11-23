# Proposal: land-host-ahead-skill-notes-1418

Issue: #1418
PR: #1422

## Why

`make fleet-host-sync-check BASE=origin/master` compares every host lane's `SOUL.md`, skill and
`config.yaml` byte-for-byte against `git show <fetched base>:agents/<lane>/<rel>`. Two lane skills ran
ahead of master with an appended `## Host notes ahead of master (asimov@mac, <timestamp>)` section:
the planner's holds the lane-concurrency bound (#1416), the never-started-head rule (#1115), the
"do not wipe runtime stamps" rule (#1401) and the master-push-supersedes-a-filed-failure rule
(#1412/#1413); the implementer's holds the five-section PR body requirement, the merge-tree OpenSpec
index race (#1239), the branch force-push / 0-job head recovery (#1398/#1115), the `--yolo` versus
`approvals.single_query_mode` seam, the bare `make <target>` master-alarm routing and the
re-read-the-PR-live-state rule. These are real lessons, not drift to discard: the remedy is to LAND
them through a reviewed change and then re-sync the host, never to delete them locally and mask the
gate.

## What Changes

- `agents/tll-planner/skills/tll-planner/SKILL.md`: the four host-ahead rules are merged into the
  existing `## Pitfalls` list, keeping their issue references and dropping the host timestamp header
  and machine name.
- `agents/tll-implementer/skills/tll-implementer/SKILL.md`: the six host-ahead rules are merged into
  the existing `## Pitfalls` list, keeping every issue reference and the `scripts/pr_body.py` /
  `scripts/master_alarm.py` pointers.
- `tests/test_fleet_lifecycle.py::test_lane_skill_mirrors_carry_landed_host_ahead_notes` proves both
  mirrors carry the reconciled notes inside their own `## Pitfalls` section, keep their issue
  references, and carry no host timestamp header, host timestamp or machine name.
- No `config.yaml` byte changes — that half stays with #1401.

## Impact

Mirror/docs only. The gate itself is unchanged; once the host profile is re-synced from the merged
tree, `make fleet-host-sync-check BASE=origin/master` reports 0 divergences on the two lanes. No make
target, stage, workflow, contract, image or data change.

## Not covered

- The `config.yaml` runtime-stamp tolerance (#1401) — a separate PR.
- Re-syncing the host profile home — the owner/planner runs it after this merges.

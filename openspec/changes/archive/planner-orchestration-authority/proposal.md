# Proposal: planner-orchestration-authority

Issue: #1398
PR: #1406

## Why

The owner directed on 2026-11-23 that the `tll-planner` lane has **full authority to orchestrate and
delegate**: the planner STARTS the other lanes itself instead of waiting for the owner on the host, and
runs the commands needed to move the board. That authority lived only in this host's session context,
and a fleet-sync on `da86387c` reverted the host-only edit — measured: `~/.hermes/profiles/tll-planner/`
`SOUL.md` and `skills/tll-planner/SKILL.md` were again byte-identical to `agents/tll-planner/...`. For the
behaviour to survive a host sync and reach the other machine it must land in the reviewed tree.

The earlier leg of #1398 also measured a hard boundary: `security.protected_instruction_files=true`, so
EVERY write to a basename `SOUL.md` needs human approval and a headless lane cannot self-approve
("Silence is not consent"). `agents/tll-planner/SOUL.md` is therefore OUT of this change; the behaviour is
procedural, and the planner's skill is its natural home.

## What Changes

- `agents/tll-planner/skills/tll-planner/SKILL.md` gains a Procedure section, "Starting a lane (owner
  directive 2026-11-23)", recording the directive with its mechanism and its guardrails:
  - starting a lane is `env -u HERMES_HOME -u HERMES_SESSION_PROFILE hermes -p <lane> chat --query-file
    <file> --oneshot`, launched with `terminal(background=true)` and monitored with `process_manage`;
  - delegation is STILL by a signed dispatch comment on the issue thread — post the comment first, then
    start the lane;
  - the planner still NEVER writes the tree and NEVER merges (`tll-implementer` writes, `qa-validate`
    merges green);
  - there is still no cron and no Actions schedule — the directive changes who starts the lanes, not the
    cadence.
- The same section carries the pitfalls: pass `--yolo --accept-hooks` or the lane hits
  `approvals.single_query_mode: deny` on `git push --force`; check the owner's checkout with `git status`
  after a lane run (a lane's shell cwd is not automatically its worktree); a lane runs 30–70 min.
- `tests/test_planner_orchestration_authority.py` reads the REAL skill file and asserts the directive and
  every guardrail survive — no mocks, no stand-ins (rule 6m). It is discovered by the ONE runner
  (`scripts/run_tests.sh`), so `make test` executes it.

## Impact

Skill text plus one guard module. No make target, stage, workflow, contract, data, store or image change;
`make fleet-host-sync-check` keeps comparing the lane bytes, so the host copy must be re-synced from this
tree after the change lands (the same seam that reverted the earlier host-only edit). The owner's checkout
is untouched; the lane works in a worktree cut from the freshly fetched `origin/master`.

## Not covered

- `agents/tll-planner/SOUL.md` — a protected agent-instruction file (rule 3c); a headless leg records the
  owed section in `findings.md` instead of writing it.
- Any change to who merges, to the dispatch-comment protocol, or to the cadence: the planner still never
  writes the tree and never merges, and no timer is added.
- Any other lane's `SOUL.md` or skill.

# Proposal: architecture-bot-write-path

Issue: #485 — arch-bot: the drift→commit→PR path has no behavioural test

## Why

`architecture-bot.yml` was merged (#483) with its WRITE path covered only by string
assertions over the YAML — `"steps.drift.outputs.changed == 'true'" in wf`,
`"%Y%m%dT%H%M%SZ" in wf`, `"Closes #" not in wf`. Its first production dispatch
(run 39520010157) exercised only the no-op half: the block already matched, so the
`changed=false` branch ran and the commit/push/PR branch has never executed.

That is the shape rule 6c forbids: a grep over a workflow cannot see a
`$GITHUB_OUTPUT` line corrupted by `make`'s own echo (#346), a branch stamp that
lost its `Z`, a commit made under the wrong identity, or a body that grew a
closing keyword that `pr-closure` would refuse. `tests/test_workflows.py::
test_fix_bot_push_behaviour` already runs a shipped step in a temp clone for
exactly this reason.

## What Changes

- `tests/test_architecture_bot.py` gains `test_the_shipped_steps_actually_commit_push_and_open_a_pr`:
  the `id: drift` step and the commit/push/PR step are read **out of the workflow
  file** with PyYAML (so the test cannot drift from what CI runs), then EXECUTED in
  a temp git repo with a real bare local remote, the repo's own
  `make git-identity` seam (`scripts/agent_identity.py`) and a stub `gh` on `PATH`
  standing in only for the network (rule 6m).
- It asserts the no-op half (`changed=false`, no branch, `gh` never called) and the
  drift half (`changed=true`, exactly one `ci/architecture-<UTC>Z` branch, the
  canonical author, `gh pr create --base master --head <branch> --body-file -`, a
  body carrying the run URL and **no** closing keyword), and asks
  `scripts/pr_closure.py`'s own regexes whether the branch name encodes an issue
  instead of re-spelling that rule.
- The three string assertions it subsumes are removed, not duplicated.

## Impact

Tests only: no workflow, Makefile, data or README change, so `make test` stays the
single gate and no image is rebuilt. The test is skipped (not passed) where PyYAML
is absent, matching the other YAML-reading modules.

## Not covered

- The `git push` auth path in CI (the PAT's `workflows` scope): the fixture pushes
  to a local bare remote, which is the real `git` but not GitHub's authorization.
  A rejected push still fails the job loudly, as before.
- The guard job and the `base-check`/refresh/check steps: covered structurally in
  `test_wired_into_the_makefile_the_guard_and_the_pipeline` and executed in
  production run 39520010157.

# Proposal: findings-check-shape-gate

Issue: #1454

## Why

Rule 6g makes the analysis artifact (`findings.md`) MANDATORY for every
implementation run, but the only gate that enforces it — `make findings-check` —
runs on the bot pipelines (`issue-bot`, `issue-review-bot`) and in the fix loop
when `REQUIRE_FINDINGS=1`. The fleet's normal delivery is a DIRECT worktree PR,
and `qa-validate` never called the check, so a PR could be green on `validate`
and `live-smoke` while its analysis was absent (measured: this worktree's
`make findings-check` exits 1 with `findings.md is missing`).

Wiring the bare `make findings-check` into `qa-validate`'s `validate` job is
refused by the architect's Option-A ruling: it would red EVERY keeper, refresh,
docs and architecture PR whose tree carries no `findings.md` — the repo-wide
blockage §6q exists to prevent. The gate must be SHAPE-AWARE.

A second, non-obvious half: `findings.md` is gitignored AND on the bot
never-stage list (`scripts/issue_bot_working_files.txt`), so `actions/checkout`
of a PR head never carries it. Enforcing a gate on a file CI cannot see is a
no-op, so the analysis must become a reviewed artifact of the head.

## What Changes

- `scripts/pr_closure.py` gains `NON_IMPLEMENTATION_BRANCHES` (the declared
  exempt prefixes) and `implementation_shaped(branch, body)`, built ONLY from
  the parser's existing derivations — `implemented_issue(branch)`, a closing
  binding, or an `implement #<n>` claim in the body's first line (code quotes
  stripped by `visible_text`). An exempt prefix WINS over any claim. No second
  parser (rule 6d).
- New host target `make findings-check-for-pr`: the same
  `scripts/file_findings.py --check`, plus optional `--event` / `--branch` /
  `--body-file`. With no inputs it behaves exactly as `findings-check` does
  today, so the bot paths are untouched.
- Wired where CI actually decides: ONE new step in `qa-validate.yml`'s
  `validate` job, immediately after `make pr-closure`, reading
  `$GITHUB_EVENT_PATH` by PATH. Also added to `scripts/fix_loop.sh`'s `CHECKS`.
- The analysis becomes visible to CI: `findings.md` leaves `.gitignore` and
  `scripts/issue_bot_working_files.txt` (with its same-change test updates), so
  an implementation head carries it and the gate is self-enforcing.
- Regression tests drive the REAL CLI: an implementation-shaped head with no
  `findings.md` goes RED; every exempt shape stays GREEN; a push event is a
  green no-op; a quoted claim is not a claim.

## Impact

Additive. No schema, contract, data shape, table, image or schedule change. A
`pull_request` run of an exempt shape (keeper, refresh, docs/rule) is a green
no-op; a `push` to `master` or a `workflow_dispatch` has no `pull_request` and
is a green no-op, so the §6q repo-wide-red hazard cannot occur. Implementation
PRs now owe the artifact the rulebook already demanded.

## Not covered

- No change to `pr-closure`'s existing refusal rules, `make pr-message-check`,
  or any other gate.
- No model call, no CI dispatch, no merge, no `master` push, no collaborator
  grant.
- No AGENTS.md write: the rule-3c rows the design owes are recorded as a
  blocked task box plus an owed-row finding, never written by this headless leg.

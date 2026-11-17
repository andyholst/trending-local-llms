# Proposal: rebase-pushes-with-owner-pat

Issue: #1115

## Why

`make auto-merge-rebase` (qa-validate's pre-squash gate, issue #1049) pushes its
rebased branch head through the checkout's `origin` remote — which carries the
`github-actions` **job token** — and the push is what GitHub treats as the event
that schedules CI on the new head. Measured on issue #1115: the rebased heads of
runs `43763984964` / `43772291016` carry **0 jobs** (`jobs_total: 0`,
`run attempt_number 2`): a workflow scheduled from the SAME `github-actions`
identity it would run as is NOT created, so the PR shows no checks forever,
`auto-merge` waits for checks that will never exist, and the queue deadlocks.
`make pr-health` (#818) hit the same wall for the same reason: its rebases also
push through the job-token checkout, and its OWN runs are created with 0 jobs —
the quietest failure in the repo, invisible to every alarm that watches runs.

## What Changes

- `scripts/pr_health.py::rebase_and_push` gains `pat_push_url(...)`: when the
  step provides `GIT_PUSH_PAT` and `origin`'s RAW configured URL is a GitHub
  HTTPS remote, the push goes to the same remote rewritten with the owner PAT
  (`https://oauth2:<pat>@github.com/<owner>/<repo>.git`); the transport alias is
  resolved with `git remote get-url`'s insteadOf rewriting in mind (the RAW
  `config --get remote.origin.url` is read, never the rewritten one). The commit
  and the `--force-with-lease` semantics are unchanged; without the PAT the push
  stays on `origin` exactly as today (host sweeps, local fixtures).
- Every push names the identity it used in the seam's output:
  `push identity: owner-pat` or `push identity: checkout-credential`.
- qa-validate's `auto-merge-rebase` step and pr-health's rebase-sweep step
  provide `GIT_PUSH_PAT: secrets.FIXBOT_DISPATCH_TOKEN` (the owner PAT the repo
  already uses to OPEN PRs, so the rebased head's CI is scheduled by a human
  identity and really runs). Their READS keep the default `github.token`.
- New alarm half: `scripts/ghost_run_alarm.py` + `make ghost-run-alarm`, run by
  `queued-alarm.yml` with the DEFAULT token (read-only): it flags a concluded
  `pull_request`-triggered run of a main pipeline that carries ZERO jobs —
  `action_required` with nothing scheduled, or `success` with nothing run — the
  #1115 shape no other alarm can see (a 0-job run concludes without any job to
  alarm on). Exit 1 names the ghost runs so the sweep goes RED.

## Impact

- `scripts/pr_health.py` (ONE rebaser, rules 6d/6s), `scripts/auto_merge_rebase.py`,
  `scripts/ghost_run_alarm.py` (new), `tests/test_auto_merge_rebase.py`,
  `.github/workflows/qa-validate.yml`, `.github/workflows/pr-health.yml`,
  `.github/workflows/queued-alarm.yml`, `Makefile` (`ghost-run-alarm` target),
  `ARCHITECTURE.md`, `AGENTS.md` §6s/§6l + §8 row.
- Pipeline contract: a rebased head re-triggers CI as the OWNER (a human-identity
  push), so `auto-merge`'s "rebased=true → CI on the new head lands it" promise
  becomes mechanically true instead of silently broken.

## Not covered

- The `dnm-check`/`pr-closure` pipelines' own token policy (unchanged).
- A human-owned behind branch is still only REPORTED, never rebased (rule 6s
  partition unchanged).
- No new labels, no marker changes, no cadence changes (rule 6t: queued-alarm
  stays dispatch-only, qa-validate still runs tests/validators only).

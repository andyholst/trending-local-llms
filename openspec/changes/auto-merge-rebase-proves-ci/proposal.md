# Proposal: auto-merge-rebase-proves-ci

Issue: #1616

## Why

#1115 ("auto-merge-rebase pushes its rebased head with the job token — that head's CI is created
with 0 jobs and never runs") is CLOSED, but the exact shape recurred twice on 2026-11-24 and cost
two manual owner-identity re-pushes: PR #1607 head `d6232184` → qa-validate run 45419443908
`action_required` with `jobs=0`, PR #1608 head `ac1b65a7` → run 45419383942 the same. §6s
already mandates the PAT push (`push identity: owner-pat`), so the push credential is no longer
the open question — the missing half is the PROOF. A seam that pushes and prints a green line is
not evidence that anything scheduled the merge gate.

## What Changes

- `scripts/pr_health.py`: after a successful rebase push to a github.com origin, read the pushed
  sha's OWN `qa-validate.yml` run back through the ONE gh field contract
  (`verify_rebased_ci`, built on `gh_json_fields.request`) and report the rebase as verified only
  when that run carries >0 jobs. A bounded poll (60 s) covers the scheduler's normal lag; a
  matched run with zero jobs (the #1115 ghost), an unreadable/wrong-shaped jobs answer, or no run
  for that exact sha inside the window is UNVERIFIED — never a guess, and never another sha's run.
  `rebase_and_push` now returns `(pushed, ci_verified, message)`; `ci_verified` is None for a
  non-github origin (a local fixture has no GitHub run to read).
- `scripts/auto_merge_rebase.py`: `verdict=rebased` — the one that makes the squash step skip —
  is reported ONLY on that proof. A push that landed without scheduling real CI prints
  `verdict=ci-unverified`, leaves `rebased=false` (the #1184 head-moved gate still skips the
  stale squash) and exits 1, naming the zero-jobs run.
- `scripts/pr_health.py`'s `run_rebaser` (the `pr-health REBASE=1` sweep path, §6s) holds the same
  contract: an unverified push is reported `REBASED but CI UNVERIFIED: …`, not as a clean rebase.
- Regression guards in `tests/test_auto_merge_rebase.py`: the REAL seam against a stub remote and
  a planted run list FAILS when the rebased head's run has zero jobs, proves the healthy direction
  reports `rebased=true`, and proves a wrong-shaped gh answer is UNPROVEN rather than proof.

## Impact

No data format, contract, image, target, workflow-trigger or schedule change. The push identity
(`GIT_PUSH_PAT` → `owner-pat`) and the `--force-with-lease` semantics are unchanged; only the
report is now backed by a read of GitHub's own run. `ci-unverified` makes the `auto-merge` job red
on a head nothing scheduled — self-healing, because the push itself fires a fresh qa-validate run
whose own `auto-merge` then sees a current branch and merges it. Host sweeps that rebase a PR gain
one bounded gh read per rebased branch.

## Not covered

- No change to `ghost_run_alarm.py` (it stays the repo-wide detector of the same shape), to the
  queued-alarm sweep, or to any workflow trigger. No new make target, pipeline job, cron or
  collaborator grant. No rulebook rule change: `AGENTS.md` gains only the §8 regression-guard row
  this change's test module already owns.

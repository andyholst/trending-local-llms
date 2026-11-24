# Proposal: rebase-step-ci-diagnosis-1646

Issue: #1646
PR: #1665

## Why

The qa-validate `auto-merge-rebase` step ran `OUT=$(make auto-merge-rebase …)` under
`set -euo pipefail`. When the seam failed, the shell died AT the assignment, so the step's
`printf '%s\n' "$OUT"` never ran and the seam's own diagnosis never reached the job log —
the step was red with nothing to read (measured on PR #1631, whose rebase runs
`45453080984`/`45462716032` sat `action_required` with zero jobs while no lane could say why).

The second half is a claim problem, not a credential problem (rule 6v puts the PAT itself out
of scope). The step printed `push identity: owner-pat` from a local variable, and an operator
read that as "checks will run". Measured through GitHub's OWN REST run record, a push made
inside the job is attributed to `github-actions[bot]` — whichever token rode in — while only a
push made from outside the runner with a real account credential is attributed to a User
(`asimov-agent`). The two classes were never distinguished in the output, so the issue #1616
premise ("push through the PAT schedules real CI") read as true when it is not.

## What Changes

- `.github/workflows/qa-validate.yml`: the `auto-merge-rebase` step captures the seam's exit
  status beside the command (`OUT=$(make …) || SEAM_RC=$?`), always echoes the seam's own
  output, and only then exits with that status. errexit is never disabled.
- `scripts/pr_health.py`: add ONE pure classifier `classify_push_identity(actor_login,
  actor_type)` (`checkout-credential` for a Bot actor, `owner-pat` for a User of this
  repository, `unknown` otherwise) and `read_run_identity(repo, run_id)`, which reads
  `actor.login`/`actor.type`/`triggering_actor.login` from the REST run endpoint
  (`gh run view --json` answers no actor field at all). `verify_rebased_ci` and
  `rebase_and_push` now carry the matched run's id and the PROVED identity next to the
  intended one; the pr-health sweep outcome records both.
- `scripts/auto_merge_rebase.py`: every landed push prints the actor/triggering_actor
  GitHub recorded, the credential class it proves, the class the local push claimed, and a
  machine-readable `push_identity=` / `push_identity_intended=` / `push_identity_proved=`.
- `tests/test_auto_merge_rebase.py`: RED-first guards — the shipped step shell executed with
  a planted failing seam, the pure label selection, the real identity read against a stub
  `gh`, and the end-to-end seam on the PR #1631 shape.

## Impact

No data format, contract, image or workflow-trigger change. The rebase verdict, the squash
skip and the head-moved gate behave exactly as before; the step only LOSES silence. Nothing
about `FIXBOT_DISPATCH_TOKEN`, its scopes, any secret, or any collaborator/access setting is
touched (rule 6v). A push that still yields a zero-job run remains `ci-unverified`/exit 1 —
this change makes that state legible and attributable instead of guessed at.

## Not covered

- Fixing the credential path itself (an owner act under rule 6v).
- Editing `AGENTS.md` §6s so its PAT-push sentence matches the measurement — carried as an
  owed rulebook row with the exact sentence named, not landed here.
- Any new pipeline schedule, cron, or merge-path change.

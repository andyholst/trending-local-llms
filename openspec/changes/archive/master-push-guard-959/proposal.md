# Proposal: master-push-guard-959

**Issue:** [#959](https://github.com/andyholst/trending-local-llms/issues/959) —
PR: #966
"Rule 1 (never push master) has no mechanical guard — master has zero branch
protection and direct pushes land today"
**Capability:** `master-push-guard`

## Why

AGENTS.md Rule 1 forbids pushing `master` directly, but nothing enforces it:
`gh api repos/andyholst/trending-local-llms/branches/master/protection` answers
404, and on 2026-11-14 two commits (`e571aa3`, `4c7c555`) landed on `master` as
**direct pushes** committed by `Mr. Asimov <support@docondee.com>` — not by
`GitHub <noreply@github.com>`, which is what every real squash merge shows. A
working session under time pressure took the direct path because nothing refused
it. Rule 1 today is a convention that holds only while every actor remembers it.

## What Changes

- **Repository setting (owner-approved act, not a code change):** `master` gains
  branch protection via the FULL-OBJECT PUT (fine-grained-PAT quirk: per-setting
  subresources 404 — a measured fact, recorded in memory):

  ```json
  {
    "required_status_checks": {
      "strict": true,
      "contexts": ["qa-validate / validate", "qa-validate / live-smoke"]
    },
    "enforce_admins": true,
    "required_pull_request_reviews": null,
    "restrictions": null
  }
  ```

  These are the exact checks `auto-merge` already gates on, so the pipeline's
  merge path is the path protection admits; a direct push is refused by GitHub.
- `scripts/check_branch_protection.py` — the guard: reads master's protection
  (live `gh api`, or a recorded JSON fixture via `--from-file`) and refuses
  (exit 1) when protection is absent, `strict` is not true, a required context
  (`validate`, `live-smoke`) is missing, or `enforce_admins` is not true; an
  unreadable read is exit 2, never a silent clean.
- `make check-branch-protection` (public target) wired as a step of the weekly
  `queued-alarm.yml` sweep (the scheduled-pipeline half the issue names), using
  `secrets.FIXBOT_DISPATCH_TOKEN` — the owner PAT, since the default
  `github.token` cannot read branch-protection state.
- `tests/test_branch_protection.py` — the real script against planted recorded
  protection shapes (external system only: `gh` is not mocked; fixture mode is
  the recorded-fixture seam rule 6m allows) plus the wiring (target + step).
- `ARCHITECTURE.md` §6 script row and the target group; `AGENTS.md` Rule 1,
  §6b `queued-alarm` bullet, §8 guard-table row (rule 3c disclosure posted on
  the issue).

## Not covered

- Applying the protection setting itself — a repository-settings act that
  requires the owner's approval (issue #959 says so explicitly); the guard PR
  lands the detection half, and the Done-when proof (a direct push REFUSED, a
  green PR still auto-merging) runs right after the owner applies it.
- Protecting any other branch; no workflow, data key or existing target changes.

## Impact

Rule 1 becomes mechanical: every commit on `master` provably passed
`validate` + `live-smoke` on its head; a silently-removed protection turns the
weekly `queued-alarm` run red instead of quietly restoring the unguarded state.

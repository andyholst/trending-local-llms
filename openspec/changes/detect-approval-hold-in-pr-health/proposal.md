# Proposal: detect-approval-hold-in-pr-health

Issue: #1123 (filed with a live measurement)

## Why

The pr-health sweep (issue #442) reads the **count** of check runs on each open PR's head
commit. A head commit whose runs all concluded `action_required` has runs — so the sweep calls
it healthy — but GitHub executed **zero jobs**: it is holding the branch's own workflows for a
collaborator's approval. That hold lands on exactly the PRs that edit `.github/workflows/`
while their head commit's author identity GitHub maps to an outside contributor. The PR then
sits with `gh pr checks` empty, `mergeStateStatus=UNSTABLE`, no jobs, no alarm — the third
silence. Measured: **PR #1116** (head `b10716488d`, 2026-11-17): `qa-validate` run 44037397846
and the `pr-closure` run both completed `action_required` with zero jobs; the sweep ran over it
several times and reported nothing; the PR carries the merge-queue identity fix itself (#1115).

## What Changes

- **`scripts/pr_health.py`** — a third reason, kept apart from the two existing ones:
  `approval_hold(total_runs, held_runs)` is true when a head commit HAS runs and EVERY one of
  them is `action_required`. `findings()` gains an optional `holds_for` map (the pure decision,
  rule 6d); `main()` collects `conclusion` alongside `databaseId` (limit 100) and counts held
  runs. The flag comment for a held PR names the human remedy — approve the pending runs
  (Actions tab → Review pending workflows → Approve, or `gh api -X POST
  repos/…/actions/runs/<run-id>/approvals`) — and NOT the rebase hint, because a hold is not a
  stale base. Approving is a collaborator's act (rule 6t): the sweep announces, never acts.
- **`tests/test_pr_health.py`** — three new tests (held PR flagged with its own reason; held
  vs ran PRs separated; the hold comment names the approval remedy, rule 6t, and no rebase
  hint; dedup preserved), the gh-stub harness now answers `run list` with conclusions.

## Impact

- Capability: `pr-health` (one ADDED requirement).
- Affected: `scripts/pr_health.py`, `tests/test_pr_health.py`, `ARCHITECTURE.md` (§6 row +
  generated inventory, stale because the script's docstring changed — issue #947),
  `AGENTS.md` §8 guard table row (rule 6c).
- No new make target, no workflow change, no contract change: the existing `make pr-health`
  (report-only) and the weekly sweep step gain detection, not wiring. `--rebase` behaviour is
  unchanged.

## Not covered

- Making GitHub not hold such PRs in the first place (authoring workflow-editing bot PRs as
  the owner identity) — named in the issue as the possible follow-up; this change only makes
  the hold LOUD.
- Approving held runs automatically — forbidden by rule 6t; the comment names the human step.

# Proposal: pr-health-unverified-rebase-red

Issue: #1647 — "an unverified `pr-health REBASE=1` sweep exits green, so a stuck rebased head
PR: #1653
never reddens the sweep" (filed by tll-reviewer from its PR #1631 review at head `460f7100`).

## Why

`scripts/pr_health.py::main` ended `if not silent: return 0` — the scheduled sweep's exit code
read ONLY the silent-PR verdict. Issue #1616 added the other half of the fact: `run_rebaser`
now reports a pushed branch whose own new head did not schedule real CI as
`REBASED but CI UNVERIFIED: …` with `ci_verified: False`. But that outcome was PRINTED and
never CONSULTED, so `make pr-health REPO=… COMMENT=1 REBASE=1` still exited GREEN over a round
that had just moved a bot branch onto a 0-job head.

Measured by the reviewer on the real script over a github-shaped fixture whose planted run is
`{"jobs": []}`: the log says `rebaser #7 … REBASED but CI UNVERIFIED: … ZERO jobs`, and the
process exits `0`. A green scheduled sweep is read as "nothing needs a human"; here it silently
leaves a branch on a head GitHub will not validate — the exact state the owner twice repaired by
hand (PR #1607/#1608) — and the only later signal is the silent-PR half rediscovering it one
round and one deadlocked `auto-merge` later.

## What Changes

- `scripts/pr_health.py`: a pure decision `unverified_rebases(outcomes)` (the mirror of
  `failed_rebases`) selecting exactly the outcomes carrying `ci_verified is False`, plus a
  named `UNVERIFIED_REBASE_REASON`. `main` consults it after the rebaser half prints: any such
  outcome REDS the sweep (`exit 1`), naming each affected PR and its head, with the reason.
  The module docstring's exit-code contract states the second red.
- `tests/test_pr_health.py`: one end-to-end guard driving the REAL script against a REAL bare
  origin + clone (only `gh` is stubbed — rule 6m). It plants a behind-and-clean `ci/` bot branch
  whose pushed head's OWN `qa-validate.yml` run carries ZERO jobs and asserts the sweep exits 1,
  NAMES `#7`/`ci/data-gap-1647-x`, and says the rebase is not a completed repair; then the same
  fixture with a run carrying real jobs asserts the sweep stays GREEN. The PR is NOT silent in
  either shape, so the red is attributable to the unverified verdict alone.

No workflow edit, no Makefile change: the `pr-health.yml` sweep already runs
`make pr-health … REBASE=1`, so the exit code propagates unchanged. A verified rebase, an
already-current branch, a refused/human/conflicted branch and a failed rebase are all untouched.

## Impact

- Active rules: 6d (the decision is a pure seam in the script), 6c (a test that fails on the
  pre-change tree — proven: 3 FAILs against `origin/master`'s `scripts/pr_health.py`),
  6r/6s (the §6r sweep keeps its promise: the round cannot call an unproven push a repair).
- Data: none. Pipelines: `pr-health.yml` sweep only, through the existing target.

## NOT covered

- Making the CI-step PAT push actually SCHEDULE jobs (owner credential scope, filed as #1646).
- The auto-merge gate's own zero-job proof (#1616, merged) — this change only reads its verdict.
- Announcing the unverified round on the PR thread: the existing `--comment` half already
  announces FAILED rebases (#964); an unverified-but-pushed head is a different shape and is
  left to the sweep's red, deliberately out of scope here.

# Proposal: record-the-pr-on-a-change

Issue: #518 — `tech-debt: Most active OpenSpec changes carry no PR reference, so the lifecycle guard cannot see them`
PR: #753

## Why

The OpenSpec lifecycle (AGENTS.md rule 6f) ends a change in the PR that completes
it: once its `PR:` line is known, that PR runs `make openspec-archive` and
`make openspec-index`, so the change reaches `archive/` with the index
regenerated. `scripts/openspec_archive_check.py` is the guard that enforces the
END — but it only asserted the lifecycle **where a `PR:` line exists**. A change
written without one — every change created before #183, plus every change whose
author did not know its PR number at authoring time — was merged and forgotten
while the guard reported a vacuous "none names a PR".

Measured on `master` when #183 landed: `grep -l '^PR: ' openspec/changes/*/proposal.md`
printed 6 while `OPENSPEC.md` listed 115 active changes; after archiving those
six, 110 active changes remained and none named a PR. The index's active count
overstated in-flight work for 110 of 111 changes — a completed change and an
unfinished one looked identical.

The fix has two halves, and both must land together:

1. **Recording is part of the workflow that opens the PR.** Once `gh pr create`
   has returned a number, the implementer bot writes `PR: #<n>` into every
   ACTIVE change whose proposal references the issue, and regenerates the index
   — so from now on no change reaches a merge without its completing-PR
   reference exposed to the guard.

2. **The guard stops being blind to issue-only changes.** A change whose `Issue:`
   references a CLOSED issue (its work ended when the completing PR merged it)
   with no `PR:` line ever recorded is now a FAILURE, not a "nothing to assert".
   The guard reads behavioral state through the SAME `gh` seam it already
   uses for PR merged-ness — one more API read, no new machinery.

## What Changes

- **`scripts/openspec_archive_check.py`** grows a second prong: for an active
  change with an `Issue:` ref but no `PR:` line, it queries the issue's state via
  `gh api repos/<o>/<r>/issues/<n>` and FAILS when closed, naming the change, the
  issue and the `make openspec-archive NAME=<change>` remedy. A change that names
  a PR is owned by the PR prong, whichever way its issue sits. A change with no
  ref at all is still "nothing to assert".
- **`scripts/openspec_record_pr.py`** (new) + **`make openspec-record-pr
  ISSUE=<n> PR=<m>`**: write `PR: #<pr>` into every ACTIVE change whose proposal
  references `Issue: #<n>` (through the SHARED `openspec_index._refs` parser, rule
  6d), MOVE those changes to `openspec/changes/archive/`, then regenerate
  `OPENSPEC.md`. REFUSES (exit 2) when no active change names the issue, so a
  recording that silently matched nothing can never leave the guard vacuous
  again.
- **`.github/workflows/issue-bot.yml`**: after the PR is opened, a step runs
  `make openspec-record-pr`, so the completing PR carries its own reference.
- **`openspec_index._refs`** reads BOTH spellings of the header — the bare
  `Issue: #170` and the bolded `**Issue:** [#170](url)` many later changes used —
  so the guard can see every issue, not only the oldest format.
- **qa-validate** grants the validate job `issues: read` (the guard now reads
  issues as well as pull requests).
- **The current backlog is archived** in this same change: the ~110 active
  changes whose issues are closed are moved to `openspec/changes/archive/` (the
  established remedy the guard teaches), so the strict guard is green after the
  change instead of red over a merged-and-forgotten pile. Additive only: no
  change is deleted or rewritten, only moved.

## Impact

`scripts/openspec_archive_check.py`, `openspec_index.py`, `Makefile` (two
targets), `.github/workflows/qa-validate.yml` (permission), `.github/workflows/
issue-bot.yml` (one step), `scripts/openspec_record_pr.py` (new), `OPENSPEC.md`
(regenerated), ~110 change directories moved to `archive/`, `ARCHITECTURE.md`,
`AGENTS.md` §8, new/updated tests and this change.

## Not covered

- **Backfilling PR numbers for the archived backlog.** The archive move does not
  need a PR number, and inventing one would be fabrication (rule 2). The guard's
  purpose is to make the missing reference LOUD so it is never forgotten again,
  not to guess what it was.
- **Archiving a change whose issue is still open.** Only changes whose issue is
  genuinely closed are moved; in-flight (open-issue) changes stay active.

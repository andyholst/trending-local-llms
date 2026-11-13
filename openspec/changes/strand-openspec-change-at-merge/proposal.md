# Proposal: strand-openspec-change-at-merge

Issue: #866
PR: (recorded by `make openspec-record-pr` on this PR's final commit)

## Why

Rule 6f closes the change lifecycle at the PR: `make openspec-archive-check
PR=<n>` (issue #779) refuses a merge while an ACTIVE change's `Issue:` is one
of the PR's closing issues — but only `while the change names no PR:`. That
escape hatch is exactly the shape every stranding this month took: a closing
PR records a `PR:` line (hand-written or recorded) and merges with the change
STILL ACTIVE, so the check goes green on the PR, red on the master push, and
an unrelated keeper PR must archive it. Measured five times: #777, #781, #851,
#862 (keeper PRs #775/#781/#851/#871) and PR #889 → keeper #892, PR #891 →
keeper #893 — each time every open PR's `validate` blocked behind the inherited
red until the keeper merged.

`make openspec-record-pr` already records AND archives in one call; the gap is
purely the gate's `PR:`-line exemption, which lets a half-recorded change
through.

## What Changes

- `scripts/openspec_archive_check.py`'s closing-PR prong drops the exemption:
  any ACTIVE change whose `Issue:` is one of `--pr`'s closing issues fails the
  check **whether or not it names a `PR:` line**. The head that merges must
  already hold the archive (`make openspec-record-pr ISSUE=<issue> PR=<pr>`
  records and archives in one call), so auto-merge can only arm on a head that
  lands its own change archived. A merged-but-active change cannot survive a
  cycle.
- `tests/test_openspec_archive_check.py` flips the old "names this PR passes"
  scenario (it asserted the exemption) to the new contract and adds the
  self-archive pass case (rule 6b).
- `AGENTS.md` §6f states the reconciled contract: self-archive on your own
  closing PR is the REQUIRED shape; archiving a change this PR does NOT close
  stays refused (issue #812's protection is untouched — it guards fix rounds
  dismantling a change mid-branch, not the required final archive).
- §8 gains the guard row for the strengthened prong (rule 6c).

## Impact

- Capability: `archived-change-lifecycle` (one ADDED Requirement).
- Gates: `make openspec-archive-check` (qa-validate `validate` job, every PR)
  — stricter; every closing PR must now land its own archive before merge.
- No data, no Makefile target changes; `openspec-record-pr` behaviour is
  unchanged (it already archives).

## Not covered

- The #812 `fix_loop.sh` refusal (an open fix round archiving prematurely)
  remains its own open issue — this change only states the boundary between
  the two rules.
- Existing already-archived stranding repairs (#892/#893 keepers) are done;
  nothing to backfill — `make openspec-archive-check` against the real tree
  is green.

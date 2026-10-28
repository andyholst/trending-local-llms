# Proposal: issue-queue-branch-hold

Issue: #647

## Why

AGENTS.md rule 6j's hold (a) says an issue is held from the implementer by "an
existing `ci/data-gap-<n>-*` branch or an open PR from one". It has never
matched. `scripts/issue_queue.py::_branches` reduced every ref the API returned
to its LAST path segment, so `refs/heads/ci/data-gap-417-tech-debt-…` became
`data-gap-417-tech-debt-…`, while `build()` compares it against
`f"{BRANCH_PREFIX}{number}-"` = `ci/data-gap-417-`. `branch` was therefore always
`None`, `has_implementer` always `False`, and the open-PR half
(`pull = … if branch else None`) was unreachable as well — the branch it was
derived from could never exist.

Measured in production (`scripts/issue_queue.py:223`, `:281`, `:284`): run
40610814947's pick logged "#417 is the head of the pick order (35 candidate(s))"
at 00:46:06Z while PR #643 was open on
`ci/data-gap-417-tech-debt-the-search-legs-write-hugging-` (pushed 00:42). The
implement job then pushed a DUPLICATE `feat(data-gap): implement #417` commit
(`eddc5d2`) onto that PR's branch and died at "Open the PR" — a whole second
implementation of an issue that was already implemented, blocked only by luck
(the branch-adopt seam and a failing `gh pr create`), not by the queue.

Nothing failed loudly: `_gh(check=False)` answers `""` for a failed read and the
queue parsed that as "no branch exists", so an unreadable hold and a genuinely
held issue were indistinguishable.

The tests could not catch it: every case in `tests/test_issue_review.py` answers
the ref read with `branches.json = []`, so the branch comparison never executed —
and the fixture's shape was a list of strings while the API answers a list of
`{"ref": …}` objects (rule 6m: a stand-in that cannot reproduce the system's
shape locks nothing).

## What Changes

- **`scripts/issue_queue.py::_branches`** keeps the full short ref
  (`refs/heads/` stripped, `ci/…` intact), which is what `build()` matches and
  what `repos/{repo}/commits/{ref}` accepts. A bare `data-gap-…` is not a ref.
- **A failed ref read is LOUD**: an empty answer prints one
  `[issue-queue] WARN:` on stderr naming the branch read and the hold it
  degrades, and the queue still runs — the other holds are unaffected, and a
  sweep must not die on a diagnostic.
- **`tests/test_issue_review.py`** gains the two cases that lock both halves, in
  the API's real shape: an issue whose `ci/data-gap-<n>-*` branch exists is NOT a
  candidate while its neighbours still are; and a `gh` that fails the ref read
  still answers, warns on stderr, and never puts the warning on the
  machine-readable stdout. The `gh` stub grows the control hook both need
  (`fail-refs.txt`), and `env_for()` the `refs_fail` flag.

## Impact

`scripts/issue_queue.py`, `tests/test_issue_review.py`, the `ARCHITECTURE.md` row
for `scripts/issue_queue.py`, a §8 guard row in `AGENTS.md`, this OpenSpec change
and `OPENSPEC.md`. No `data/**` change, no workflow change, no new make target:
the queue's ONE implementation already runs in both bots (`make issue-queue`,
`make issue-pick`).

Behaviour is strictly a NARROWING of what a sweep may pick up: an issue with an
existing implementer branch or an open PR from one is now skipped, exactly as
rule 6j states. An issue with neither is offered exactly as before.

## Not covered

- **The PR half of the hold when the branch read fails.** `pull` is derived from
  the matched branch, so an unreadable ref list still hides an open PR; the new
  WARN makes that state visible but does not close it. Filed as a finding
  (`findings.md`) rather than widened here.
- **A `gh pr list` window.** `_pulls` reads `--state all --limit 100`; a repo
  with more PRs could miss the open one. Filed as a finding.
- **Why the duplicate implementation still landed a commit.** The issue-bot path
  that pushed `eddc5d2` resumes the branch and only then attempts `gh pr create`;
  with the hold working, that path is no longer reached for an issue that already
  has a PR, so this change does not touch it.

# Proposal: issue-queue-open-pr-predicate

Issue: #1310

## Why

`make issue-queue` is the ONE shared queue the implementer bot reads to pick the oldest unclaimed actionable issue. Its `has_implementer` predicate only recognised a `ci/data-gap-<n>-*` branch and a PR whose `headRefName` equalled that branch. An agent-owned PR cut as `fix/`, `feat/` or `rule/` was invisible, so an issue already in review was offered as `next-sweep` to the next run — measured live with PR #1289 (`fix/pr-block-grace-derived-1176`, one `closes #1176`) and issue #1176 printed as `position=2 has_implementer=0 reason=next-sweep`.

## What Changes

- `scripts/issue_queue.py::_pulls` reads each PR's `body` in addition to the existing fields.
- A new `_closes_issue` helper asks the repo's ONE closure parser (`scripts/pr_closure.py::closing_bindings`, through `visible_text`) whether a PR binds a closing keyword to the issue.
- `build()` marks an issue as having an implementer when ANY OPEN PR closes it, regardless of `headRefName`, while keeping the prefixed-branch path and folding the closing PR's timestamps into the reported implementer activity.
- `tests/test_issue_queue_predicate.py` drives the real queue against a stub `gh` and the real parser; it is RED on the base script and green on the fix.

## Impact

No contract, data format, workflow, image or make target changes. The queue only gains a second implementer signal; the reviewer's window and verdict holds are untouched. A PR that merely mentions an issue without a closing binding stays claimable.

## Not covered

- No change to `pr_health.py`'s rebase ownership predicate (#1295) — that is the sibling's separate work item.
- No issue is closed, no PR merged, no CI dispatched, no master push, no owner ruling decided.

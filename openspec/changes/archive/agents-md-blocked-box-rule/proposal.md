# Proposal: agents-md-blocked-box-rule

Issue: #635
PR: #849

## Why

`AGENTS.md` §6f describes `make openspec-check` as "every active change
validates, no unticked box, the index is current" — but after issue #409 the
gate has a third state: a `- [~] … — blocked: <who/why>` box is ACCEPTED and
reported as review-required, while a `- [~]` box with no reason FAILS. The
rulebook therefore describes a gate narrower than the one CI runs, and §8's
`tests/test_check_openspec_tasks.py` row names neither new check. A reader of
the rulebook would tick a blocked step as done — exactly what the blocked
state exists to prevent.

## What Changes

- §6f names the blocked state in the same sentence as "no unticked box":
  blocked boxes must be reported (`- [~] … — blocked: <who/why>`, a
  review-required change, never counted as done).
- §8's `tests/test_check_openspec_tasks.py` row gains the two blocked-box
  checks: blocked WITH a reason passes and is reported as review-required;
  blocked WITHOUT a reason fails (the annotation rule).

## Impact

- `AGENTS.md` only (rule 3c: this diff is review-required — the PR is the
  review surface; the issue states exactly which sections change and why).
- No script, no Makefile target, no contract changes; the gate's behaviour is
  already implemented and tested by `scripts/check_openspec_tasks.py` and
  `tests/test_check_openspec_tasks.py` (issue #409), which this change aligns
  the rulebook to.

## Not covered

- The blocked-box gate itself (#409, already merged) — this change only makes
  the rulebook describe it.
- Any further §6f prose reorganization.

# Proposal: wiki-rulebook-1773

Issue: #1773
PR: fix/wiki-rulebook-1773

## Why

PR #1774's `validate` job reds on the `OpenSpec lifecycle` step because no OpenSpec change names Issue: #1773. The completing PR closes issue #1773, yet nothing in `openspec/changes/` records a change bound to that issue, so the lifecycle guard (`scripts/openspec_archive_check.py`, a hard step of `qa-validate`'s `validate` job, rules 6f/#518/#779) cannot see the work behind the issue it closes, and the PR cannot merge.

## What Changes

- Create a new active OpenSpec change at `openspec/changes/wiki-rulebook-1773/` binding Issue: #1773 and PR: fix/wiki-rulebook-1773.
- Add the change's capability spec (`specs/openspec-lifecycle/spec.md`), its task checklist (`tasks.md`, one checked box), and `.openspec.yaml`.
- Regenerate the root index `OPENSPEC.md` via `make openspec-index` (never hand-edited) so the change is listed as active and the index counts it.

## Impact

Additive only. The change lands on top of PR #1774's tree — no data format, contract, workflow, Makefile or test change. It makes the OpenSpec lifecycle guard see the work behind Issue: #1773 and clears the `validate` job's lifecycle step for PR #1774.

## Not covered

- No change to `scripts/openspec_archive_check.py`, the archive workflow, or `openspec-record-pr`; recording/ archiving the completed change follows its own tracked lifecycle (issue #518) and is out of scope here.
- No deletion of any change or value (rule 3b — additive only).

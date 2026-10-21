# Proposal: openspec-archive-lifecycle

Issue: #183

## Why

Rule 6f requires a tracked change for every piece of work (proposal, capability
spec, ticked `tasks.md`) and `OPENSPEC.md` lists every change active and
archived — but **nothing says when a change stops being active**. Measured on
`master` when this change was written:

- `grep -rn "openspec-archive" AGENTS.md` returns nothing: the rulebook never
  mentions the target that ends a change's life, although `make
  openspec-archive` exists (`Makefile:279`).
- `OPENSPEC.md` renders an "Archived changes" table that has **0** rows while
  **115** changes sit in "Active changes", and `openspec/changes/archive/` is
  empty — no target, workflow or rule ever moves a change into it.
- Six of those active changes name a `PR:` that GitHub reports as **merged**
  (`gh api repos/andyholst/trending-local-llms/pulls/173` → `merged_at`
  2026-10-14T19:48:57Z; likewise #180, #189, #374, #379, #384), so the index's own
  count is not a measure of in-flight work: a merged change and an unfinished one
  look identical.

The lifecycle has an end state that nothing reaches. A checklist that is never
archived grows into a wall of "active" changes, and a reviewer cannot tell what
is still moving.

## What Changes

- **The lifecycle says when a change is archived**: in the PR that completes it,
  after its `PR:` line is known, the same PR runs
  `make openspec-archive NAME=<change>` and `make openspec-index`, so the change
  moves to `openspec/changes/archive/` with the index regenerated in one commit.
  That timing is documented in `ARCHITECTURE.md` §8 (the life of a change), and
  the matching `AGENTS.md` rule-6f sentence is quoted below for a human to apply
  (this environment refuses writes to `AGENTS.md`: it is a protected
  agent-instruction file). Archiving is a data/description move, not a merge
  action: the bot never merges (rule 6e).
- **A guard asserts the lifecycle** — `scripts/openspec_archive_check.py`
  (`make openspec-archive-check`, run by `qa-validate`'s `validate` job): every
  ACTIVE change whose `PR:` line names a **merged** PR fails, naming the change,
  the PR and the two commands that fix it. An archived change is not checked
  (its life is over), a change with no `PR:` line is not guessed about, and a
  GitHub read that fails is LOUD (exit 2) instead of a silent pass.
- **The six already-merged active changes are archived in this change**, so the
  guard is green on merge and the "Archived changes" table stops being empty.

### The AGENTS.md rule-6f sentence (blocked here, needs a human)

Append to rule 6f, after the `make openspec-index-check` sentence:

> **A change also ENDS**: in the PR that completes it — once its `PR: #<n>` line is
> known, after the PR is opened and before it merges — that same PR runs
> `make openspec-archive NAME=<change>` and `make openspec-index`, so the archive
> and the regenerated index land in one commit. A change left ACTIVE after its PR
> merged is a defect: `make openspec-archive-check` fails it (exit 2, never 0,
> when the PR state cannot be read), and qa-validate's `validate` job runs it with
> `pull-requests: read`.

## Not covered

- **The `AGENTS.md` rule-6f edit itself**: the file is a protected
  agent-instruction file in this environment and writes to it are refused, so the
  exact sentence is quoted above and a human must apply it. The behaviour is
  documented and enforced either way (`ARCHITECTURE.md` §8 + the guard).
- Backfilling a `PR:` line for the ~109 active changes that have none: their PR
  state cannot be established from the change directory, so the guard cannot see
  them. Recording the PR is part of the reference workflow, and the gap is filed
  as its own issue (rule 6g).
- Deciding that an abandoned change (its PR closed without merging) must be
  archived or deleted: this change only asserts the merged case.
- Applying a change's spec deltas into `openspec/specs/` on archive — the CLI's
  `archive` also merges specs; here the archive is the directory move the
  Makefile documents, and the delta-application gap is filed as its own issue.

# Keeper branches are references, not implementations

**Issue:** [#872](https://github.com/andyholst/trending-local-llms/issues/872)
**Capability:** `pr-lifecycle`

## Why

`scripts/pr_closure.py::implemented_issue()` reads a branch's TRAILING number as "the
issue this branch implements" (the `ci/pr-closure-284` convention), and the keeper PRs
the pipelines land — the archive keeper, the index keeper, the architecture keeper — are
routinely cut named after the issue whose RUN surfaced the drift. The two conventions
collide structurally: a keeper PR is by definition a repair observed during issue N's
run, not an implementation of issue N.

Measured (issue #872): PR #867, branch `ci/archive-stranded-cadence-wording-866`, run
43285662684, died at the first cheap gate in 9 s —

```
[pr-closure] REFUSED: ci/archive-stranded-cadence-wording-866 implements #866 —
1 problem(s): the branch implements #866, but no closing keyword binds to it
```

Unblocking needed a **manual branch rename** (`ci/archive-stranded-cadence-wording`,
PR #871) — a human-shaped act repeated at every recurrence. The alternative is worse:
writing `Closes #866` to satisfy the gate would be a FALSE claim, since #866's
Done-when (keeper job + AGENTS.md §6f reconciliation + a test) is not implemented by an
archive move.

## What Changes

- `scripts/pr_closure.py` declares the **keeper branch shape** `ci/keeper-<slug>[-<issue>]`
  (rule 6d: the shape lives in ONE place, next to the parser that reads it).
  `implemented_issue()` returns `None` for it — the trailing number is a REFERENCE —
  while every other branch keeps the existing convention unchanged.
- The existing rule "a PR that implements no issue must not close one" then guards the
  dishonest shape for free: a keeper branch that writes `Closes #N` is REFUSED.
- `tests/test_pr_closure.py` fails on the planted collision from #872: a keeper branch
  naming a still-open issue PASSES with zero closing keywords; the measured #867 branch
  (no keeper token) still demands a binding; an implementer branch `ci/data-gap-<n>-…`
  still MUST bind `Closes #n`.
- The `issue-implement` skill names the convention at the point the agent picks the
  branch: implementation branches keep the issue binding; a PR that only records or
  unblocks drift lands as `ci/keeper-<slug>` or `ci/keeper-<slug>-<issue>` with
  `refs #N` in the body and NO closing keyword.

## Impact

- `scripts/pr_closure.py` (the ONE closure implementation), `tests/test_pr_closure.py`,
  `.hermes/skills/issue-implement/SKILL.md`, `AGENTS.md` §6e (one clause naming the keeper
  shape — rule 3c: review-required, announced by comment on #872), `OPENSPEC.md` (regenerated).

## Not covered

- The keeper-PR landing seam itself (the three hand-written copies) is issue #869, and
  the recurring archive-keeper job is issue #866 — this change makes their branch naming
  legal, it does not build those jobs.
- Existing keeper branches already merged are untouched; no data or contract key moves.

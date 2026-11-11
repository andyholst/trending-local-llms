# Proposal: engagement-tasks-claim

Issue: #699 (follow-up) — correct the residual false "typed README byte-identical" claim in the
merged `measurement-store-normalized` change's `tasks.md`.

## Why

PR #700 landed the value-fidelity guard, corrected the `measurement-store-normalized`
`proposal.md` and the spec scenario, and regenerated the README. However the **same change
dir's `tasks.md` line 10 still read `README.md byte-identical`** on master — the exact
false claim the #699 dispatch named. `openspec-check` only validates that task boxes are
ticked, not their wording, so the stale statement shipped on master while the proposal
around it was corrected. This is a doc-fidelity defect of the same class #699 prohibited.

## What Changes

- `openspec/changes/measurement-store-normalized/tasks.md` line 10: replaces
  `` `README.md` byte-identical `` with a disclosure that the README is regenerated from
  the flattened view and its engagement-derived buzz/trend lines are re-resolved from the
  canonical `data/posts.json` (the intended GWT2 consequence, corrected on issue #699) —
  not claimed byte-identical.

## Impact

Docs-only, non-breaking, additive. One line in the merged change's task list corrected to
tell the truth it already claimed was the proposal/spec's job. No code, no schema, no data,
no README regeneration (the README is already the regenerated artifact). Green under
`make openspec-check`, `make lint` and the test suite.

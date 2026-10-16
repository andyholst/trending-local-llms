# A pipeline (or an agent) never opens a draft PR

**Issue:** [#276](https://github.com/andyholst/trending-local-llms/issues/276)
**Capability:** `pr-lifecycle`

## Why

`qa-validate`'s `auto-merge` job requires a non-draft PR (`.github/workflows/qa-validate.yml:190`,
`github.event.pull_request.draft == false`), and `tests/test_workflows.py:628` pins that — on the
**merge** side only. Nothing forbids a run from **opening** a draft, and `AGENTS.md` invited the
mistake: rule 2.1 promises every change is auto-merged once `validate` + `live-smoke` are green and
rule 6e promises an implementation "ends in a monitored, green, squashed PR", but the rulebook never
says which duty wins when a run wants to hold a change for review.

Measured: PR #272 (issue #271) was opened as a draft for exactly that reason — "rule 3c wants a
reviewer's sign-off first" — and a draft is *valid, green and permanently unmergeable*: no job can
land it, `dispatch-fixbot` and `auto-merge` both key on the `pull_request` event, so the fix loop can
run, repair and go green while the change still cannot merge. The run's own promise ("green, squashed
PR") becomes unreachable, silently.

The review duty of rule 3c does not need a draft: the PR **is** the review, GitHub's required checks
are the gate, and `auto-merge` only merges on green — so holding a change is never what a draft
achieves; it only disables the only mechanism that can land it.

## What Changes

- **`AGENTS.md` rule 6e** (review-required per rule 3c — the disclosure comment on the issue names
  it): the PR an implementer or `refresh-bot` opens is **ready for review, never a draft** — a draft
  is excluded by the merge gate, so the run would end with work that can never land; and the §8 row
  for `tests/test_workflows.py` names the new guard.
- **`tests/test_workflows.py`**: every `gh pr create` in every workflow must NOT carry `--draft`,
  and the PR-opening step of the two branch-cutting pipelines (`refresh-bot`'s `aggregate`,
  `issue-bot`'s `implement`) is asserted to be a non-draft creation — complementing the existing
  merge-side assertion (`auto-merge: never a draft PR`), so both halves of the contract are locked.

## Impact

None on the data, the ranking or the store: this is the pipeline's own lifecycle. A change can no
longer be parked in a state that looks complete and cannot merge, and the "review" that rule 3c asks
for is the reviewable PR itself.

## Not covered (out of scope — separate issues)

- Whether GitHub's branch protection also requires an approving review (a repo setting, not code).
- #273: `auto-merge` can still squash a PR onto a `master` it was never validated against — the
  other half of "the merge gate must actually mean green on this tree".

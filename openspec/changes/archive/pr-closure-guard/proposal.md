# A merged PR always closes the issue it implements

**Issue:** [#284](https://github.com/andyholst/trending-local-llms/issues/284)
**Capability:** `pr-lifecycle`

## Why

The rulebook promises it twice — rule 6e: "**opens the PR** (`closes #<issue>` …)", and the change's
own contract "PR (closes #<issue>)" — but the only thing asserted anywhere is a marker word:

```python
# tests/test_workflows.py:705
check("issue-bot: the PR closes the issue", "closes #" in pr_run, pr_run[:200])
```

That cannot see either way the promise breaks, and both were measured in this repository:

**A chained reference closes only the first issue.** GitHub binds a closing keyword to the ONE
reference that follows it; it does not enumerate a list. PR #272's body said
`Closes #271 and #276` — #271 closed on merge, **#276 did not**. The change was in `master`, the
issue stayed open, and no check noticed. The shared bot queue (`scripts/issue_queue.py`: "oldest open
`data-gap-analysis` issue with no implementer") would then offer an issue whose work already landed,
and the next run would implement it a second time. A silently-open issue is worse than a red run:
every dashboard says the work is done.

**A PR can close an issue it does not implement.** `refresh-bot.yml`'s refresh PR body ended with
`Closes #1` — the *CI pipeline meta issue*, closed since 2026-09-28 — while the commit message for
the same run correctly said `Ref: #1`. If #1 were ever reopened, the next refresh would close it.

The PR body is the only artifact in the pipeline whose whole purpose is "this merge closes that
issue", and the only one with no guard on its content.

## What Changes

- **`scripts/pr_closure.py`** — the ONE implementation (rules 6d/6m): reads the head branch and the
  body from the webhook payload **by path** (`--event "$GITHUB_EVENT_PATH"`, so nothing is ever
  interpolated into a `run:` block — that would be a script-injection vector), derives the issue the
  branch implements (`ci/data-gap-<n>-<slug>`, taking its FIRST number so the title slug's digits
  cannot win; `ci/trending-refresh-<UTC>` implements none), and refuses three shapes: a closing
  keyword whose clause chains a second reference, a branch issue with no keyword bound to it, and a
  closing keyword on a PR that implements no issue. Code is not a claim: a keyword inside a
  fenced block or an inline code span is ignored, because GitHub links nothing there — measured on
  this change's own PR, whose only `Closes #284` sat in backticks and produced an EMPTY
  `closingIssuesReferences`, which a naive parse read as a binding and would have passed.
- **`make pr-closure`** — the seam CI and a human share (`PR_EVENT=…` in CI, `BRANCH=… BODY_FILE=…`
  by hand), wired into `qa-validate`'s `validate` job with the other cheap, image-free gates.
- **`AGENTS.md` rule 6e** (review-required per rule 3c, disclosed on the issue): a PR's body closes
  the issue it implements, **one closing keyword bound to that issue**, and a PR whose branch
  implements no issue closes none — the refresh PR *references* its tracking issue. Plus the §8 row.
- **`.github/workflows/refresh-bot.yml`**: `Closes #1` → `Refs #1`, so a refresh PR stops carrying a
  closing keyword for the meta issue.
- **`tests/test_pr_closure.py`** (in `make _test`): the two measured bodies are refused, the
  correct forms pass, the branch-issue derivation is pinned (the slug's numbers cannot win), every
  GitHub closing keyword is recognised, and the CLI is driven over real event payload files — plus
  the wiring (Makefile target, `_test` chain, the CI step, the payload read by path).
- **`ARCHITECTURE.md`** (rule 6h): the script and the new `validate` step.

## Impact

Only the PR lifecycle: no data, no store, no ranking. A PR can no longer merge green while leaving
the issue it claims to implement open, and the next run cannot be offered the same work again.

## Not covered (out of scope — separate issues)

- A PR that closes an issue belonging to ANOTHER repository (`Closes owner/repo#12`) — this repo has
  a single repository per pipeline, so cross-repo references are recognised as references but not
  resolved to an issue.
- **A body edit does not re-run this check.** `pull_request` fires on `opened`/`synchronize`/
  `reopened` by default, so a body corrected after the last push is validated only on the NEXT push
  (measured on this change's own PR, whose `validate` evaluated the previous body). The normal flow —
  push the branch, then create the PR with its final body — is covered; the hole is a body EDITED
  after the last push, and it is filed as its own finding rather than widened here.
- Whether the issue's `data-gap-analysis` label is removed on merge (the queue already skips an
  issue with an open PR or a closed state).

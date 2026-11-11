# Proposal: pr-body-closure-guard

Issue: #289 — `tech-debt: The weak marker-word assertion that hid the bug is still there`

## Why

`tests/test_workflows.py:917` asserts `"closes #" in pr_run` — a marker WORD. It passes
for every body that merely contains the string, including the two shapes `make
pr-closure` exists to refuse:

- `Closes #271 and #276` — GitHub binds one reference per keyword, so #271 closes and
  #276 stays open (the measured PR #272);
- `closes #999` — a body that closes an issue the branch does not implement.

So the suite stayed green on exactly the defect the pipeline guard was added for, and
a reviewer reading "issue-bot: the PR closes the issue ✓" was told nothing. The
assertion looks like coverage and is not.

## What Changes

- **The test RUNS the real step.** `_run_issue_pr_step()` executes the issue-bot
  "Open the PR" `run:` block with a stub `gh` on `PATH` (the external system is the
  only stand-in — rule 6m), captures the `--body-file` content the step hands to `gh`,
  and returns it.
- **The body is checked with the pipeline's own parser**, `scripts/pr_closure.py`:
  `check(body, "ci/data-gap-376-slug")` must report no problems, and
  `closing_bindings()` must be exactly `[(376, [376])]` — one keyword, one reference,
  the implemented issue.
- **The assertion proves it is not vacuous**: the same parser is fed the two real
  failure shapes (`closes #271 and #276`, `closes #999`) and must refuse both.
- The marker-word check is deleted rather than left beside the new one.

Verified by mutating the workflow's closing line to `Closes #%s and #999`: the new
test fails with the closure parser's own message and `[(376, [376, 999])]`, and passes
again when reverted.

## Impact

`tests/test_workflows.py` (one assertion replaced, one helper + test added), this
OpenSpec change and the regenerated `OPENSPEC.md`. No product code, workflow, make
target, stage or image changes — `ARCHITECTURE.md` unchanged (rule 6h). The
`tests/test_workflows.py` row already exists in `AGENTS.md` §8 ("a PR ... without a
closing keyword" is covered there), and this change strengthens a check inside that
row rather than adding a guard, so no new row is owed.

## Not covered

- **A PR body edited AFTER opening** still does not re-run the closure check — that is
  #290, and it is a workflow-trigger change, not a test change.
- **Post-merge verification** that the issue actually closed is #288.

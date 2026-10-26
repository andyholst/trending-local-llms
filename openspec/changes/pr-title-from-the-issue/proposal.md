# The PR title is composed, and names the kind of work

**Issue:** [#541](https://github.com/andyholst/trending-local-llms/issues/541)
**Capability:** `pr-body`

## Why

`.github/workflows/issue-bot.yml` spelled the title inline:

```
--title "feat(data-gap): implement the #$ISSUE gap analysis item"
```

The sweep takes **both** `data-gap-analysis` and `tech-debt` issues (rule 6j), so a technical-debt
fix was titled a *data-gap* change about a "gap analysis item" — wrong kind, wrong artifact. And
because the text lived inside a YAML block, nothing could branch on the issue's label and no test
could run it. That is the same defect `#287` fixed for the body, one line above it.

## What Changes

- **`scripts/pr_body.py`** — `title(issue, kind)` composes
  `fix(tech-debt): implement #<n> from the tech-debt the analysis filed` or
  `feat(data-gap): implement #<n> from the post-refresh gap analysis`. `--title` (with `--kind`)
  prints it. An unknown kind is **refused** (exit 2), never guessed.
- **`make pr-title ISSUE=<n> [KIND=data-gap|tech-debt]`** — the one target, `@`-silenced so a
  capture holds the title alone (rule 6d).
- **`.github/workflows/issue-bot.yml`** — the step reads the issue's labels
  (`index("tech-debt")` → `tech-debt`, else `data-gap`), composes the title with `make pr-title`, and
  hands it to `gh pr create`.
- **`tests/test_pr_body.py`** — `test_the_pr_title_is_composed_from_the_issue_kind` drives the real
  target (both kinds, an unknown kind, a missing ISSUE, and the silenced-recipe shape) and asserts
  the workflow no longer carries the inline title.

## Impact

A reviewer's first line now says what the change IS. The composer and the workflow cannot drift,
because the workflow calls the target.

## Not covered (out of scope)

- The body's own wording still describes the `data-gap` case (issue #542 covers the remaining inline
  text of the refresh and architecture PRs).

# A recipe redirected into a file is silent, so the file holds only the product's output

**Issue:** [#539](https://github.com/andyholst/trending-local-llms/issues/539)
**Capability:** `issue-bot-artifacts`

## Why

`make` echoes each recipe line to stdout before running it. `issue-bot.yml` redirects a
target straight into a file another step READS as content:

```yaml
make issue-thread REPO="$REPO" ISSUE="$ISSUE" > issue.md
```

Measured on `origin/master`: the first line of `issue.md` was

```
python3 scripts/issue_thread.py --issue 547 --repo andyholst/trending-local-llms
```

— make's own echo, not the issue. `issue.md` is the implementer's specification (issue
#210: "read it FIRST and judge every claim against this tree"), so every run opened with a
line that is not part of the issue, and the model had to decide whether it was content.

The same shape would corrupt `pr-body.md` (the body GitHub parses for the closing keyword,
issue #287) if `make pr-body` were ever unsilenced — it is silenced today by luck of
inspection, and nothing prevented the next author from dropping the `@`.

## What Changes

- **`Makefile`** — the `issue-thread` recipe starts with `@`, so only
  `scripts/issue_thread.py`'s output reaches `issue.md`.
- **`tests/test_workflows.py`** — a guard derived from the tree, not from a list: every
  `make <target> … > <file>` a workflow performs (a `|` pipeline, a `->` arrow in prose and
  a `*.log` capture are not redirects into content) must have a recipe whose command lines
  are all silenced. It also asserts the measured case (`issue-thread`) is still covered, so
  the guard cannot pass by finding nothing.
- **`AGENTS.md`** §8 — the guard row (review-required, rule 3c).

## Impact

One character on one recipe, plus a guard. `issue.md` now begins with the issue title.
No data, no README, no ranking change.

## Not covered (out of scope)

- `implement.log` / `review.log` captures still contain the echoed command. That is
  intended: they are captured streams that `make scrub-log` redacts, not artifacts another
  step parses as content.
- The workflow's `> issue.md` redirect itself is unchanged — the fix is the recipe, so a
  local `make issue-thread` and the pipeline produce identical bytes.

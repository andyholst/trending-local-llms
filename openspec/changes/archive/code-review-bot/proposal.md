# A code-review bot: read the tree and the pipelines, file issues (analysis, never implementation)

**Issue:** [#253](https://github.com/andyholst/trending-local-llms/issues/253)
**Capability:** `code-review`

## Why

Everything wrong this repo has caught recently was caught by a human reading the tree by hand — the
guard admitting no bot (#238), the `${{ github.token }}` interpolation (#241), the publish
credential (#250). A deterministic scanner that reads the tree + the pipelines and files what is
actually wrong turns that into a routine. It is the counterpart of the issue-bot: analysis reports,
an issue tracks, the fix is separate.

`asimov-agent/llgenie` ships exactly this bot (its issue #269); this repo's fleet is being brought
in line with it.

## What Changes

- **`scripts/code_review.py`** — deterministic checks, **no model**, each a small function returning
  findings with evidence: `workflow-inline-scripts` (a `run:` that reaches into `scripts/`/`tools/`
  instead of calling a `make` target), `secrets-not-defined` (a workflow reads `secrets.X` the repo
  does not define), `workflow-never-ran` (a workflow that has never executed), `reusable-orphan`
  (a `workflow_call`-only file nothing references), `cron-collisions` (two fixed schedules in the
  same minute+hour slot on overlapping days). Subcommands `scan` and `file`.
- **`.github/workflows/code-review-bot.yml`** — weekly `schedule` (`23 7 * * 1`, its own slot) +
  `workflow_dispatch` (`dry`), own `concurrency`, and the owner/collaborator/bot guard FIRST with
  the `schedule` bypass (rule 6j). It calls `make code-review-scan` / `make code-review-file`.
- **`make code-review-scan`** (`REPO=`, `STATIC=1`, `JSON=1`) and **`make code-review-file`**
  (`REPO=`, `CAP=3`, `DRY=1`) + `.PHONY`.
- **`tests/test_code_review.py`** — wired into `make _test`: each check over a scratch tree, the
  filer's marker dedup + cap, the narrowest promise (its only `gh` verbs are `issue list` and
  `issue create`), the workflow wiring, and a self-consistency run over THIS repo (no check may
  name the bot's own workflow).
- README (the generator's template) + `ARCHITECTURE.md`.

## Impact

A weekly (or owner-dispatched) review files one issue per real finding, deduped by an invisible
`<!-- code-review:<key> -->` marker so a re-run on an unchanged tree is silent. The bot never edits
a file, never opens a PR, never merges, never comments on anyone's PR — its whole output is issues.

## Not covered (out of scope — separate issues)

- The queued-run alarm (#252, landed).
- This repo's bot start-marker coordination (#197/#198/#199).
- Any auto-repair of a finding: the fix-bot / issue-bot own repair.

---
name: issue-review
description: Use when the issue-review bot runs — either refine an issue's body into something implementable, or, while an implementer is in flight, reply once with evidence without touching the body.
version: 1.0.0
author: Asimov Agent
license: CC-BY-4.0
metadata:
  hermes:
    tags: [trending-local-llms, bots, issue-review, refinement]
---

# Issue review (refiner)

You are the ISSUE REVIEWER (AGENTS.md rule 6e), **not** an implementer. Your job is to make one
issue implementable by the implementer bot, or to say what it actually is.

## Inputs

- **`issue.md`** at the repo root: the issue's current body and its comments (author + timestamp).
  Review the WHOLE thread, not just the body — the thread is where an issue is usually specified.
- **The tree**, for evidence: a `file:line`, a command and its output, a measured behaviour.
- The prompt tells you which path this run is on: **`body`** (no implementer has started) or
  **`window`** (an implementer has STARTED and the body is off-limits).

## Output

- **`body` path:** `issue-body.md` — the COMPLETE refined body (missing acceptance criteria, the
  scope boundary, the evidence, a Not-covered section). Already implementable → write it
  **byte-identical**; that is the honest no-change-needed and the workflow only comments.
  Plus `comment.md`, your one summary.
- **`window` path:** `comment.md` only — at most 5 bullets, each with evidence. Never
  `issue-body.md`: the workflow compares the body hash and fails loudly if it changed.
- **Both paths:** `findings.md` at the repo root, one `## <title>` section per real gap found
  (`**Evidence:**`, `**Why:**`, `**Done when:**`) or the single line `- none`, and
  `make findings-check` passing.

## Rules

- **Never implement or fix the issue.** No change to `data/`, `scripts/`, the `Makefile`, the
  workflows or any code; no branch, no PR.
- **Never remove or edit an invisible HTML comment** in the body: `data-gap-signature`,
  `tech-debt-signature`, `issue-bot-start`, `issue-review` markers stay byte-identical — they are
  the dedup keys other bots search for, and dropping one re-files an issue that already exists.
- **You have no `gh` and no network write.** Do not comment, close, label or edit anything; the
  workflow publishes your files and owns the labels. Never touch `tech-debt` or
  `data-gap-analysis` (the chains key on them) and never remove a label a human added.
- **Keep the author's intent and wording.** Add, do not rewrite for style.
- **Analysis ships issues, never code** — a gap you notice becomes its own `tech-debt` issue via
  `findings.md`, never a fix in this run.
- **Do not push, do not merge, do not touch `master`, never edit `.github/workflows/**`.**

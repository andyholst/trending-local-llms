# Proposal: sweep-reverifies-against-the-base

Issue: #494 (the owner's ruling: *"the sweep bot analyzes each issue again against the latest
fetched main upstream branch so it can decide if it's old, not valid anymore, or still valid but
refinement is needed … every hour … one issue only"*)

## Why

Two gaps made the backlog decorative:

1. **No queue read `tech-debt`.** The sweep's label was `data-gap-analysis` only, so the 48
   `tech-debt` issues the bots' own findings file (#345) had no reader at all. The sweep ran
   hourly and green, over an empty queue, while the backlog grew.
2. **The verdict was taken from the issue's words.** `implement-issue` reads the thread and
   chooses `implement` / `refine` / `close`, but nothing required it to re-check the issue against
   the tree it had just fetched — so an issue already fixed on the base could be re-implemented,
   and `EVIDENCE:` was never required to point at anything checkable.

## What Changes

- **`issue_queue.QUEUE_LABELS = ("data-gap-analysis", "tech-debt")`** and `_issues()` unions
  per-label queries by issue number, oldest first — `gh issue list --label a --label b` is an AND,
  so a multi-label queue needs one call per label and a dedupe. `--label` accepts a
  comma/space-separated list. ONE issue per run is unchanged: the head of that one order.
- **The reviewer is untouched**: `review-issue-pick` runs `scripts/issue_review.py` with its own
  default, so refining a `tech-debt` body is not silently switched on.
- **The implementer's prompt requires the re-check** against the fetched base (`make base-check`
  already proves the checkout IS `origin/master`, rule 6n): judge the issue on the TREE — grep the
  file it names, run the command it quotes — then `close` with tree evidence when it is already
  fixed or obsolete, `refine` when it still holds but reads wrong, `implement` otherwise.
- **`issue_verdict.parse` refuses prose-only evidence**: an `EVIDENCE:` block that names no
  `path:line`, checkable path, or `make`/`python3`/`gh` command is REFUSED, so a lazy close cannot
  bury a live gap and a lazy refine cannot park one.
- **Tests**: three mock issues driven through the REAL scripts — one per verdict — plus the
  refused-prose cases, plus the two-label queue (both labels asked, each issue once, one head).

## Impact

`scripts/issue_queue.py`, `scripts/issue_verdict.py`, `Makefile` (the implement prompt),
`tests/test_issue_triage.py`, `tests/test_issue_review.py`, `OPENSPEC.md`, this change. No new
target, job or image: the sweep already runs hourly and `make implement-issue` already exists.

## Not covered

- **`AGENTS.md` §6j/§6e wording** — the rulebook rows for "the sweep reads both labels" and "the
  verdict's evidence must come from the tree" are a PROTECTED file; the write is refused in this
  environment, so it is filed as its own issue (rule 3c) rather than smuggled in.
- **The 48 existing `tech-debt` issues are not triaged by this change** — the sweep will take the
  oldest one per hour and decide, which is exactly the behaviour asked for.
- **The `refine` verdict still parks an issue for a human** (no expiry, by the owner's earlier
  ruling). What changed is that the parking note is announced and now needs tree evidence.

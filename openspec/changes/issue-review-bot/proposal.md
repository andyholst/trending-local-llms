# Proposal: issue-review-bot

Issue: #179

## Why

`issue-bot` implements ONE open `data-gap-analysis` issue per hour (the oldest
with no branch and no PR). Nothing in this repository ever *reads* an issue:
a machine-filed report that a human later scoped in a comment, or that a merge
made obsolete, stays exactly as first written — measured on #163 (unlabelled and
invisible for five hours), #174–#177 (filed with no triage step at all) and on
#161/#157/#152/#150, where a vague report only became implementable because a
human rewrote it by hand.

Two scheduled bots now write to the same queue, so the refinement cannot simply
be bolted on: the implementer reads the body ONCE, at the start of its run
(`issue.md`), and a rewrite during that run would make the text a human reviews
differ from the text the PR implements. The reviewer therefore needs a window
around an implementer start on BOTH sides — and both bots must read ONE queue
rule to agree on where that window is.

## What Changes

- **`scripts/issue_queue.py`** — the implementer's queue, once: the pick order
  (oldest open `data-gap-analysis` issue with no branch and no open PR) plus each
  candidate's window (`position`, last implementer activity, `window=open|closed`
  and why). `issue-bot`'s `pick` job now runs `make issue-queue` instead of
  pasting the rule into shell, so the two bots cannot drift (rule 6d).
- **`issue-bot` announces its window**: one comment before `make implement-issue`
  (`<!-- issue-bot-start: <ISO8601Z> -->`, branch + run URL, default token) on
  both paths — the `issues: [opened]` event and the hourly sweep.
- **`scripts/issue_review.py`** — the reviewer's deterministic core: `--pick`
  (one issue per run), `--mark`/`--finish` (the `review-in-progress` label and the
  `<!-- issue-review: … run=<id> -->` marker), `--guard` (the TOCTOU re-check
  before any write), `--body-hash` (the proof the window path edited nothing) and
  `--check-markers` (a rewrite may not drop an invisible dedup marker).
- **`REVIEW_GAP_HOURS := 3`** in the Makefile — ONE constant for both bots: the
  reviewer refuses an issue whose implementer window is open, i.e. 3 hourly
  sweeps before a start, a run in flight, or an implementer start within the last
  3 h; and the implementer's pick defers to a fresh reviewer marker (a bare
  `review-in-progress` label carries no timestamp, so it is advisory only).
- **`.github/workflows/issue-review-bot.yml`** — hourly (off the hour, `41`),
  owner-guarded, one issue per run, `issues: write` only. Path `body`: Hermes
  refines the body into `issue-body.md`, the workflow checks the markers survived
  and publishes it with one summary comment. Path `window` (an implementer has
  started): the body is off-limits — the workflow PROVES it is unchanged — and
  the run posts ONE bounded reply carrying the review's reminders. Either way the
  findings are filed as their own `tech-debt` issues through the existing
  `make findings-check` + `make file-findings` path.
- **`Makefile`**: `issue-queue`, `review-issue-pick`, `review-issue-mark`,
  `review-issue-guard`, `review-issue-body-hash`, `review-issue-check-markers`,
  `review-issue-finish`, `_review-issue`/`review-issue` and
  `_review-issue-window`/`review-issue-window`.
- **Docs**: `AGENTS.md` §6b (the implementer adds the start comment; the
  rulebook names the reviewer as the fourth pipeline and states the window), §2
  rules 6e/6g, one §8 row; `ARCHITECTURE.md` (a fifth workflow, three crons, the
  new targets and scripts); `README.md`; `OPENSPEC.md` (generated).
- **Tests**: `tests/test_issue_review.py` (the queue rule, the 3 h boundary at
  2 h 59 m vs 3 h 01 m with an INJECTED clock, the pick, the guard, the marker
  writes, the run-id rule) and the `tests/test_workflows.py` cases for the
  announcement, the one-queue rule and the reviewer's wiring.

## Impact

`Makefile`, `scripts/{issue_queue,issue_review}.py`,
`.github/workflows/{issue-bot,issue-review-bot}.yml`, `.gitignore`,
`tests/{test_issue_review,test_workflows}.py`, `AGENTS.md`, `ARCHITECTURE.md`,
`README.md`, `OPENSPEC.md`.

No data, contract or search change: `data/models.json` differs only by the
`generated_utc` that the regenerated `README.md` carries (the generated README
documents the new pipeline in its "How to contribute" section, so it is
regenerated with `make merge` rather than hand-edited). No image change either:
the reviewer runs in the existing base image, and no token ever reaches the
container (the workflow performs the `gh` write).

## Not covered

- Letting the reviewer implement anything — that stays the implementer's job.
- The reviewer filing anything but `tech-debt` findings from its own review: it
  never files a `data-gap-analysis` issue and never runs the data-gap analysis.
- Changing the implementer's cadence, label gate or PR/merge path: the window
  composes with the hourly sweep as it is (the start comment is the one addition).
- The eventual consistency of the `tech-debt-signature` dedup (#185): the
  reviewer preserves the markers and reuses the filing path; the race is #185.

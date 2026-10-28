# Proposal: rulebook-names-every-pipeline

Issue: the `tech-debt` issue `agents-md-6b-enumerates-five-of-the-eleven-pipelines`
(filed while implementing #479; this run's parameter arrived as `issue=#`, so the
issue is named by its signature marker rather than a number)

## Why

`AGENTS.md` §6b is the pipeline list a reader consults first, and it is
hand-maintained. Its own measure:

```
$ grep -c '^- \*\*`.*\.yml`\*\*' AGENTS.md        # inside §6b
6
$ ls .github/workflows/*.yml | wc -l
12
```

The six bullets are `refresh-bot`, `qa-validate`, `fix-bot`, `issue-bot`,
`issue-review-bot` and `architecture-bot`. `bot-health`, `code-review-bot`,
`pr-closure`, `pr-health`, `publish-agent-image` and `queued-alarm` exist, run on a
schedule or on every PR, and are described in `ARCHITECTURE.md` — but the rulebook a
contributor reads first never says they exist. The heading made the same claim twice
over: it read `## 6b. Four pipelines` while the section listed six.

The issue offers two resolutions: name every pipeline in §6b, or declare
`ARCHITECTURE.md` §4 the canonical enumeration. Only the first is safe here, and the
reason is the split rule 6h already draws: `ARCHITECTURE.md` describes **how** a
pipeline works (triggers, jobs, the `make` targets each calls — generated and gated),
while `AGENTS.md` states **what must happen**. A rulebook entry is where the rule that
governs an alarm lives, so a pointer alone would leave the rules for six running
pipelines outside the rulebook. And a guard that only asked "is it in §4" would be
vacuous: §4 already requires a section per workflow, so it can never fail on a
workflow §4 has.

## What Changes

- **`AGENTS.md` §6b** — the heading stops claiming a count it does not have, and the
  section gains one line per previously-unlisted pipeline, each naming the rule that
  pipeline enforces (`bot-health`, `code-review-bot`, `pr-closure`, `pr-health`,
  `publish-agent-image`, `queued-alarm`), plus a sentence saying `ARCHITECTURE.md` §4
  is canonical for each pipeline's *shape* while §6b must *name* every pipeline.
- **`AGENTS.md` rule 6h** — states the new requirement: a workflow added to the tree
  must be named in §6b in the same change, and `make architecture-check` fails
  otherwise. This is the rulebook-behaviour change the issue declared review-required.
- **`AGENTS.md` §8** — the `tests/test_architecture.py` row names the §6b guard.
- **`scripts/architecture_check.py`** — gains `rulebook_pipelines()` and two findings:
  a workflow in `.github/workflows/` that §6b does not name, and a `.yml` §6b names
  that is not a workflow in the tree (both directions, like the §3 target tables). A
  missing `AGENTS.md` is a finding too, so deleting the file cannot silence it.
- **`ARCHITECTURE.md`** — §4's "Eleven workflows … Seven have a cron" becomes the real
  twelve/eight (`bot-health` was counted in neither), and §6's
  `scripts/architecture_check.py` row states the §6b half of its job.
- **`tests/test_architecture.py`** — the fixture writes an `AGENTS.md` with a §6b list
  (the shape the rule requires), plus a new case: a workflow missing from §6b is
  reported in both directions and turns green when named.

## Impact

- A new pipeline can no longer ship unlisted: adding `.github/workflows/x.yml`
  without a §6b line turns `make architecture-check` (and `make test`) red in the PR
  that adds it, and in the daily `architecture-bot` run.
- No data, contract, README, make target, workflow or image change.
- The `AGENTS.md` diff is the review-required part (rule 3c).

## Not covered

- §4's per-pipeline **prose** (why each pipeline exists, its triggers) stays
  hand-written and unguarded beyond presence, the §4 job names and the generated §10
  inventory — the same boundary `scripts/architecture_check.py` documents.
- The counts inside §4's prose stay unreadable to the guard (it cannot read prose);
  this change corrects them by hand, and only the *sections* are enforced.

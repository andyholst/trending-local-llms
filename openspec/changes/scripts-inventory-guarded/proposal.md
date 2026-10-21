# Proposal: scripts-inventory-guarded

Issue: #506 — architecture-check: §6's script inventory is unguarded

## Why

The daily `architecture-bot` run [39582646399](https://github.com/andyholst/trending-local-llms/actions/runs/39582646399/job/119163787910)
is green (`[architecture-bot] OK the inventory block matches the tree (150 lines)`) and
`make architecture-check` passes — while `ARCHITECTURE.md` §6 "The scripts" is missing
**9 of the 46 files in `scripts/`**:

```
architecture_bot.py, code_review.py, env_int.py, install_hermes_ci.sh, pr_health.py,
queued_run_alarm.py, refresh_base.py, sweep_alarm.py, verify_closure.py
```

`scripts/architecture_check.py` only asked whether a script's NAME appears *somewhere*
in the document. Since #479 the generated §10 block names every script, so that
requirement is satisfied by the block while §6 — the table a reader actually uses to
learn what a script does — silently lost a fifth of its entries. Nine scripts, including
every bot written this week, had no role there.

This is why the bot looked idle: it keeps the generated half true, and the half a human
reads has no guard at all.

## What Changes

- `scripts/architecture_check.py` gains `described_scripts()` + a finding: every file in
  `scripts/` MUST have a row in §6's table (first-cell backticked path). A name in the
  generated §10 block no longer satisfies it.
- `ARCHITECTURE.md` §6 gains the 9 missing rows, written from each script's real code
  (the installer seam, the silent-PR alarm and its repair half, the stuck-run alarm, the
  dropped-cron alarm, the refresh-base publisher, the post-merge closure proof, the
  settings reader, the code-review decision, and the inventory generator itself).
- `tests/test_architecture.py`: the fixture writes a §6 table (the shape the rule now
  requires), plus a new case — a script named in the document but with no §6 row is
  reported, and adding the row turns it green.
- `AGENTS.md` rule 6h and the §8 row name the §6 requirement.

## Impact

- A new script without a §6 role now turns `make architecture-check` RED in the PR that
  adds it — and, through the same target, in the daily `architecture-bot` run.
- No data, contract or README change; no new make target, workflow or image.

## Not covered

- §4's per-pipeline PROSE (why a pipeline exists) stays hand-written and unguarded; that
  is the remaining half of #480, which this change does not close.
- The role text is prose: the guard proves a row EXISTS and names the script, not that
  the sentence about it is still accurate.

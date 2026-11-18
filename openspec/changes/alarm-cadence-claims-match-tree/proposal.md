# Change: alarm-cadence-claims-match-tree

Issue: #1032

## Why

`ARCHITECTURE.md` §4 and `AGENTS.md` §6b say what starts each pipeline, and since the owner
cadence directive of 2026-11-15 (rule 6t, issue #1029) that text is wrong for seven pipelines:
the description claimed **eight** cron-scheduled pipelines ("each ONCE a week on Wednesday") and
headings labelled `architecture-bot.yml` (weekly `13`), `pr-health.yml` (weekly `53`),
`bot-health.yml` (weekly `23`), `queued-alarm.yml` ("schedule + dispatch"),
`issue-review-bot.yml` ("weekly sweep"), `issue-bot.yml` ("weekly sweep") and
`code-review-bot.yml` ("weekly (Monday `23 7`)") as scheduled. Only `refresh-bot.yml`
(`0 6 * * 3` + `43 17 * * 3`) declares a `schedule:` in the tree today.

The consequence is not cosmetic. An alarm that waits for an owner dispatch is described as a
scheduled sweep, so a reader (or an agent) waits for a cron GitHub never fires, and the failure
stays silent — the exact class the alarms exist to catch. Rule 6h already verifies job names,
targets and scripts against the tree; **the cadence claim was the one pipeline property stated
in prose and verified by nothing.**

## What Changes

- `make architecture-check` gains a CADENCE guard (`scripts/architecture_check.py::cadence_findings`):
  - a cron slot quoted for a pipeline must be a cron that pipeline declares;
  - a cadence word ("weekly", "scheduled", "cron", "twice-an-hour") attached to one pipeline —
    in a §4 heading's parenthetical or in an `AGENTS.md` §6b rulebook bullet — requires that
    workflow to declare a `schedule:`;
  - a dispatch claim requires the workflow to declare `workflow_dispatch:`;
  - a counted claim ("Eight have a cron") must equal the tree's scheduled-pipeline count.
- `architecture_check.py` gains `rulebook_pipeline_claims()`: a §6b bullet is ONE wrapped
  paragraph, so its claim is read across its intro lines (measured blind spot:
  `- **`code-review-bot.yml`**` hid "weekly (Monday `23 7`)" on the following line).
- `cadence_findings(root)` takes its workflow list and documents from the tree by default, so a
  test or caller can ask the question about a root alone.
- `ARCHITECTURE.md` §4's lead paragraph and the seven pipeline headings, and the `AGENTS.md`
  §6b/§6l/§6q/§6s sentences that call a dispatched alarm "weekly"/"scheduled", are rewritten to
  the tree's truth: ONE cron pipeline (`refresh-bot.yml`), the rest owner-dispatched.
- `AGENTS.md` §6h states the new clause; §8 gains the row for the guard's tests.
- No workflow trigger changes: the guard describes the cadence, it does not create one (rule 6t
  stays the owner's decision).

## Impact

- Affected specs: `architecture-description` (the description now verifies pipeline cadence).
- Affected code: `scripts/architecture_check.py`, `tests/test_architecture.py`,
  `ARCHITECTURE.md`, `AGENTS.md`.
- Affected pipelines: none (no trigger added or removed).
- Not covered: the cadence itself is not changed here — re-scheduling a sweep is an owner act
  (rule 6t); and general prose that never names a pipeline is out of scope, because a cadence
  word inside a sentence about history is not a claim about how a pipeline starts.

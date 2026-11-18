# Tasks — #1032: the alarm sweeps are owner-dispatched; ARCHITECTURE.md still calls them weekly

## Guard (cadence claims are claims about the tree)

- [x] `scripts/architecture_check.py::cadence_findings` — quote-a-slot, cadence-word, dispatch and counted-cron prongs, wired into `findings()`
- [x] `rulebook_pipeline_claims()` reads each `AGENTS.md` §6b pipeline bullet's INTRO so a claim wrapped onto the next line is still read (measured: `code-review-bot.yml` hid "weekly (Monday `23 7`)" on the following line)
- [x] `_CADENCE_RETIRED` exempts the sentence that documents a removal (and names `no schedule`)
- [x] `cadence_findings(root)` defaults `workflows`/`docs` to the tree so a test can ask about a root alone

## Description rewritten to the tree's truth

- [x] `ARCHITECTURE.md` §4 lead: ONE cron pipeline (`refresh-bot.yml` `0 6 * * 3` + `43 17 * * 3`), the other sweeps owner-dispatched, `tests/test_workflows.py` pins it (rule 6t)
- [x] §4 headings for `architecture-bot`, `pr-health`, `bot-health`, `queued-alarm`, `issue-bot`, `issue-review-bot`, `code-review-bot` re-labelled "(owner dispatch)"; `bot-health` body names the slot #1029 removed
- [x] `sweep-alarm` Make-target row: dispatch-only mode derived from the workflow tree, no `MAX_AGE_HOURS=3` override (issue #804)
- [x] `AGENTS.md` §6h carries the cadence-claim clause; §6l/§6q/§6s/§3b sentences that called a dispatched alarm "weekly"/"scheduled"/"twice-an-hour" corrected

## Tests

- [x] `tests/test_architecture.py`: slot-for-dispatch-only RED, "weekly" word RED, truthful slot GREEN, counted-cron RED→GREEN, wrapped §6b bullet RED, retirement sentence GREEN, dispatch-without-trigger RED
- [x] `tests/test_architecture.py::test_the_shipped_documents_pass_the_cadence_guard` — the real documents against the real workflows, GREEN
- [x] The one-view pin extended: `architecture_check` imports the bot's `workflow_crons` / `workflow_trigger_events` instead of writing its own trigger parser

## Wiring / bookkeeping

- [x] `AGENTS.md` §8 gains the row naming what these tests catch (rule 6c/6h)
- [x] `make architecture-check` green on the rewritten tree
- [~] `make test` green on this branch — blocked: the suite is running on this branch at the time of writing; the PR reports the verified run

# Change: rediagnosis-annotates-issue-thread

Issue: #987

## Why

`make pipeline-failure-issue`'s re-diagnosis pass (issue #969) raises an UNDIAGNOSED ledger row
when the failed run's log later becomes readable. It writes the raise to `data/pipeline_failures.json`
ONLY — the ledger note (`rediagnosed_utc` / `error_excerpt` / `rediagnosis_note`) lands, but nothing
is posted on the issue thread the row was filed on. `entry["issue_url"]` is present on raised rows
(the 7 rows live-previewed by this change) yet the issue's thread still reads "log unreadable"
while its diagnosis now lives in the ledger. The ledger is the machine's memory; the issue thread is
the human's. A raised row whose thread still claims "log unreadable" invites a redundant manual
re-diagnosis — the exact work this seam exists to remove (measured: issue #969's own thread).

## What Changes

- `scripts/bot_markers.py` declares a new marker `pipeline-rediagnose` (the UNREGISTERED_OWED seam:
  its AGENTS.md §6j table row is owed to rule 3c — a protected agent-instruction file a headless
  leg cannot write). The marker's shape lives in `bot_markers.py` via a dedicated writer and a
  `run=`-carrying parser, so the writer and the dedup reader share ONE spelling (rule 6j).
- `scripts/pipeline_failure_issue.py`'s `rediagnose_undiagnosed()` posts ONE marker-deduplicated
  comment on the cited issue when a raise lands: it reads the issue's comments first and skips
  when a `pipeline-rediagnose` comment for the same run id already exists (one comment per raised
  row, never per sweep). The comment quotes the landed scrubbed `error_excerpt` and the `targets`.
  Written with the default `github.token` (rule 6e) — the caller `queued-alarm.yml` passes
  `GH_TOKEN: ${{ github.token }}`.
- No new make targets, no workflow change: the pass and the comment ride the existing
  `make pipeline-failure-issue` call in `queued-alarm.yml`.
- The owed AGENTS.md §6j table row (naming `pipeline-rediagnose`) is recorded as a findings.md
  finding (owed-row marker, rule 3c) — a headless leg cannot write AGENTS.md.

## Impact

- Capability: `alarms` (rule 6r filer)
- Affected code: `scripts/bot_markers.py`, `scripts/pipeline_failure_issue.py`,
  `tests/test_pipeline_failure_issue.py`, `tests/test_bot_markers.py` (wiring assertion),
  `findings.md`
- Not covered: retroactively backfilling already-rediagnosed rows' threads (a data/threshold
  decision, not a code path); the AGENTS.md §6j table row wording (owed to rule 3c human sign-off).

# Proposal: pipeline-failure-diagnosis

Issue: #802 (measured: qa-validate master run 43088760321 red on `openspec-archive-check` — diagnosed only because a human opened the run page; the chain ended as issue #800 → fix PR #808 → guard `tests/test_openspec_archive_check.py`)
PR: #811

## Why

The repo already alarms on a red master (`make master-alarm`, rule 6q) and on queued runs (rule
6l) — but an alarm names a failing JOB, not its CAUSE. Every pipeline failure that reached CI so
far was diagnosed only because someone re-opened a run log and re-derived the error by hand; the
measured chain for #800 began with a human reading run 43088760321's log. When nobody re-opens
the log — the normal state — a red main pipeline leaves no artifact, its error text expires with
the run, and the same error class can return unnoticed on the next merge. A failure that lands on
master or on a schedule must DIAGNOSE ITSELF: file an issue carrying the log's own error block,
and forbid closing it without a regression guard.

## What Changes

- **`scripts/pipeline_failure_issue.py`** (`make pipeline-failure-issue`, run by `queued-alarm.yml`
  after its three alarms): reads every MAIN-PIPELINE run (`qa-validate`, `refresh-bot`,
  `issue-bot`, `issue-review-bot`, `architecture-bot`, `queued-alarm`) that concluded bad on a
  `push` to master or a `schedule` within `--window-hours` (default 192 — one full weekly cadence
  plus grace), fetches each failing job's log, extracts the bounded, deduplicated error block and
  the `make` targets the log names, **scrubs it through `scripts/scrub_log.py`'s redactor before
  any of it is written** (§3d), and files ONE `tech-debt` issue per failing job in the message
  pattern (issue #771) carrying the marker `<!-- pipeline-run-failure: <ts> run=<id> -->`
  (registered in `scripts/bot_markers.py`). An unreadable log files UNDIAGNOSED, loudly. A failed
  read of pipeline state exits 2.
- **`data/pipeline_failures.json`** — the append-only LEDGER (rule 3b): one row per diagnosed
  run (run id, workflow, job, targets, issue, `fix_pr`, `guard`). Dedup is run-id keyed against
  BOTH memories — the ledger and a `--state all` marker scan — so a quickly-fixed closed issue is
  never re-filed. When a sweep appends, `queued-alarm.yml` lands the append as a ledger PR (the
  architecture-bot pattern; body via `make pipeline-failure-ledger-pr-body`, NO closing keyword).
- **`scripts/pipeline_failure_guard_check.py`** (`make pipeline-failure-guard-check`, a step of
  qa-validate's `validate` job, named in `master_alarm`'s gate registry): REFUSES a ledger entry
  whose issue is CLOSED while it names no fix PR and no guard test; a fix PR whose `guard` test is
  not a collected `tests/test_*.py`; and a CLOSED marker issue the ledger never recorded. An
  in-flight fix is reported, never red; an unreadable ledger exits 2.
- **`tests/test_pipeline_failure_issue.py` + `tests/test_pipeline_failure_guard.py`** — the real
  filer end-to-end against a stub `gh` (rule 6m) and the real gate against planted ledgers.
- **Rulebook + description**: `AGENTS.md` rule **6r** and its two §8 guard rows;
  `ARCHITECTURE.md` §3 target rows, §4 queued-alarm + qa-validate steps, §6 script rows.

## Impact

- Affected specs: `alarms` (new requirements: diagnosis-filing, the ledger, the guard gate).
- Affected code: `Makefile` (four targets), `.github/workflows/queued-alarm.yml` (filer step +
  ledger-PR job), `.github/workflows/qa-validate.yml` (guard step), `scripts/bot_markers.py`
  (marker registration), `scripts/master_alarm.py` (gate registry entry), `AGENTS.md`,
  `ARCHITECTURE.md`, `data/pipeline_failures.json`.
- No existing data, contract key, or table changes; nothing removed (rule 3b).

## Not covered

- `pull_request`-event failures: already tracked by the PR itself (fix-bot, pr-health) — filing an
  issue per failing PR would duplicate the queue.
- The fix itself: a filed failure issue is fixed in its own reviewed change with its own OpenSpec
  record (rule 6g); this change only files, records, and gates.
- `workflow_dispatch` runs: a manual start is a collaborator's act (§3f), not an auto-diagnosed
  pipeline failure.

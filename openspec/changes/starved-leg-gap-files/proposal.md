# Proposal: starved-leg-gap-files

Issue: #856

## Why

`analyse()` treats every empty raw snapshot as a quiet query and keeps all of them
out of the issue-triggering signature (`scripts/data_gap_analysis.py:559-565`: "only a
whole refresh with no models at all would be a defect"). A WHOLE LEG starving is a
different event and nothing detects it. Measured on the 2026-11-11 refresh
(`data/raw/*-20261111*.json`): every one of the six `cpu` snapshots and 10 of the 11
`amd` snapshots hold `models: []`, while the same refresh's `nvidia` and `metal` legs
captured models — the mirror was reachable and two query sets captured nothing. That
state files nothing, prints only an "(informational)" line, and is invisible to
`make query-coverage` (which proves which models queries NAME, never which legs
CAPTURE) and to `make validate-fetch` (a live dry-run re-fetch in `qa-validate`, never
an inspection of the captured snapshots). A backend whose query vocabulary drifts
starves silently forever.

## What Changes

- **Whole-leg starvation becomes a signature gap** in `scripts/data_gap_analysis.py`:
  for each backend seen in `data/raw/`, take its NEWEST run (the 8-digit date stamp in
  the file name); if every snapshot of that run captured 0 models, emit
  `starved_leg:<backend>` in the signature (backend only — no date, so a continuing
  starvation is ONE stable entry, the #472 churn lesson) and a loud
  `STARVED LEG <backend>: …` finding naming the snapshot count and run date.
- A **single empty snapshot stays informational** — a per-query write legitimately
  captures nothing; a leg with a capturing newest snapshot never fires.
- `report["maintenance"]["starved_legs"]` carries the detail; the existing
  `make data-gap-issue` label machinery files it with no filer change.
- AGENTS.md §4's gap-analysis row and §8's guard row state the amended rule
  (rule 3c disclosure — the volatile exclusion now covers a *single* empty snapshot,
  not a starved leg).
- Tests: `test_a_whole_starved_leg_changes_the_signature` and
  `test_a_single_empty_snapshot_stays_informational`.

## Impact

- `scripts/data_gap_analysis.py` — new per-backend newest-run scan, signature entry, finding line.
- `tests/test_data_gap_analysis.py` — two new guards.
- `AGENTS.md` — §4 gap-analysis sentence and §8 guard row amended (rule 3c).

## Not covered

- *Why* the CPU/AMD queries capture nothing (query-vocabulary repair is its own change).
- A backend that ran no snapshots at all in a refresh (absent legs stay unreported; a
  missing leg is a pipeline defect the refresh workflow itself must catch).
- The `--require-hits` live gate (#293 closed that reporting class).

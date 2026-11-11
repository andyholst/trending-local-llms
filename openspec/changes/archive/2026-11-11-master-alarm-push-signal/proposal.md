# Proposal: master-alarm-push-signal

Issue: #527 (measured: qa-validate run 39625708799 — a push to master red at the OpenSpec gate, unit tests never reached)

## Why

`qa-validate`'s `validate` job runs on a `push` to master as well as on PRs, and every repair
path in this repo needs a PR: `dispatch-fixbot` only touches `ci/trending-refresh-*` /
`ci/data-gap-*` PRs, `fix-bot` refuses a non-PR, `pr-health` sweeps open PRs, and
`architecture-bot` repairs exactly two generated files. A deterministic gate that goes red AFTER
`auto-merge` therefore stays red until a human opens a run page — measured on run 39625708799,
master red at the OpenSpec gate with the unit tests never reached. A red master must produce a
signal, not a page nobody opens (issue #527).

## What Changes

- **`scripts/master_alarm.py`** — the alarm: reads the NEWEST `push`-to-master `qa-validate` run
  and exits 1 naming the run URL and the failing jobs when it concluded in failure; 0 when green,
  pending or absent; 2 when GitHub cannot be read. It carries the KEEPER/ALARM registry: every
  deterministic gate of the `validate` job sits on the keeper list (architecture-bot repairs it) or
  the alarm list (this alarm covers it).
- **`make master-alarm`** — internal `_master-alarm` + public wrapper (`REPO=`, `LIMIT=`), run by
  a new step of `queued-alarm.yml`'s `alarm` job, so the scheduled sweep goes RED instead of the
  red sitting silent.
- **`tests/test_master_alarm.py`** — runs the real script against a recorded fixture, pins the
  registry (a validate-job gate on NEITHER list fails the suite), pins the workflow (guard first,
  the workflow calls the make target, never the script) and the AGENTS.md rule + §8 row.
- **Rulebook + description**: `AGENTS.md` rule **6q** and its §8 guard row; `ARCHITECTURE.md` §3
  target row, §4 `queued-alarm.yml` step, §6 scripts row.

## Impact

`Makefile`, `.github/workflows/queued-alarm.yml`, `scripts/master_alarm.py`,
`tests/test_master_alarm.py`, `AGENTS.md`, `ARCHITECTURE.md`, `OPENSPEC.md`.
CI: rides the existing `queued-alarm.yml` schedule; `master-alarm` is exercised by its tests in
`make test` (live GitHub reads stay out of the unit tests).

## Not covered

- A second **keeper** that edits data on red master — the keeper list stays exactly
  `architecture-bot`'s two generated files; any gate whose repair needs a code edit remains
  alarm-only until a real keeper exists for it (the alarm is the signal, not the fix).

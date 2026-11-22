# Proposal: cron-install-check-1270
PR: #1272

Issue: #1270 — "Fleet: Hermes cron watcher installation must be identical on both hosts".

## Why

The C/R/M trigger protocol lives in the repo (`scripts/watch_monitor.py`, PR #1267) but the HOST cron installation is outside it. A missing watchdog, a disabled agent gate, a shared state file or a stripped-PATH wrapper makes a host fall out of sync silently.

## What

Add `make cron-install-check` (`scripts/cron_install_check.py`): an offline, secret-free verifier of the two-job layout — exactly one enabled no-agent watchdog and one monitor-gated agent job, separate state files, an explicit `gh` path fix, and the repo-owned detector's C/R/M marker contract. Add offline fixture tests and the ARCHITECTURE row. It never calls the network and never reads credential values.

## How

Reads `cron/jobs.json` from `HERMES_HOME` (or `~/.hermes`), checks job shape and wrapper bytes, prints stable `[cron-install] OK/FAIL …` lines, exits non-zero on any gap. `tests/test_cron_install_check.py` plants fixtures for disabled/missing/duplicate/shared-state/detector-drift cases.

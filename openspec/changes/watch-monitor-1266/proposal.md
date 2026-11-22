# Proposal: watch-monitor-1266

Issue: #1266

## Why

The comment/CI/merge detector lives only in one host's `~/.hermes/scripts/`, so the two machines can drift and a rebuilt host loses the trigger. PR #1244's `make comment-watch` is not on master.

## What Changes

- Add `scripts/watch_monitor.py`: deterministic, timestamp-free `C:` / `R:` / `M:` markers from a caller-owned JSON state file; `make watch-monitor` with a CI-safe `--check` mode.
- Add `tests/test_watch_monitor.py` and an `AGENTS.md` rule 6w + §8 row naming the two-job watcher and the fetch/pull-on-merge duty.
- Update `ARCHITECTURE.md` target/script rows and wire the check into `qa-validate`.

## Impact

One script, one target, one test module, one rulebook rule and description. No data format, contract or image change.

## Not covered

- No GitHub app, webhook receiver, collaborator grant, CI dispatch or merge behaviour.

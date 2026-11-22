# Proposal: heartbeat-1282

Binding-exempt: work folded into PR #1267, which closes #1266; issue #1282 is the filer's tracking thread and is referenced, not closed here.

## Why

The agent cron is monitor-gated. Without a deterministic heartbeat, a change observed after the agent's last run waits until the next agent tick, and a quiet stretch can leave the queue untouched. The host-side bridge on `asimov@omarchy` proved the need but is not installable on the other machine.

## What Changes

- Add an opt-in `--heartbeat-seconds N` flag (default `0`) to `scripts/watch_monitor.py`; with `N>0`, emit one `H:<bucket>` marker where `bucket = int(time.time()) // N`. No wall-clock timestamp.
- Extend `make watch-monitor` to forward the flag and `CHECK=1` to accept `H:` as a legal marker prefix.
- Extend `tests/test_watch_monitor.py` with quiet-tick, heartbeat-boundary, coexistence and wiring guards.
- Extend `AGENTS.md` rule 6w with the H marker and the "after C/R/M, keep working" duty, and §8 with the extended row. Update `ARCHITECTURE.md` rows.

## Impact

No data format, contract, image or workflow wiring change. The no-agent monitor keeps emitting nothing on a quiet tick because the heartbeat is opt-in. Host wrappers pass `--heartbeat-seconds 900` and stop synthesising H locally.

## Not covered

- No CI dispatch, no merge, no master push, no collaborator grant, no new cron job on either host.

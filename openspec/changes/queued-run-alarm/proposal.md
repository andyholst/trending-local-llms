# A stuck `queued` job must be loud, not an eternal pending

**Issue:** [#252](https://github.com/andyholst/trending-local-llms/issues/252)
**Capability:** `queued-run-alarm`

## Why

When a runner label matches nothing (an offline/unregistered self-hosted runner, or the account's
hosted-runner minutes for that OS exhausted), GitHub does **not fail** the job — it leaves it
`queued` forever. The run never concludes, `mergeStateStatus` stays `BLOCKED`, and every PR's
checks sit at "pending" with no signal anywhere that anything is wrong. This repo's bots all run
on schedules and dispatches, so a run that never concludes is invisible: no failure, no issue, no
comment.

`asimov-agent/llgenie` measured this state and shipped a deterministic sweep for it (its issue
#254); this repo has the same exposure and no alarm.

## What Changes

- **`.github/workflows/queued-alarm.yml`** — `schedule` (`7,37 * * * *`) + `workflow_dispatch`
  (`minutes` input), its own `concurrency` group, and the owner/collaborator/bot guard as the
  FIRST job with the `schedule` bypass (rule 6j, as fixed in #238). It calls `make queued-alarm`.
- **`scripts/queued_run_alarm.py`** — deterministic, `gh` + stdlib, no model: read the
  `queued`/`in_progress` runs, list the still-`queued` jobs, flag those queued longer than
  `--minutes` (default 30), print a table naming the label and age, and `--comment` posts ONE
  marker-deduplicated comment per affected run. Exit 0 = nothing stuck, 1 = a job is stuck (so
  the scheduled job goes red), 2 = the API call failed.
- **`make queued-alarm`** (`REPO=`, `MINUTES=`, `COMMENT=`) — the workflow's one command.
- **`tests/test_queued_run_alarm.py`** — wired into `make _test`: the decision, the marker dedup,
  and the workflow wiring, over the REAL code with a fake `gh` on PATH.
- README + `ARCHITECTURE.md`.

## Impact

A stuck queue becomes a red scheduled run plus a comment on the affected run. Read-only apart
from the optional comment; it never edits code, never opens a PR, never merges.

## Not covered (out of scope — separate issues)

- The code-review bot (#253).
- This repo's bot start-marker coordination (#197/#198/#199).

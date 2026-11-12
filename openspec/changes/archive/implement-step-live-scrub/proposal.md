# Proposal: implement-step-live-scrub

Issue: #629 — `tech-debt: The implement step redacts its agent stream only AFTER the run — a post-mortem, not a live log`
PR: #844

## Why

The implementer leg is the longest agent call in the repo (~20 minutes), and its step shape is a
post-mortem:

```
make implement-issue > implement.log 2>&1   # the step prints NOTHING while the agent runs
...agent runs ~20 minutes, console silent...
make scrub-log FILE=implement.log LOG_OUT=implement.scrubbed.log TAIL=60   # redaction AFTER the end
```

Three consequences (issue #629): (1) the job log cannot answer "what is the implementer doing
right now?" — a reviewer watching a live run sees an empty console until the leg ends; (2) the RAW
capture sits in the runner's workspace for the whole run and is redacted only at the end, while
every search leg already redacts line-by-line through the `scrubbed_run` seam (#591) — the same
stream has two different safety stories, and (3) the same post-mortem shape exists in both
reviewer steps of `issue-review-bot.yml`.

The seam already exists and is already proven live (`tests/test_scrub_log.py::test_the_seam_shows_a_round_while_it_runs`).
What is missing is the two agent legs USING it: the redaction belongs in the TARGET (rule #355:
"a workflow step, `fix_loop.sh` and a human all call this target, so a caller cannot be the one
that remembers"), and the step should stop capturing what the target already redacts.

## What Changes

- **`make implement-issue`, `make review-issue` and `make review-issue-window` run their container
  through `$(call scrubbed_run, …)`.** The target pipes the whole agent stream through
  `scripts/scrub_log.py --stream` before the console, writes the raw capture (gitignored) AND the
  redacted artifact itself (names pinned per target via `HERMES_LOG` / `HERMES_LOG_SCRUBBED`), and
  keeps the agent's own rc through `bash -o pipefail`.
- **The shipped steps stop capturing.** `issue-bot.yml`'s `Implement the issue` step and both
  reviewer steps of `issue-review-bot.yml` run `make <target>` uncaptured; the rc contracts
  (`rc=$?` → `implemented=false`, `exit $rc`, the rc=3 detach `::error::`) are unchanged, and the
  uploaded artifact path (`implement.scrubbed.log` / `review.scrubbed.log`) is unchanged.
- **The guard covers the new shape.** `implement-issue`, `review-issue` and `review-issue-window`
  join `AGENT_TARGETS_TO_SCRUB` (`scripts/check_secret_output.py`, ONE list), so
  `agent-target-does-not-scrub` refuses any of them losing the seam, and a step that ran an agent
  target with nothing redacting it stays refused (`agent-stream-printed-raw`).
- **A new suite** `tests/test_implement_stream.py` drives the shipped step `run:` text (read from
  the workflow file, never a copy) and proves: lines reach the console BEFORE the agent process
  exits, rc survives the pipe, every spelling of a planted value stays masked WHILE streaming, the
  raw capture keeps the value and the artifact does not, and the reviewer rc=3 contract survives.
  `tests/test_scrub_log.py`'s stub `make` now emits through the real seam (the target self-scrubs),
  and `tests/test_secret_output.py`'s matrix fixture seeds the guard's OWN list, never a copy.

Verified RED-then-GREEN: the new suite's step-text assertions failed 3 checks against the shipped
post-mortem step (`> implement.log` + `make scrub-log` present) and pass against the live shape;
the guard's `agent-target-does-not-scrub` fired while the Makefile recipes lacked the seam.

## Impact

`Makefile` (three recipes), `.github/workflows/issue-bot.yml`, `.github/workflows/issue-review-bot.yml`,
`scripts/check_secret_output.py`, `tests/test_implement_stream.py` (new),
`tests/test_scrub_log.py`, `tests/test_secret_output.py`, `tests/test_workflows.py` (the pinned
step-shape test), regenerated `ARCHITECTURE.md` §10 block (the jobs' `make` calls changed) and
`OPENSPEC.md`. No target, stage, job or image is added, renamed or removed.

## Not covered

- **`make fix` / the search legs** — already live-scrubbed through the seam (#591/#355); untouched.
- **Artifact upload retention** (7 days) and the gitignored raw capture's lifecycle — the seam
  already writes both files today for the search/fix legs; this change reuses that behavior.
- **Streaming the redacted stream back into Hermes** or any interactive console — out of scope.

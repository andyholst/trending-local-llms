# Proposal: per-round-log-capture

Issue: #631
PR: #846

## Why

`scripts/fix_loop.sh` runs up to `FIX_ROUNDS` (3) `make fix` rounds — plus a
reasoning-off retry — and every round streams the agent through the
`scrubbed_run` seam into the SAME `$(HERMES_LOG)` / `$(HERMES_LOG_SCRUBBED)`
capture files. `scripts/scrub_log.py`'s `stream()` opened both with mode
`"w"`, so each round TRUNCATED the transcript of every round before it. The
capture artifact exists (issue #566) precisely so a round that DETACHED leaves
its question behind — but with three rounds the artifact held only the LAST
one: the first round's detach message was gone the moment round 2 started,
which is exactly the case the artifact was added for.

## What Changes

- `scripts/scrub_log.py`: `stream()` gains an `append` mode; `main()` gains
  `--append`. With it, both captures open in append mode and each invocation
  writes a `===== [scrub-log] capture <UTC> pid=<pid> =====` delimiter first,
  so one artifact file holds every invocation, delimited and timestamped.
  Without the flag the behaviour is unchanged (truncate) — the flag is
  opt-in per invocation.
- `Makefile` `scrubbed_run` seam: passes `--append`, so EVERY agent leg
  (`make fix`, `make search-*`, `make implement-issue`, `make review-issue`)
  appends per invocation within a run.
- `.github/workflows/issue-bot.yml`: the QA artifact uploads
  `hermes-run.scrubbed.log` alongside `implement.scrubbed.log` — with the
  append seam that file is the fix loop's full, round-delimited transcript,
  which is what the #566 artifact was filed to preserve. (The issue's cited
  `fix-bot.yml` no longer exists; `issue-bot.yml`'s fix-loop step is the live
  caller.)
- `AGENTS.md` §3d + §8 guard table: the capture-appends rule and its guard row.

## Impact

- Affected specs: `pipeline-integrity` (agent-log redaction scenario).
- Affected code: `scripts/scrub_log.py`, `Makefile` (seam),
  `.github/workflows/issue-bot.yml` (artifact path),
  `tests/test_scrub_log.py` (two new tests).
- No data-store change; no contract change; purely additive pipeline behaviour.

## Not covered

- Per-round SEPARATE files (the delimiter-in-one-file shape was chosen:
  artifact paths, `.gitignore` and the working-file list stay unchanged).
- Cross-RUN persistence: each CI job starts from a clean workspace, so the
  append is bounded to one run by design.

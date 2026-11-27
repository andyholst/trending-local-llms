# Proposal: scrub-run-attach-stdin

Issue: #1808
PR: #1819

## Why

The `scrubbed_run` seam pipes the agent command into `$(PYTHON_RUN) python3
scripts/scrub_log.py --stream` so the live agent output is masked, printed and
captured. `PYTHON_RUN` is a `docker run`, but without `-i` Docker closes the
container's stdin. The redactor therefore read EOF immediately — refresh run
46000947806 logged `[scrub-log] stream: 0 line(s)` — exited, and the still-writing
agent died with SIGPIPE (exit 141) before one redacted line was captured. #1747
fixed only the classification; the cause remained, so every search leg of the
weekly refresh failed and the store never updated.

## What Changes

- Add `-i` to the `docker run` in `PYTHON_RUN`, attaching the live pipe to the
  redactor's stdin. The many other `python3 scripts/…` callers of this seam never
  read stdin, so `-i` is harmless for them.
- Leave the `#1747` SIGPIPE classification and the `pipefail` exit-status contract
  in `scrubbed_run` byte-identical: a genuinely dead agent still fails, no skip,
  no retry-all, no fabricated line.
- Add a RED-first guard in `tests/test_scrubbed_run_seam.py` that drives the shipped
  seam and the shipped `PYTHON_RUN` against a stand-in Docker CLI: a delayed
  producer must reach the redactor with both lines and a success status on the
  fix, and the unfixed Makefile must reproduce the 141 with zero lines.

## Impact

All four search legs and the fix/implement/review legs that route through
`scrubbed_run` capture their live agent stream again. No data value, contract,
target, workflow or rulebook rule changes; the redactor's output files and
exit-status semantics are unchanged (rule 3b additive).

## Not covered

No change to the #1747 outage classification, to `scrub_log.py` itself, or to
the agent command's own failure handling. A genuinely silent or genuinely dead
agent is still reported exactly as before.

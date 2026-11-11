# Proposal — repair-in-flight-is-visible

Issue: #386 (a repair in flight is invisible in the job log)

## Why

`$(call scrubbed_run,…)` ran the command into `hermes-run.log` and printed `make scrub-log`'s bounded
tail only AFTER it had exited. Windows read "fix-bot is repairing this PR **now**" while the job log
itself showed one line and then nothing, so "is the bot working?" was answerable only from a
post-mortem — measured on fix-bot run 39183131652, where the whole step was empty in
`gh run view --log` for over an hour while the round ran.

Two causes, one shape:

1. **The seam printed at the END.** Redaction after the fact is safe and useless: it hides the round
   it is redacting until the round is over.
2. **The container's stdio is a pipe, not a TTY.** `docker run` without a TTY makes every Python
   process block-buffer, so even a host that streams would see nothing until the child exited.

## What changes

- `scripts/scrub_log.py` gains `--stream`: it reads a command's stream from stdin, MASKES each line,
  prints it at once (flush per line), and writes the same pair of files the post-mortem mode writes —
  the RAW capture to `--raw` (gitignored, never uploaded) and the REDACTED copy to `--out` (the run
  artifact). The `--in` post-mortem mode is unchanged and stays in use by `make scrub-log`.
- `Makefile`'s `scrubbed_run` seam feeds the command's stream through `--stream`, under
  `bash -o pipefail` so the command's own exit status is what the recipe returns (a pipeline in
  `/bin/sh` would report the redactor's 0 and turn a red leg green).
- `DOCKER_RUN` sets `-e PYTHONUNBUFFERED=1` explicitly, so the container's Python children flush each
  line into the stream the redactor is already reading.
- `scripts/check_secret_output.py` gains `scrub-seam-is-not-live`: a seam that goes back to
  `> log; scrub-log --in log` is refused, so the liveness cannot be dropped by a later edit.

## Impact

- `scripts/scrub_log.py`, `Makefile`, `scripts/check_secret_output.py`.
- `tests/test_scrub_log.py` (live stream, its refusal shapes, the unbuffered wrapper, the seam end to
  end under `make`) and `tests/test_secret_output.py` (the post-mortem seam is a violation).
- `AGENTS.md` §8: the scrub-log guard row names the new rule.
- No data, no README, no contract, no schema, no make target, no workflow step.

## What is NOT covered

- The implementer's implement step still captures its agent stream to `implement.log` and prints the
  redacted tail afterwards, so its liveness is unchanged; that step is its own change (recorded in
  `findings.md` of this run).
- The bound on what a round prints: the stream mode prints every line; the `--in` mode keeps the
  bounded tail.
- Why an agent asks for input (the detach itself) is not addressed — this makes the round readable
  while it runs, not interactive.

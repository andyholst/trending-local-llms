# Proposal: seam-positional-command

Issue: #632
PR: #848

## Why

The `scrubbed_run` seam interpolates the command INSIDE a single-quoted
`bash -c` script (`Makefile:188` on the base: `bash -o pipefail -c '$(1) 2>&1 |
python3 scripts/scrub_log.py …'`). Every current caller happens to quote its
command with double quotes only, so nothing breaks today — but AGENTS.md §4
tells every prompt to put prose in single quotes inside the `-z "…"` body. One
caller following that rule closes the `-c` string early: bash parses the rest
of the prose as a command, and the leg dies with a syntax error far from its
cause. The failure is silent at the seam and lands in the wrong place.

## What Changes

- The seam passes the command to `bash -c` as a POSITIONAL argument (`$1`),
  shell-escaped with `$(subst ','\'',$(1))`, and runs it with `eval "$$1"` —
  the command text is never spliced into the script text. The capture paths
  (`$(HERMES_LOG)`, `$(HERMES_LOG_SCRUBBED)`) travel as `$2`/`$3` the same way.
- Parsing, the `bash -o pipefail` exit-status contract and the redaction stay
  identical; the positional hand-off is invisible to every existing caller.
- A new suite drives the REAL seam through a fixture Makefile with a command
  carrying single quotes — red on the old splice (measured: bash
  `unexpected EOF while looking for matching '`, exit 2), green on the new one.

## Impact

- `Makefile`: the `scrubbed_run` define (all nine callers benefit; none change).
- `tests/test_scrubbed_run_seam.py` (new file, wired into `make test` via the
  runner's per-file loop).
- `AGENTS.md` §8: a guard row for the new suite.

## Not covered

- The seam's append/round semantics (that is issue #631 / PR #846 — a separate
  change; the seam edit here keeps whichever flag set the shipped seam carries).
- Any change to `scripts/scrub_log.py` itself: its behaviour is unchanged.

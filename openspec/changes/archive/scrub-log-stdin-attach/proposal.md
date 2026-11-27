# Proposal: scrub-log-stdin-attach

Issue: #1810
PR: #1815

## Why

The four search legs pipe a talking agent into `scripts/scrub_log.py --stream`, but the
redactor ran through the shared `PYTHON_RUN` (`Makefile:344-345`), whose `docker run` has no
`-i`. The container therefore got `/dev/null` as stdin: the reader saw an immediate EOF,
printed `[scrub-log] stream: 0 line(s), 0 redaction(s)`, and the still-writing producer died
of SIGPIPE, so `PIPESTATUS[0]=141` and make reported `Error 141`. #1747 only classified that
141; it did not cause it.

## What Changes

- Add `PYTHON_RUN_STDIN` beside `PYTHON_RUN`, carrying the same flags as the byte-unchanged
  `PYTHON_RUN` plus `-i`, and use it ONLY at the redactor end of `scrubbed_run`. The shared seam
  stays stdin-detached for its ~30 other callers; no global `-i`, and a drift guard refuses any
  future flag divergence.
- Keep `bash -o pipefail`, `PIPESTATUS[0]`, `--stream --append --raw --out`, the producer's
  own exit status and #1747's SIGPIPE classification line unchanged. No retry, no SKIP, no
  classifier change, no workflow/data/schema/rulebook churn.
- Teach `check_no_bare_host_python.HARNESS_TOKENS` the scoped sibling and pin both polarities
  in `tests/test_os_agnostic_make.py`.
- Add `tests/test_scrub_log_stdin.py`: the real shipped Makefile seam and real
  `scrub_log.py --stream` driven by a stubbed container runtime that only decides whether
  stdin is attached; real `zero_hit_verdict` for the quiet/outage guard. RED on the base
  (0 lines / 141), GREEN on this head (4/4 lines, 1 redaction, rc 0).

## Impact

- Capability: `agent-log-capture` — the live redactor owns an attached stdin.
- Non-breaking: no contract, data shape, schedule, workflow, label or master push changes.
- In-container callers keep the host python's piped stdin: both harness variables are empty
  when `IN_CONTAINER` is set.

## Not covered

- No retry-on-141, no SKIP-on-empty, no change to `zero_hit_verdict` or `check_secret_output`.
- No merge, no manual `qa-validate` gate override, no new schedule.

# Proposal: search-leg-sigpipe-classify

Issue: #1747 (search-leg shape; the buildkit lock and aggregate token are separate)
PR: pending

## Why

Run `45657191852` killed all four search legs with `make: *** [Makefile:1311: search-nvidia] Error 141` after the redactor printed `[scrub-log] stream: 0 line(s), 0 redaction(s)`. The producer died with SIGPIPE and the job log named no cause — a silent empty-agent-stream failure that looks like a source outage or a flake. The issue requires the recipe to classify that shape loudly instead of hiding it behind exit 141.

## What Changes

- `scrubbed_run` in the Makefile reads the producer's `PIPESTATUS[0]` after the redaction pipeline and, on exit 141, prints `[scrub-log] FAIL: the agent stream closed with SIGPIPE (exit 141) and NO redacted line was captured — classified as quiet/agent-failed, not a source outage (issue #1747)` before returning the producer's own status. The capture contract, redaction seam and exit code are unchanged.
- `tests/test_os_agnostic_make.py::test_the_redaction_seam_classifies_a_silent_agent_sigpipe` guards the macro: RED on the old seam (no PIPESTATUS, no classification), GREEN on this head. Wired into `main()`.
- OpenSpec change + findings declared owed to the attended owner (rule 3c).

## Impact

- Capability: `no-bare-host-python` / search-leg observability (the shared redaction seam names a silent SIGPIPE).
- Additive: no data, workflow, script or rulebook byte changes; every caller of `scrubbed_run` keeps its status and captures.
- Scoped: this does NOT root-cause why the agent stream closes; that remains in #1747, as does the buildkit layer lock.

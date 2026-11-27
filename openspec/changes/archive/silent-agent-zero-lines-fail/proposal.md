# Proposal: silent-agent-zero-lines-fail

Issue: #1820
PR: #1821

## Why

The `scrubbed_run` seam piped a talking agent into `scripts/scrub_log.py --stream`, but a producer that emitted NO line and exited 0 reached the routine `[scrub-log] stream: 0 line(s), 0 redaction(s)` summary and a clean rc 0. #1747's anti-vacuous contract says a silent agent must FAIL loudly, but its only classification was the SIGPIPE(141) branch; a clean 0-line producer was neither classified nor refused. A no-post search refresh leg could therefore succeed with an empty transcript and a zero-byte artifact, hiding store staleness behind a green check.

## What Changes

- In the `--stream` branch of `scripts/scrub_log.py::main`, immediately after `lines, count = stream(...)`: when `lines == 0`, print EXACTLY ONE stderr line — `[scrub-log] FAIL: the agent stream produced 0 line(s) and exited 0 — classified quiet/agent-failed, not a source outage (issue #1820, #1747)` — and `return 3`, before the routine summary. Code 3 is free (2 is already reserved for fatal write/input errors).
- In the `Makefile` `scrubbed_run` status tail only, capture both pipeline statuses in ONE assignment (`st=${PIPESTATUS[0]} rt=${PIPESTATUS[1]}`) and promote the redactor's non-zero status only when the producer is clean (`if [ "$st" = 0 ] && [ "$rt" != 0 ]; then st="$rt"; fi`). Keep the pipe segment, `PIPESTATUS[0]`, the #1747 141 line, `exit "$st"`, the shipped `PYTHON_RUN` runner and every other byte unchanged. No new `printf`.
- Add RED-first guards to the already-wired `tests/test_scrubbed_run_seam.py`: a silent `quiet:` producer (RED on the base, GREEN here), a talking 3-line control, and a byte-untouched guard for the shipped seam contract and #1747 141 line. G4 (quiet/1 vs outage/0) is already locked by `tests/test_firecrawl_fetch.py`.
- Write `findings/1820.md` and this additive OpenSpec change; regenerate `OPENSPEC.md` with `scripts/openspec_index.py --write`.

## Impact

- Capability: `agent-log-capture` — additive requirement, no new capability, based on the current `origin/master` seam (the #1808 stdin fix is already there; this change does not alter it).
- Non-breaking: a producer that emits at least one line keeps its existing path byte-for-byte; no schema, data, contract, workflow, schedule or rulebook change.
- Distinctions preserved: the refusal checks the STREAM COUNT, never search content. A talking producer that reports a full outage still reaches `zero_hit_verdict` → `outage`/0; a reachable-mirror no-hit stays `quiet`/1; the 141 SIGPIPE line and a non-zero producer status are unchanged.

## Not covered

- No retry, retry-all, SKIP, classifier rewrite, new `printf`, rule amendment, label, schedule, cron or master push.
- No merge by hand; `qa-validate` merges when `validate` and `live-smoke` are green on the exact head.

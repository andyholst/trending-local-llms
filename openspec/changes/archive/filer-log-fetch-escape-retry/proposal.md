# Proposal: filer-log-fetch-escape-retry

Issue: #923 (measured: all 12 issues #822–#833 filed UNDIAGNOSED on 2026-11-12 — every log fetch answered `the response contains terminal escape sequences; pass --allow-escape-sequences to output it anyway`)
PR: #924

## Why

Rule 6r exists so a red main pipeline diagnoses ITSELF: the filer reads the failing job's log and
files the issue carrying its error block. But `scripts/pipeline_failure_issue.py::fetch_log` calls
`gh api repos/…/actions/jobs/<id>/logs` plainly, and gh REFUSES to print any log containing
terminal escape sequences — which is exactly what GitHub Actions' colored `##[error]` decoration
writes. Measured on the live queue: all 12 failures filed from the 2026-11-12 sweep carry no error
block at all, only `(the log could not be read: … terminal escape sequences …)`. The diagnosis half
of rule 6r is therefore blind on a large share of real failures: no error text on the issue, no
`make <target>` reproduction, and `make pipeline-failure-guard-check` cannot demand a guard test
for an error it never named. gh itself names the remedy in its refusal message.

## What Changes

- **`scripts/pipeline_failure_issue.py`**: `fetch_log`'s ONE retry carries gh's own suggested
  `--allow-escape-sequences` flag, and the fetched text is passed through a new
  `strip_terminal_escapes` helper (one implementation, module-level) BEFORE the tail-bound and
  before `extract_error_block` / the scrubber see it — so escape bytes can never reach an issue
  body. A genuine two-attempt failure still raises the loud UNDIAGNOSED error.
- **`tests/test_pipeline_failure_issue.py`**: a fixture `gh` that answers the PLAIN fetch with the
  exact measured refusal and answers the flag-carrying retry with an ANSI-colored log containing
  `##[error]` lines; the filed issue must carry the error lines and ZERO escape characters. The
  existing UNDIAGNOSED path stays pinned. The new tests go RED against the pre-change `fetch_log`.

## Impact

- Affected capability: `alarms` (rule 6r filer).
- Affected code: `scripts/pipeline_failure_issue.py`, `tests/test_pipeline_failure_issue.py`.
- No contract, data-format, Makefile-target, workflow or image change.

## Not covered

- Retroactive re-diagnosis of the 12 already-filed UNDIAGNOSED issues (#822–#833): their logs
  remain fetchable and a follow-up change can backfill their error blocks once the fetch is fixed.

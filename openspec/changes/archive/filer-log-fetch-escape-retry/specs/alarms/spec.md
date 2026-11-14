# Spec delta: alarms — escape-sequence-tolerant log fetch (issue #923)

## ADDED Requirements

### Requirement: The filer reads escape-bearing job logs with gh's own suggested retry

`make pipeline-failure-issue` SHALL diagnose a failing job whose log contains terminal escape
sequences: `fetch_log` tries the plain `gh api …/logs` fetch first, and its ONE retry carries
`--allow-escape-sequences`; the returned text is stripped of terminal escape sequences (CSI/OSC
and bare ESC forms, via one `strip_terminal_escapes` helper) before tail-bounding and before
`extract_error_block` sees it. A log fetched this way produces a normal diagnosed issue; no
escape character may appear in the filed body. A job whose log fails twice for any other reason
still files UNDIAGNOSED, loudly.

#### Scenario: a colored log is diagnosed on the retry

Given a failing job whose plain log fetch is refused with gh's measured message (`the response
contains terminal escape sequences; pass --allow-escape-sequences to output it anyway`)
When the filer runs `make pipeline-failure-issue` against it
Then the retry carries `--allow-escape-sequences`
And the filed issue body contains the log's `##[error]` lines and zero escape characters
And the ledger records the diagnosis, not UNDIAGNOSED
- **Test:** tests/test_pipeline_failure_issue.py::test_an_escape_refused_log_is_diagnosed_on_the_flag_retry

#### Scenario: stripping happens before extraction, so error lines survive intact

Given a log whose error lines are wrapped in ANSI color codes (GitHub Actions' `##[error]`
decoration)
When `extract_error_block` runs on the fetched text
Then it sees the lines with their escape sequences removed and matches them unchanged
And `strip_terminal_escapes` removes CSI/OSC/bare-ESC forms and leaves ordinary text untouched
- **Test:** tests/test_pipeline_failure_issue.py::test_strip_terminal_escapes_leaves_plain_text_intact

#### Scenario: a genuinely unreadable log still files UNDIAGNOSED

Given a failing job whose log fetch fails twice even with `--allow-escape-sequences`
When the filer files its issue
Then the body says UNDIAGNOSED and quotes the fetch error
And nothing is skipped silently
- **Test:** tests/test_pipeline_failure_issue.py::test_undiagnosed_filing_is_loud_never_a_skip

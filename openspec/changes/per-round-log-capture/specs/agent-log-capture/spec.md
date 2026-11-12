## ADDED Requirements

### Requirement: The agent-log capture keeps every invocation of a run

The `scrubbed_run` seam SHALL append each invocation's capture — raw and
redacted — behind a timestamped, pid-stamped delimiter instead of truncating
the previous one, so a multi-round caller (`scripts/fix_loop.sh`'s rounds of
`make fix`, the `make search` legs) leaves EVERY round's transcript in the
artifact file, including a detached round's message. Redaction SHALL apply
identically to every appended segment.

#### Scenario: two rounds through the real seam leave both transcripts

Given a fixture Makefile that embeds the shipped `scrubbed_run` seam and two
targets that each stream a line (one printing a planted secret value, the
second printing a marker and exiting non-zero),
When both are run in the same workspace,
Then the redacted artifact and the raw capture BOTH contain both rounds'
lines behind two `===== [scrub-log] capture … =====` delimiters,
And the planted value appears in NO line of the redacted artifact,
And the second round's failing exit status is preserved.

- **Test:** tests/test_scrub_log.py::test_two_rounds_through_the_seam_leave_both_transcripts

#### Scenario: append is opt-in per invocation and never weakens the default

Given three sequential `--stream` invocations against the same capture paths
(plain, `--append`, plain),
When the invocations complete,
Then the first plain invocation's file is untouched by delimiters,
And the appended invocation PRESERVES the earlier content behind its capture
header,
And the later plain invocation truncates as before — append is per invocation.

- **Test:** tests/test_scrub_log.py::test_append_mode_preserves_an_earlier_stream_and_defaults_to_truncate

### Requirement: The fix loop's transcript reaches the QA artifact

The implementer's QA artifact SHALL upload the REDACTED fix-loop capture
(`hermes-run.scrubbed.log`) alongside `implement.scrubbed.log`, and SHALL
never upload a raw capture.

#### Scenario: the shipped issue-bot artifact names both redacted logs and no raw one

Given the shipped `.github/workflows/issue-bot.yml`,
When its `Upload the QA report` step's `path:` list is read,
Then it names `qa-report.txt`, `implement.scrubbed.log` and
`hermes-run.scrubbed.log`,
And it names no raw capture (`implement.log`, `hermes-run.log`).

- **Test:** tests/test_scrub_log.py::test_the_target_is_wired_into_the_repo

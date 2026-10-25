# fix-round-transcript

## ADDED Requirements

### Requirement: A fix-bot run uploads the redacted agent transcript

The fix-bot's QA artifact MUST include `hermes-run.scrubbed.log` beside `qa-report.txt`, always and
with `if-no-files-found: ignore`, and MUST NOT upload the raw `hermes-run.log`.

#### Scenario: the shipped artifact carries the scrubbed log and not the raw one

- **Given** `.github/workflows/fix-bot.yml`'s `fix` job
- **When** its upload-artifact step is read
- **Then** the `path` names `hermes-run.scrubbed.log`
- **And** it does not name the raw `hermes-run.log`
- **Test:** `tests/test_workflows.py::test_a_detached_fix_round_leaves_its_transcript_behind`

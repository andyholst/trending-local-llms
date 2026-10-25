# Proposal — fix-round transcript

Issue: #566

## Why

fix-bot run 40180788039 died in all three rounds with `Input required; detached without cancelling`
(rc=3) and its only artifact was `qa-report.txt`. `make scrub-log` already writes
`hermes-run.scrubbed.log` in the same workspace, and it was never uploaded — so what the model asked
is unknowable, and every diagnosis of this fleet's most common failure is inference from a three-line
tail. Extending the `pr-fix` skill (#560/#561) did not change the detach, so the next step needs the
transcript.

## What changes

`fix-bot.yml`'s QA artifact carries `hermes-run.scrubbed.log` beside `qa-report.txt`. The REDACTED
copy is the one uploaded; `hermes-run.log` (the raw capture) never is — rule 3d.

## Impact

- `.github/workflows/fix-bot.yml` — the artifact's `path` list.
- `tests/test_workflows.py::test_a_detached_fix_round_leaves_its_transcript_behind`.

## What is NOT covered

- It does not stop the detach; it makes the next one diagnosable.
- The issue-bot's artifact set is unchanged (its leg leaves `implement.log`, already scrubbed and
  uploaded by its own step).

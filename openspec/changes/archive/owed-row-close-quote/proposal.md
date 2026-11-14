# Closing an owed-row issue quotes the ledger on the thread

**Issue:** [#766](https://github.com/andyholst/trending-local-llms/issues/766)
PR: #922

## Why

The #523 ledger reads OPEN issues only. The backlog #523 named (#212, #314,
#322, #324, #369, #380, #385, #405) is 8/8 closed, and the repo cannot show
which AGENTS.md line covered each one — a closed row is invisible to the
ledger. #766's Done-when: a documented close path quotes the marker's landed
line on the issue at close time, as an extension of the implementer's verdict
comments, not a new bot.

## What Changes

- `scripts/owed_rows_check.py` splits its landing decision into a pure
  `row_states(parsed, agents_lines, secs)` (the report walks it; the check
  report output is byte-identical), and adds `owed_row_close_note(repo, issue,
  agents_file)`: the ONE close-time quote — LANDED with its
  `AGENTS.md:<line>` proof, or OUTSTANDING. A thread/rulebook read failure, a
  malformed marker, or a marker naming a missing section RAISES.
- `scripts/issue_verdict.py` quotes that note IN the `close` verdict comment:
  a close on an issue with owed rows appends an "Owed rows" section; a broken
  ledger read REFUSES the close (exit 2, nothing written) — a broken read must
  never launder a close. A new `--agents-file` (default `AGENTS.md`) names the
  rulebook. Issues without owed rows close exactly as before.
- Tests: `tests/test_owed_rows.py` locks report↔note parity (same states, same
  landed line, refusal raises); `tests/test_issue_triage.py` locks the five
  close-path outcomes end to end (landed quoted with line, outstanding named
  and still closed, missing section refused exit 2, malformed refused, plain
  close unchanged).

## Impact

- Capability `agents-guard-registry` gains the close-time quote requirement.
- No new bot, no new make target: `make issue-verdict` is already wired and
  already runs in the implement job.
- AGENTS.md: a §8 guard row (rule 6c) and a §6e sentence naming the close
  quote — the §6e half is the rule-3c review-required part, declared in a
  comment on #766.

## Not covered

- Backfilling the 8 already-closed backlog issues with quotes (their landed
  lines are unrecoverable history; #523's own close comment already records
  that).
- A reviewer-side (`issue-review-bot`) owed-row verdict — the reviewer keeps
  its own verdict path; only the implementer's `close` gained the quote.

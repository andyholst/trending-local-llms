# fix-loop-scratch

## ADDED Requirements

### Requirement: The fix loop writes no scratch file into the checkout

The fix loop's between-round notes MUST live outside the repository worktree, so no
run of the loop can leave a file a bot's `git add -A` commit step would stage. The
notes are still folded into the report the loop owns, so a timed-out round and a
no-progress round remain visible in `qa-report.txt`.

#### Scenario: a timed-out round leaves no file beside the report

- **Given** the REAL fix loop run with the production report path (`QA_REPORT=qa-report.txt`, relative to the checkout) and a Hermes round that outlives `HERMES_FIX_TIMEOUT`
- **When** the loop aborts that round and writes its note
- **Then** the note is recorded in `qa-report.txt` and no `*.notes` file exists beside it
- **Test:** tests/test_fix_loop.py::test_scratch_notes_stay_out_of_the_tree

### Requirement: The bot commit step never pushes the report or its siblings

The commit step MUST NOT commit `qa-report.txt` or any `qa-report.txt.*` sibling (the
loop's scratch class), whatever `git add -A` picks up.

#### Scenario: the loop's notes file is present when the bot commits

- **Given** the REAL commit+push script, run in a temp clone whose `.gitignore` is the repository's, with `qa-report.txt`, `qa-report.txt.notes` and `comment.md` present
- **When** the loop is green and the step commits and pushes its fix
- **Then** the pushed commit carries the fix and none of those three files
- **Test:** tests/test_workflows.py::test_fix_bot_push_behaviour

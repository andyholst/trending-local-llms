# fix-bot-repair-loop

## ADDED Requirements

### Requirement: One Hermes round is bounded, and its timeout is reported

Every Hermes repair round MUST run under an explicit timeout
(`HERMES_FIX_TIMEOUT`), so a round that never returns is aborted BY THE LOOP and
reported — in the loop's log and in the QA report the PR comment shows — instead of
consuming the job's whole budget and leaving the PR with nothing.

WHEN a Hermes round exceeds its bound,
THEN the loop aborts that round, records the timeout, and continues with its own
round budget intact.

#### Scenario: a hung round is aborted by the loop and recorded

- **Given** a `make fix` that never returns inside `HERMES_FIX_TIMEOUT` seconds
- **When** the loop runs its rounds
- **Then** each round is aborted at the bound, the timeout is named in the log and in `qa-report.txt`, and the loop still ends through its own exit path
- **Test:** `tests/test_fix_loop.py::test_a_hung_round_is_bounded_by_the_loop`

### Requirement: The Hermes call itself is bounded inside the container

`make fix` MUST bound the `hermes` invocation it runs, so the container dies with the
round rather than being orphaned; the loop's own timeout is the backstop. Both read
the SAME variable, so the two bounds cannot disagree.

WHEN the fix target runs,
THEN the hermes call it executes carries a timeout argument.

#### Scenario: the fix recipe bounds its hermes call

- **Given** the `Makefile`'s `fix` and `_fix` recipes
- **When** `make -n _fix` is expanded
- **Then** the ONE hermes command it yields is prefixed by a `timeout`
- **Test:** `tests/test_hermes_prompts.py::test_make_dry_run_single_hermes_command`

### Requirement: The base is merged before any LLM round

The loop MUST fetch the base branch and merge it into the branch BEFORE the first
Hermes round when the branch is behind, because a red refresh PR is usually red
because the base moved. A failure the base already fixed MUST cost zero LLM rounds.
The merge MUST never be fatal: no checkout, an unreachable remote, or a conflicting
merge leaves the branch as it was, and says so.

WHEN the branch is behind its base,
THEN the base is merged in first and the checks are re-run before any LLM round.

#### Scenario: a behind branch is merged before any LLM round

- **Given** a real repository whose base branch has moved ahead of the checked-out branch
- **When** the loop starts
- **Then** the branch contains the base's commits, the merge is reported, no LLM round ran, and the loop is green
- **Test:** `tests/test_fix_loop.py::test_the_base_is_merged_before_any_llm_round`

#### Scenario: outside a checkout the merge is a loud no-op

- **Given** a working directory that is not a git checkout
- **When** the loop starts
- **Then** it says the base merge is skipped and still runs every check
- **Test:** `tests/test_fix_loop.py::test_base_merge_is_skipped_outside_a_checkout`

### Requirement: A round that changes nothing does not buy the next one

When a round leaves the failure byte-identical AND the working tree untouched, the
loop MUST stop and report it rather than spending its remaining rounds on the same
failure. The check MUST be asked only inside a git checkout, so a control-flow
fixture can never trip it.

WHEN a round produces neither a different failure nor a changed tree,
THEN the loop exits red with the no-progress reason recorded.

#### Scenario: no progress is detected inside a git checkout

- **Given** a git checkout in which a round changes nothing and the failure repeats
- **When** the loop re-checks
- **Then** it stops, records that the round made no progress, and does not run the remaining rounds
- **Test:** `tests/test_fix_loop.py::test_a_round_that_changes_nothing_stops_the_loop` (and `tests/test_fix_loop.py::test_red_forever_gives_up`, whose fixture is not a checkout, so the round cap still governs)

### Requirement: The loop's own notes survive the report's per-round truncation

The QA report is truncated at the start of every round, so a note the loop writes
between rounds (a timeout, a no-progress round) MUST be accumulated separately and
folded into the report, or it is lost before the PR comment can show it.

WHEN the loop records a note and then runs another round's checks,
THEN the note is still in the QA report afterwards.

#### Scenario: a recorded timeout is still in the report

- **Given** a timed-out round and a further round of checks
- **When** the report is read
- **Then** it still names the timeout
- **Test:** `tests/test_fix_loop.py::test_a_hung_round_is_bounded_by_the_loop`

# bot-coordination

## ADDED Requirements

### Requirement: A sweep that dies before its verdict posts its own outcome on the picked issue

`issue-bot.yml`'s `implement` job MUST run one `always()` step that calls `make issue-outcome`
when the run resolved an open issue, did NOT find it closed while in flight, and produced no
verdict (`steps.verdict.outputs.verdict == ''`). The comment MUST be written through
`gh issue comment` with the default `github.token` in a job that declares `issues: write`.

#### Scenario: an implement job that died before its verdict

- **Given** a run that resolved issue 498 as open and whose `verdict` step never produced a value
- **When** the shipped `run:` block is executed with `make issue-outcome` stubbed
- **Then** the step runs, passes the run id, the run URL, the branch and the per-stage outcomes, and uses `${{ github.token }}`
- **Test:** tests/test_workflows.py::test_issue_bot

#### Scenario: a run that already has an outcome stays quiet

- **Given** the same step in `issue-bot.yml`
- **When** its condition is inspected
- **Then** it requires `steps.verdict.outputs.verdict == ''`, so an `implement`, `refine` or `close` run posts only what its own step posts, and a closed-while-in-flight run posts only the already-fixed notice
- **Test:** tests/test_workflows.py::test_issue_bot

### Requirement: The outcome comment is once per run and carries the registered marker

`sweep_outcome.owed()` MUST answer False when the run implemented nothing, when the issue closed
while in flight, and when the verdict was `implement`, `refine` or `close`; True only when the run
stopped before its verdict. The body MUST start with the marker
`<!-- issue-bot-outcome: <ISO8601Z> run=<id> -->` taken from `scripts/bot_markers.py`, and
`--post` MUST refuse to write a second comment carrying this run's marker (or an
`issue-bot-already-fixed` notice for this run).

#### Scenario: the decision matrix

- **Given** the four states a finished-or-dead run can be in
- **When** `owed()` is asked
- **Then** only "implemented, not closed, no verdict" is True, and each refusal names why
- **Test:** tests/test_sweep_outcome.py::test_the_decision_names_every_refusal

#### Scenario: a re-run of the same run id

- **Given** an issue whose comments already carry `issue-bot-outcome` for run 40194644167
- **When** `--post` is called again for that run id
- **Then** it posts nothing and says so, while a comment from an EARLIER run does not suppress it
- **Test:** tests/test_sweep_outcome.py::test_a_second_post_for_the_same_run_writes_nothing

#### Scenario: an unreadable or missing issue is loud

- **Given** no `--issue`, a non-numeric `--issue`, or a `gh` that fails
- **When** the script runs
- **Then** it exits 2 and names what it could not read — never a silent pass
- **Test:** tests/test_sweep_outcome.py::test_a_missing_or_unreadable_issue_is_loud

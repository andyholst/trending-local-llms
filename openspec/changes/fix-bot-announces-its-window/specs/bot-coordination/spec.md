# bot-coordination

## ADDED Requirements

### Requirement: fix-bot announces its window before it reads the branch

A fix-bot run SHALL post ONE comment on the PR it repairs — carrying the shared
`<!-- fix-bot-start: <ISO8601Z> run=<id> -->` marker, the branch and the run URL — **before** any
step reads the PR branch, using the default `github.token`.

#### Scenario: the announcement precedes the branch read

- **GIVEN** the `fix` job's steps in order,
- **WHEN** the position of the window announcement is compared with the checkout,
- **THEN** the announcement comes first, so a reader of the PR sees the repair in flight before the
  branch it will change is read.

- **Test:** `tests/test_workflows.py::test_fix_bot_announces_its_window`

#### Scenario: the marker is the registered one and names the run

- **GIVEN** the announcement step's script,
- **WHEN** it is read,
- **THEN** it writes `<!-- fix-bot-start:` with the branch and `GITHUB_RUN_ID`, so the marker is the
  one `scripts/bot_markers.py` parses and a reader can find the run that posted it.

- **Test:** `tests/test_workflows.py::test_fix_bot_announces_its_window`

### Requirement: the announcement uses a token that can comment

The announcement SHALL use the default `github.token` with the `issues: write` permission, never the
owner PAT.

#### Scenario: the PAT cannot comment

- **GIVEN** the owner PAT is scoped to Actions/Contents/Pull-requests and cannot comment
  (`Resource not accessible by personal access token (addComment)`, measured on #124),
- **WHEN** the announcement's `GH_TOKEN` and the workflow's `permissions:` are read,
- **THEN** the token is `${{ github.token }}` and `issues: write` is granted.

- **Test:** `tests/test_workflows.py::test_fix_bot_announces_its_window`

### Requirement: the announcement leaves no file behind

The announcement SHALL deliver its body without writing a file into the checkout, so the push step's
`git add -A` can never commit it.

#### Scenario: the body arrives on stdin

- **GIVEN** the announcement step's script,
- **WHEN** it is read,
- **THEN** it pipes the body to `gh pr comment … --body-file -` and writes no `.md` file.

- **Test:** `tests/test_workflows.py::test_fix_bot_announces_its_window`

### Requirement: the window is closed on every path

The run's outcome comment SHALL carry `<!-- fix-bot-end: <ISO8601Z> run=<id> -->` and SHALL run
under `if: always()`, so a repair that dies mid-way still ends with a closing timestamp.

#### Scenario: a failed run still closes its window

- **GIVEN** the outcome comment step,
- **WHEN** its condition and body are read,
- **THEN** the condition is `always()` and the body carries the end marker with the run id.

- **Test:** `tests/test_workflows.py::test_fix_bot_announces_its_window`

### Requirement: the registry knows the writer exists

The shared marker registry SHALL list `(fix-bot, start)` and `(fix-bot, end)` as written, so its own
test requires a writer in the tree.

#### Scenario: the declared markers become written

- **GIVEN** `scripts/bot_markers.py`,
- **WHEN** its `WRITTEN` and `DECLARED_BY` sets are read,
- **THEN** both fix-bot markers are in `WRITTEN`, are absent from `DECLARED_BY`, and each appears in
  the tree.

- **Test:** `tests/test_bot_markers.py::test_every_written_marker_has_a_writer`

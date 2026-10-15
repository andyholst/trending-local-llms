# code-review

## ADDED Requirements

### Requirement: the deterministic checks report the real defects

The scan SHALL report, with evidence, a workflow step that runs a repo script directly instead of a
`make` target, two fixed crons sharing a minute+hour slot on overlapping days, and a
`workflow_call`-only file nothing references, and SHALL report nothing for a clean tree.

#### Scenario: an inline repo-script step is reported

- **GIVEN** a workflow whose `run:` invokes `python3 scripts/…`,
- **WHEN** the inline-script check runs,
- **THEN** the finding names that workflow, and a `make <target>` step is not reported.

- **Test:** `tests/test_code_review.py::test_an_inline_repo_script_is_reported`

#### Scenario: two colliding crons are reported

- **GIVEN** two workflows scheduled at `23 7 * * 1`,
- **WHEN** the cron-collision check runs,
- **THEN** the pair is reported, and distinct minutes are not.

- **Test:** `tests/test_code_review.py::test_two_colliding_crons_are_reported`

### Requirement: the bot's only writes are issues

The filer SHALL create at most one issue per NEW finding, marker-deduplicated and capped per run,
and SHALL use no `gh` verb other than `issue list` and `issue create` — it never edits a file, never
opens a PR, never merges, never comments on anyone's PR.

#### Scenario: a re-run on an unchanged tree files nothing

- **GIVEN** a finding whose marker is already in an issue body,
- **WHEN** the filer runs,
- **THEN** it files nothing, and a fresh key is filed up to the cap.

- **Test:** `tests/test_code_review.py::test_the_filer_is_marker_deduped_and_capped`

#### Scenario: the narrowest promise

- **GIVEN** the filer with a fake `gh` recording every argv,
- **WHEN** it files a finding,
- **THEN** the only verbs used are `issue list` and `issue create`.

- **Test:** `tests/test_code_review.py::test_the_bot_only_lists_and_creates_issues`

### Requirement: the workflow guards first and calls the make targets

The workflow's `guard` job SHALL be first and admit the owner, a write+ collaborator and the bot
itself with the `schedule` bypass; the `review` job SHALL call `make code-review-scan` and
`make code-review-file` and SHALL NOT invoke a repo script directly.

#### Scenario: the workflow is wired as the rule requires

- **GIVEN** `.github/workflows/code-review-bot.yml`,
- **WHEN** its jobs and steps are read,
- **THEN** the guard is first and the two make targets are the only repo commands.

- **Test:** `tests/test_code_review.py::test_the_workflow_guards_first_and_calls_the_make_targets`

### Requirement: the checks do not flag the bot's own workflow

Run over this repo, no check SHALL report the code-review bot's own workflow file.

#### Scenario: self-consistency

- **GIVEN** the real repository,
- **WHEN** the deterministic checks run over it,
- **THEN** none of them names `code-review-bot.yml`.

- **Test:** `tests/test_code_review.py::test_no_check_flags_the_bots_own_workflow`

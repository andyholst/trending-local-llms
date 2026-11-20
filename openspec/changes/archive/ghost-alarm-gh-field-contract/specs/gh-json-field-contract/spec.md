## ADDED Requirements

### Requirement: Every gh `--json` field request is built through one recorded contract

`scripts/gh_json_fields.py` SHALL hold the recorded set of fields `gh run list`
answers, and SHALL refuse — at request-build time — any field list that names a
field gh cannot answer, naming the command and the field. A command the contract
has not recorded SHALL get no opinion (an unrecorded request can never produce a
false red). The module SHALL also expose `check_argv`, which validates a whole
`gh … --json …` argv.

#### Scenario: The pre-change ghost request is refused at build time

- **Given** the field list `scripts/ghost_run_alarm.py` asked before issue #1158
  (it ends in `htmlUrl`)
- **When** `gh_json_fields.request("run list", …)` builds the request
- **Then** the call raises, and the message names `run list` and `htmlUrl`
- **Test:** tests/test_gh_json_fields.py::test_the_seam_refuses_a_field_gh_cannot_answer

#### Scenario: The recorded set is gh's own answer set

- **Given** the field list gh prints as its `Available fields` for `run list`
- **When** the contract is compared with that recorded list
- **Then** they are equal, `url` is in the set and `htmlUrl` is not, and an
  unrecorded command is left alone
- **Test:** tests/test_gh_json_fields.py::test_the_field_set_is_the_real_cli_answer

### Requirement: The scan runs in CI and refuses a field gh cannot answer anywhere in scripts/

`make check-gh-json-fields` (internal `_check-gh-json-fields`) SHALL run
`scripts/gh_json_fields.py --scan` over every `gh run list` call in `scripts/`,
naming the file, the line and the unknown field, and SHALL be bundled into
`make lint`, which `qa-validate`'s `validate` job runs. A `--json` field list the
scan cannot read, and a tree without `scripts/`, SHALL fail loudly (exit 1 /
exit 2), never pass silently.

#### Scenario: The scan is green here and red on the old shape

- **Given** this repository's `scripts/` tree, and a scratch tree holding the
  pre-change ghost field list
- **When** `--scan` runs on each
- **Then** this repository exits 0, the scratch tree exits 1 naming
  `file:line` and `htmlUrl`, an unreadable `--json` expression is a finding, and
  a tree with no `scripts/` exits 2
- **Test:** tests/test_gh_json_fields.py::test_the_tree_scan_is_green_here_and_red_on_the_old_shape

#### Scenario: Every CLI mode decides loudly

- **Given** the `--scan` and `--check-argv` modes
- **When** each is run against a good tree, a planted bad tree, an unreadable
  tree and a gh-refused argv
- **Then** they exit 0, 1, 2 and 1 respectively, each naming what it refused
- **Test:** tests/test_gh_json_fields.py::test_the_cli_modes_decide_loudly

#### Scenario: The gate is wired where CI runs it

- **Given** the Makefile and the pipelines
- **When** the wiring is read
- **Then** `_check-gh-json-fields` runs the script, `check-gh-json-fields`
  delegates to it, `make lint` bundles it, `qa-validate` runs `make lint`, and no
  workflow reaches the script past the Makefile
- **Test:** tests/test_gh_json_fields.py::test_the_scan_is_wired_where_ci_runs_it

### Requirement: The ghost-run alarm reads gh through the contract and checks the answer's shape

`scripts/ghost_run_alarm.py` SHALL build its `run list` request through
`gh_json_fields.request` (asking for `url`, never `htmlUrl`), SHALL validate every
gh argv through `check_argv` before calling gh, and SHALL treat an answer whose
shape is not what the command answers — an array where an array is expected, a
`{"jobs": […]}` object where the jobs array is expected — as a failed read. A
`gh` binary that is not runnable SHALL be the same failed read. Every failed read
SHALL exit 2 with the `READ FAILED` line, never a verdict built on `[]` and never
a traceback.

#### Scenario: The alarm asks only for fields gh can answer

- **Given** the alarm's `RUNS_JSON` and the gh argvs it issues
- **When** they are validated against the contract
- **Then** no unknown field remains, the request is built through the seam, and
  the printed ghost line uses the `url` gh answered
- **Test:** tests/test_gh_json_fields.py::test_the_ghost_alarm_builds_its_request_through_the_seam

#### Scenario: An answer of the wrong shape is a loud read failure, not a ghost verdict

- **Given** a planted `run view` answer with no `jobs` array, and a planted answer
  that is an array where gh answers an object
- **When** the alarm reads it
- **Then** each exits 2 naming the bad shape and the run is NOT reported as a
  ghost, while a real `{"jobs": []}` answer is still flagged as the ghost it is
- **Test:** tests/test_auto_merge_rebase.py::test_the_ghost_alarm_refuses_a_gh_answer_of_the_wrong_shape

#### Scenario: A missing gh is a failed read, not a traceback

- **Given** an environment whose PATH holds no `gh`
- **When** the alarm runs
- **Then** it exits 2 printing the `READ FAILED` line and no traceback
- **Test:** tests/test_auto_merge_rebase.py::test_a_missing_gh_is_a_loud_read_failure_not_a_traceback

### Requirement: The ghost alarm's test stub cannot answer a query the real gh refuses

The stub `gh` in `tests/test_auto_merge_rebase.py` SHALL validate every `--json`
request through `gh_json_fields.check_argv`, so a request the real CLI refuses
fails in the test exactly as it fails in production (rule 6m: an external system
stood in for, not a contract-free echo).

#### Scenario: The stub refuses htmlUrl and answers url

- **Given** the pre-change field list and the fixed one
- **When** each is sent to the stub `gh`
- **Then** the first exits non-zero naming `Unknown JSON field`, the second is
  answered, and `run view --json jobs` (unrecorded) is answered unchanged
- **Test:** tests/test_gh_json_fields.py::test_the_ghost_stub_cannot_answer_a_query_the_real_gh_refuses

#### Scenario: The ghost verdict still flags a real zero-job run

- **Given** a planted `pull_request` queue with `action_required`-zero-jobs and
  `success`-zero-jobs runs beside runs with jobs, a `skipped` run and an
  out-of-window run
- **When** `make ghost-run-alarm`'s script runs against the stub
- **Then** it exits 1 naming exactly the ghosts, prints the `url` gh answered, and
  a failed GitHub read is exit 2
- **Test:** tests/test_auto_merge_rebase.py::test_ghost_alarm_flags_completed_pr_runs_with_zero_jobs

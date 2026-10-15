# secret-output-guard

## ADDED Requirements

### Requirement: No secret VALUE reaches a log, a process list or a committed file

`scripts/check_secret_output.py` MUST fail closed when any text file a reviewer
would call part of the repo (make recipes, workflows, shell, python, yaml) lets a
secret-shaped variable's **value** leave the process: printed (`echo
"$NOUS_API_KEY"`), passed on a command line (`-e KEY=$KEY`,
`--build-arg KEY=$KEY`), read under a shell xtrace (`set -x` beside a key read),
dumped (bare `env`/`printenv`), interpolated into a workflow `run:` block
(`${{ secrets.X }}`), or committed as a credential-shaped literal. The guard
reports each violation with its file:line and exits non-zero. It scans the
secret-shaped variables this repo uses by NAME only — a value never appears in
the source.

WHEN a file prints, argv-passes, xtraces, dumps or commits a secret-shaped
variable's value,
THEN `make check-secret-output` reports the file:line and exits non-zero.

#### Scenario: a value printed to the log is a violation

- **Given** a shell file that runs `echo "token: $NOUS_API_KEY"`
- **When** the guard scans it
- **Then** it reports the line as `prints-secret-value` and exits non-zero
- **Test:** `tests/test_secret_output.py::test_echoing_a_secret_value_is_a_violation`

#### Scenario: a value on a command line is a violation

- **Given** a recipe line `docker run -e HF_TOKEN=$HF_TOKEN`
- **When** the guard scans it
- **Then** it reports `value-in-argv` and exits non-zero
- **Test:** `tests/test_secret_output.py::test_a_secret_value_on_the_command_line_is_a_violation`

#### Scenario: a `${{ secrets.X }}` in a `run:` block is a violation

- **Given** a workflow whose `run: |` block contains `Authorization: Bearer ${{ secrets.HF_TOKEN }}`
- **When** the guard scans it
- **Then** it reports `secrets-in-run-block` and exits non-zero
- **Test:** `tests/test_secret_output.py::test_a_secret_interpolated_into_a_run_block_is_a_violation`

#### Scenario: `set -x` beside a key read is a violation

- **Given** a shell script that sets `set -x` and also expands `$HF_TOKEN`
- **When** the guard scans it
- **Then** it reports `xtrace-with-secrets` and exits non-zero
- **Test:** `tests/test_secret_output.py::test_xtrace_in_a_file_that_reads_a_secret_is_a_violation`

#### Scenario: a bare environment dump is a violation

- **Given** a line that runs a bare `env` whose output reaches a log
- **When** the guard scans it
- **Then** it reports `env-dump` and exits non-zero
- **Test:** `tests/test_secret_output.py::test_a_bare_environment_dump_is_a_violation`

#### Scenario: a credential-shaped literal is a violation unless marked

- **Given** a file containing `hf_<20+ alphanumeric>` with no test-value marker
- **When** the guard scans it
- **Then** it reports `key-shaped-literal`; a second file with the same string plus the `secret-output: test value` marker passes
- **Test:** `tests/test_secret_output.py::test_a_credential_shaped_literal_is_a_violation`, `tests/test_secret_output.py::test_the_marker_declares_deliberate_test_values`

#### Scenario: passing the name through `env:` is not a violation

- **Given** a workflow step that reads the secret via an `env:` entry (`env: { HF_TOKEN: ${{ secrets.HF_TOKEN }} }`)
- **When** the guard scans it
- **Then** it finds no `secrets-in-run-block` and no `value-in-argv` violation
- **Test:** `tests/test_secret_output.py::test_a_secret_passed_through_env_is_not_a_violation`

### Requirement: The guard is a CI gate, and this repo cannot violate its own rule

`make check-secret-output` MUST be a step of `qa-validate`'s `validate` job (next
to `make secret-scan`), and `tests/test_secret_output.py` MUST run under `make
test` — a gate no pipeline executes is a defect (rule 6d). The guard MUST also
pass over THIS repository, because a rule the repo itself violates is not a rule.

WHEN a PR is opened,
THEN `qa-validate`'s `validate` job runs `make check-secret-output`, and the
guard's own test file runs under `make test`.

#### Scenario: the gate is on every PR

- **Given** the PR pipeline definition and the Makefile
- **When** their wiring is read
- **Then** the `validate` job runs `make check-secret-output` beside `make secret-scan`, and `make test` runs `tests/test_secret_output.py`
- **Test:** `tests/test_workflows.py::test_secret_output_guard_wired_into_qa_validate`, `tests/test_secret_output.py::test_the_guard_is_wired_into_the_repo`

#### Scenario: a rule the repo violates is red

- **Given** the guard run over this repository
- **When** any file in the tree violates a rule
- **Then** the run is non-zero
- **Test:** `tests/test_secret_output.py::test_this_repository_never_prints_a_secret_value`

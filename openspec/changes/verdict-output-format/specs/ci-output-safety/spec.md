# ci-output-safety

## ADDED Requirements

### Requirement: A step writes `key=value` into the output file, never a whole stream

A workflow `run:` block MUST NOT redirect a command's whole stdout into
`$GITHUB_OUTPUT`. It MUST capture the output and write only the keys it needs, so a
line the command prints — `make` echoing its recipe, a diagnostic, a value nobody meant
to publish — can never reach the output file. A pipe inside a quoted argument
(`echo "k=$(cmd | sed …)" >> "$GITHUB_OUTPUT"`) writes one computed literal and is the
safe shape; a pipeline whose last stage redirects to the file is not.

WHEN a step needs a command's result,
THEN it captures the output, parses the specific keys, and writes only those `key=value` lines.

#### Scenario: the measured verdict step is refused by the guard

- **Given** the pre-change line `make issue-verdict | tee /dev/stderr >> "$GITHUB_OUTPUT"`
- **When** the secret-output guard runs over the tree
- **Then** it reports `whole-stdout-into-output-file` (and `whole-stdout-into-log`), naming the file and line
- **Test:** `tests/test_secret_output.py::test_a_whole_stdout_piped_into_github_output_is_a_violation`

#### Scenario: a command substitution redirected into the output file is refused

- **Given** a step whose `run:` is `$(make rebuild-decision) >> "$GITHUB_OUTPUT"`
- **Then** the guard reports `whole-stdout-into-output-file`
- **Test:** `tests/test_secret_output.py::test_a_command_substitution_into_the_output_file_is_a_violation`

#### Scenario: the parsed shape is clean

- **Given** a step that captures `OUT=$(make …)` and writes `printf '%s=%s\n' "$key" "$value" >> "$GITHUB_OUTPUT"`
- **Then** the guard reports nothing for it
- **Test:** `tests/test_secret_output.py::test_parsed_key_values_are_not_a_violation`

### Requirement: No whole stream is copied into the job log

A `run:` block MUST NOT pipe a command's stdout into the log (`… | tee /dev/stderr`,
`| tee /dev/stdout`): GitHub masks only the values it registers, so a transformed value
leaks. At most the parsed fields may be printed.

WHEN a step wants a command's diagnostics in the log,
THEN it prints the parsed fields (or the specific diagnostic lines), never the stream.

#### Scenario: a bare tee to the log is refused

- **Given** `make thing | tee /dev/stderr`
- **Then** the guard reports `whole-stdout-into-log`
- **Test:** `tests/test_secret_output.py::test_tee_into_the_log_alone_is_a_violation`

#### Scenario: a filtered pipeline is not a violation

- **Given** `make thing | sed -n "/^a=/p"`
- **Then** the guard reports nothing
- **Test:** `tests/test_secret_output.py::test_tee_into_the_log_alone_is_a_violation`

### Requirement: The shipped verdict step passes only the parsed verdict

The implementer's verdict step MUST write exactly one key — `verdict=<value>` — into
`$GITHUB_OUTPUT`. Nothing else the target printed (the recipe echo, a diagnostic, a
value) may reach the file or the log. A refused verdict (`make` exits 2) MUST still fail
the step, unchanged from before this change.

WHEN the verdict step runs,
THEN `$GITHUB_OUTPUT` contains `verdict=…` and nothing else, and a refusal aborts the step.

#### Scenario: only the parsed key reaches the output file

- **Given** a `make` whose output carries a recipe echo, `[verdict] …`, `verdict=implement` and a secret-shaped line
- **When** the SHIPPED step text is executed with `bash -e`
- **Then** the output file holds exactly `verdict=implement`, and the secret-shaped value appears in neither the file nor the log
- **Test:** `tests/test_secret_output.py::test_the_verdict_step_writes_only_the_parsed_key_and_never_the_whole_stream`

#### Scenario: a refused verdict still fails the step

- **Given** a `make` that exits 2 (a close with no EVIDENCE, an unreadable verdict)
- **When** the shipped step text runs
- **Then** the step exits non-zero, so a refusal can never look green
- **Test:** `tests/test_secret_output.py::test_a_refused_verdict_still_fails_the_step`

### Requirement: The workflow test locks the shipped text, not a copy

The test that proves the verdict step's shape MUST read the step's `run:` text from the
workflow file itself, so a later edit cannot drift away from what the test executed.
A test asserting a copy of the snippet would keep passing after the workflow regressed.

WHEN the workflow's verdict step changes,
THEN the executed text changes with it, and the assertions apply to the new text.

#### Scenario: the snippet is extracted from the workflow

- **Given** `.github/workflows/issue-bot.yml`
- **Then** the extracted `run:` text contains `OUT=$(make issue-verdict)` and no `| tee`
- **Test:** `tests/test_secret_output.py::test_the_verdict_step_writes_only_the_parsed_key_and_never_the_whole_stream`

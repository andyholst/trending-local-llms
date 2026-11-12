## ADDED Requirements

### Requirement: The scrubbed_run seam passes the command positionally, never spliced

The `scrubbed_run` seam SHALL hand the command to `bash -c` as a positional
argument (`$1`), shell-escaped so every single quote inside the command is
escaped (`$(subst ','\'',$(1))`), and SHALL run it via `eval "$$1"` inside the
script. The command text SHALL NEVER be interpolated into the script body, so
a command containing single quotes — the prose quoting AGENTS.md §4 tells
prompts to use — reaches the shell intact instead of closing the `-c` string.
The `bash -o pipefail` exit-status contract, the streaming redaction, and the
raw + redacted capture files SHALL behave exactly as before.

#### Scenario: a command carrying single quotes survives the seam

Given a fixture Makefile embedding the shipped `scrubbed_run` seam and a
target whose command is `echo "prose with 'single quotes' inside"`,
When the target is run through real `make`,
Then the command runs (exit 0) and prints its output intact,
And the console contains NO bash splice syntax error — the same probe fails
with `unexpected EOF while looking for matching '` against the old splice.

- **Test:** tests/test_scrubbed_run_seam.py::test_a_command_with_single_quotes_survives_the_seam

#### Scenario: the shipped seam text refuses the old splice shape

Given the `define scrubbed_run` block read from the repository Makefile,
When the guard inspects it,
Then it runs the command as `eval "$$1"` behind a positional terminator `_`,
And it escapes the value with `$(subst ','\'',$(1))`,
And the old splice form `-c '$(1) …'` is absent.

- **Test:** tests/test_scrubbed_run_seam.py::test_the_seam_never_splices_the_command_into_the_script_text

#### Scenario: positional passing keeps the redaction and the status contract

Given the fixture workspace with a command that prints a planted secret value
and a command that exits 3,
When both run through the real seam with the planted value in the environment,
Then the planted value appears on NO console line and the masked line does,
And BOTH capture files (raw and redacted) are written,
And the failing command makes `make` exit non-zero.

- **Test:** tests/test_scrubbed_run_seam.py::test_redaction_still_wraps_the_positional_command
- **Test:** tests/test_scrubbed_run_seam.py::test_a_red_command_keeps_its_exit_status_through_eval

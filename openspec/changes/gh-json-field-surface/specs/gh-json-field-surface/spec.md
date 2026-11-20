# gh-json-field-surface

## ADDED Requirements

### Requirement: the contract records the real CLI field set for every gh subcommand the tree calls

`scripts/gh_json_fields.py` carries a recorded `Available fields:` answer for each gh
subcommand the repository calls — `run list`, `run view`, `pr list`, `pr view`,
`issue list`, `issue view`, `label list`, `secret list`, `workflow list`, `repo view` —
transcribed from the real CLI's own answer on this repository (2026-11-20). The recorded
set for a command is exactly the CLI's answer: a field the CLI cannot answer is refused
by `request()` and by `check_argv()` at REQUEST-BUILD time, not at the `gh` exit far from
the typo. A command with no recorded set still gets no opinion (never a false red), and
`run view` answers `jobs` while `run list` does not.

WHEN a script builds a `--json` field list through `gh_json_fields.request(command, fields)`
THEN every field is one the recorded set for `command` answers, or the seam raises naming
the field and the command,
AND a field gh cannot answer is refused before `gh` is called,
AND a subcommand with no recorded set is left alone.

#### Scenario: every recorded set is the CLI's own answer

- **Given** the recorded `Available fields:` answer for each of the ten subcommands, transcribed from the real CLI
- **When** `tests/test_gh_json_fields.py` compares each `FIELD_SETS` entry with its transcription
- **Then** every set is exactly equal (no script-only and no CLI-only field), `run view` carries `jobs` and `run list` does not, and an unrecorded command still returns `[]`
- **Test:** `tests/test_gh_json_fields.py::test_every_recorded_field_set_is_the_real_cli_answer` — the real table against the fixture

#### Scenario: the request seam refuses an invented field at build time

- **Given** a caller building a `--json` list through `gh_json_fields.request()`
- **When** the list names a field the recorded set for that command does not answer
- **Then** the seam raises, naming the field and the command
- **Test:** `tests/test_gh_json_fields.py::test_the_seam_refuses_a_field_gh_cannot_answer` — real seam, RED on the pre-#1158 ghost request

### Requirement: the tree-wide scan validates every `gh … --json …` request in `scripts/`

`scan_scripts()` / `scan_file()` read every `gh … --json …` request in `scripts/` through
the AST, resolve the command from the literal subcommand tokens, and check every requested
field against that command's recorded set, reporting `file:line`, the command and the
field. An argparse `--json` flag (no field list, no gh command) is not a gh request; a
`--json` field list the scan cannot read, or whose command the contract does not name, is
a FINDING — never a silent pass — and a tree without `scripts/` raises (the CLI exits 2).

WHEN the scan walks `scripts/`
THEN every `gh … --json …` request asks only for fields that command answers,
AND a drift in ANY subcommand (not only `run list`) is reported naming the file, line and field,
AND an unreadable field list or an unrecorded command is reported rather than skipped.

#### Scenario: the scan is green on this repository and red on a planted field in each subcommand

- **Given** this repository's `scripts/`, and a scratch tree per subcommand carrying one planted `gh <cmd> --json htmlUrl` caller
- **When** `scan_scripts()` runs on each tree
- **Then** the real tree is green, and every planted tree is RED naming `caller.py`, `htmlUrl` and `gh <cmd>`
- **Test:** `tests/test_gh_json_fields.py::test_the_scan_reads_every_subcommand_not_only_run_list` — real scan, one RED per subcommand

#### Scenario: a supported request and an argparse flag are not findings

- **Given** a scratch tree whose caller asks `gh pr list --json number,title`, and one carrying only `argparse`'s `--json` flag
- **When** `scan_scripts()` runs on each
- **Then** both are green — the scan opines per command and does not read a CLI flag as a gh request
- **Test:** `tests/test_gh_json_fields.py::test_the_scan_reads_every_subcommand_not_only_run_list` — real scan, GREEN

#### Scenario: an unreadable field list is a finding

- **Given** a scratch caller whose `--json` value is `os.environ["FIELDS"]`
- **When** the scan runs
- **Then** it reports a field list the scan cannot read, instead of passing silently
- **Test:** `tests/test_gh_json_fields.py::test_the_tree_scan_is_green_here_and_red_on_the_old_shape` — real scan, RED

### Requirement: the scan stays wired where CI runs it

`make lint` keeps bundling `check-gh-json-fields`, and `qa-validate`'s `validate` job keeps
running `make lint`, so the widened scan lands in the pipeline's first gate and in the fix
loop.

WHEN the Makefile and `qa-validate.yml` are read
THEN `make lint` still bundles the scan and the validate job still runs `make lint`.

#### Scenario: the wiring is unchanged and still asserted

- **Given** the Makefile's `lint:` recipe and `.github/workflows/qa-validate.yml`
- **When** `tests/test_gh_json_fields.py` reads them
- **Then** the internal `_check-gh-json-fields` recipe runs `python3 scripts/gh_json_fields.py --scan`, `make lint` bundles `check-gh-json-fields`, and the validate job runs `make lint`
- **Test:** `tests/test_gh_json_fields.py::test_the_scan_is_wired_where_ci_runs_it` — real files, GREEN

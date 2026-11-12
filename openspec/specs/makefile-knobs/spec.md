# makefile-knobs Specification

## Purpose
TBD - created by archiving change log-tail-honored. Update Purpose after archive.

## Requirements

### Requirement: Every declared Makefile override knob has a reader

Every top-level `NAME ?=` assignment in the `Makefile` MUST be read in a use shape
(`$(NAME)`, `${NAME}`, `$NAME`, an `os.environ`/`getenv` read in `scripts/`, a YAML `NAME:`
env key in a workflow, or a Dockerfile `ARG NAME`) somewhere in the runner's tree, and
`make lint` MUST run a guard that refuses a knob with no reader, naming `Makefile:line` and
stating that an operator setting it changes nothing. Mentions that move no value — comments,
docstrings, `tests/**` fixtures, `openspec/**` prose — are not readers.

#### Scenario: a declared-and-unread knob reaches the guard

- **Given** a fixture tree whose Makefile declares `DEAD_KNOB ?= 60` and no reader
- **When** `scripts/check_makefile_knobs.py` runs it
- **Then** the guard exits 1 naming `DEAD_KNOB` and its `Makefile:line`
- **Test:** tests/test_makefile_knobs.py::test_a_planted_dead_knob_goes_red

#### Scenario: prose mentions are not readers

- **Given** a fixture knob mentioned only in comments, a docstring, a `tests/` fixture and
  archived openspec prose
- **When** the guard runs it
- **Then** it exits 1 — the exact cover the dead `HERMES_LOG_TAIL` had is refused
- **Test:** tests/test_makefile_knobs.py::test_a_knob_read_only_by_prose_goes_red

#### Scenario: every use shape counts as a reader

- **Given** fixture knobs read via `$(NAME)`, `${NAME}`, `os.environ.get("NAME")`,
  `os.environ["NAME"]`, a workflow `NAME:` env key and a Dockerfile `ARG NAME`
- **When** the guard runs the tree
- **Then** exit status is 0 and no knob is named
- **Test:** tests/test_makefile_knobs.py::test_a_knob_read_by_a_recipe_or_a_script_goes_green

#### Scenario: an unreadable tree is never a silent clean

- **Given** a directory with no Makefile
- **When** the guard runs it
- **Then** it exits 2 with a loud FATAL line
- **Test:** tests/test_makefile_knobs.py::test_a_missing_makefile_fails_loudly

#### Scenario: the real Makefile passes its own guard and the dead knob is gone

- **Given** the repository's real `Makefile`
- **When** the guard runs against it
- **Then** exit status is 0, and `HERMES_LOG_TAIL ?=` is no longer declared while the seam
  comment states there is deliberately no tail knob
- **Test:** tests/test_makefile_knobs.py::test_the_real_makefile_passes_its_own_guard
- **Test:** tests/test_makefile_knobs.py::test_the_dead_knob_from_issue_630_is_gone

### Requirement: The guard is wired where a red is caught early

`make check-makefile-knobs` MUST exist as a public target over an internal host recipe, and the
`lint` recipe MUST call it, so `qa-validate`'s `validate` job (whose first gate is lint) and the
fix loop run the guard without a CI round-trip.

#### Scenario: lint runs the guard end to end

- **Given** the repository's `Makefile`
- **When** the wiring tests read the lint recipe, the internal recipe and the public target
- **Then** the lint recipe calls `check-makefile-knobs`, `_check-makefile-knobs` runs
  `python3 scripts/check_makefile_knobs.py`, and the public target exists
- **Test:** tests/test_makefile_knobs.py::test_lint_runs_the_guard

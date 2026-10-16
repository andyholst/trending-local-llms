# refresh-run-block

## ADDED Requirements

### Requirement: The composer reads the run through `gh api`

`scripts/refresh_run_block.py` MUST build every `gh` argv as `gh api <path>` —
`gh` accepts an API path only after its `api` subcommand, and
`gh repos/<o>/<r>/actions/runs/<id>` is `unknown command "repos/…" for "gh"`.
The prefix MUST have ONE definition (`GH_API`) so the writer and the tests'
stub cannot drift. A failed read MUST still raise loudly, naming the full
command it ran.

WHEN `make refresh-run-block` composes the block for a run,
THEN it reads `gh api repos/<o>/<r>/actions/runs/<id>` (and `…/jobs`) and renders
the run's own timestamps.

#### Scenario: the read is a valid `gh` command

- **Given** a `gh` on `PATH` that answers only `gh api …` and otherwise exits 1 with `unknown command "…" for "gh"`
- **When** the block is composed for a run
- **Then** the read succeeds and the block carries the run's recorded start
- **Test:** `tests/test_refresh_run_block.py::test_the_read_is_a_valid_gh_command`

#### Scenario: a dropped `api` is RED

- **Given** `origin/master`'s composer, whose argv is `gh repos/…` with no `api`
- **When** the new stub-backed test runs against it
- **Then** it FAILS — the measured defect (run 38889575999) cannot come back silently
- **Test:** `tests/test_refresh_run_block.py::test_the_read_is_a_valid_gh_command`

#### Scenario: an unreadable run is still loud

- **Given** a `gh` on `PATH` that fails
- **When** the block is composed
- **Then** the run exits non-zero and names the failure — never an empty/clean block
- **Test:** `tests/test_refresh_run_block.py::test_a_run_we_cannot_read_is_loud`

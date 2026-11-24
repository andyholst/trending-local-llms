# gh-api-jq-fields

## ADDED Requirements

### Requirement: `gh api … --jq` reads are inside the ONE field contract

`scripts/gh_json_fields.py` SHALL record a family per REST endpoint the tree reads through
`gh api <path> --jq <expr>`, keyed by the endpoint path tail, and SHALL record the dotted JSON
paths the repository reads from that answer. The recorded surface SHALL be the paths the tree
reads, not GitHub's whole recursive payload, and an unrecorded path SHALL be a finding rather
than a silent pass.

#### Scenario: a planted `--jq` typo is refused at build time

- **Given** a scratch `scripts/` tree whose caller runs `gh api repos/o/r/actions/runs/1 --jq .actor.loginr`
- **When** `scan_scripts()` reads it
- **Then** it reports one finding naming the file, the line and `.actor.loginr`
- **Test:** `tests/test_gh_json_fields.py::test_a_planted_jq_path_is_refused`

#### Scenario: the real `pr_health` identity read is green

- **Given** the exact expression `scripts/pr_health.py::read_run_identity` sends
- **When** it is checked against the recorded `actions/runs/{}` family
- **Then** it reports no problem, and the same expression with the correct field name scans green
- **Test:** `tests/test_gh_json_fields.py::test_the_api_read_surface_is_recorded`

#### Scenario: the guard fails on the base revision rather than crashing

- **Given** `git show origin/master:scripts/gh_json_fields.py`, which carries no `API_SHAPES`
- **When** the new guards run against it
- **Then** they FAIL as assertions (7 failed, no traceback), never raise `AttributeError`
- **Test:** `tests/test_gh_json_fields.py::test_the_api_read_surface_is_recorded`

### Requirement: an endpoint or expression the scan cannot read is loud

The scan SHALL treat an endpoint family the contract does not record, an endpoint the AST cannot
resolve, and a `--jq` value the AST cannot resolve as findings. A `--jq`/`-q` projection beside a
`--json` field list, and a `gh api` call carrying no field expression, SHALL stay exempt.

#### Scenario: an unrecorded family, a dynamic endpoint and a dynamic expression

- **Given** three planted callers — an unknown endpoint family, an endpoint from `os.environ`, a
  `--jq` value from `os.environ`
- **When** `scan_scripts()` reads them
- **Then** each is reported (the family gap, the ENDPOINT and the EXPRESSION respectively)
- **Test:** `tests/test_gh_json_fields.py::test_an_unrecorded_endpoint_or_unreadable_expression_is_a_finding`

#### Scenario: the exemptions hold so a later widening cannot sneak them back

- **Given** `gh pr list --json number,headRefName --jq '[.[] | select(.headRefName …)]'` and a
  fieldless `gh api repos/o/r/issues/1/comments --paginate --slurp`
- **When** `check_argv()` validates both
- **Then** neither is a problem
- **Test:** `tests/test_gh_json_fields.py::test_the_json_projection_and_fieldless_api_calls_are_exempt`

### Requirement: the tree scan is green here and non-vacuous

`make check-gh-json-fields` (`make lint`) SHALL stay green on this repository and SHALL really
discover its `gh api … --jq` calls, so a green verdict cannot come from a scan that sees nothing.

#### Scenario: green on the shipped tree, with the calls discovered

- **Given** the repository at the change head
- **When** `scan_scripts()` runs over `scripts/`
- **Then** it reports no problem AND discovers at least 15 `gh api … --jq` requests
- **Test:** `tests/test_gh_json_fields.py::test_the_scan_reads_the_real_tree_and_sees_the_api_calls`

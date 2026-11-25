# gh-json-projection-membership

## ADDED Requirements

### Requirement: a `--json` argv's `-q|--jq` projection re-reads a listed field

`scripts/gh_json_fields.py::check_argv()` SHALL enforce the exemption's STATED reason: when the
SAME argv carries `--json <fields>` AND a `-q|--jq <expr>`, every dotted path the expression READS
shall name one of the fields that argv lists (the TOP-LEVEL segment is the field). A path outside
the list SHALL be refused, naming the expression, the path and the listed fields. The recorded
`--json` sets and `API_SHAPES` families SHALL stay unchanged.

#### Scenario: a planted projection path outside its own `--json` list is refused

- **Given** the argv `gh pr list --json number -q .title`
- **When** `check_argv()` validates it
- **Then** it reports exactly the `.title` read as outside the listed field `number`, through both
  the `-q` and the `--jq` spellings
- **Test:** `tests/test_gh_json_fields.py::test_a_planted_json_projection_path_is_refused`

#### Scenario: the five shipped composite sites stay green

- **Given** `repo view --json nameWithOwner -q .nameWithOwner` (`openspec_archive_check.py:108`,
  `issue_queue.py:194`, `bot_health.py:183`), its `--jq` spelling (`issue_verdict.py:417`) and
  `keeper_pr.py:161`'s `pr list --json number,headRefName,… --jq '[.[] | select(.headRefName …)]'`
- **When** `check_argv()` validates each
- **Then** none is a problem, so enforcing the reason changes no live call
- **Test:** `tests/test_gh_json_fields.py::test_the_json_projection_and_fieldless_api_calls_are_exempt`

#### Scenario: the guard fails on the base revision rather than crashing

- **Given** `git show origin/master:scripts/gh_json_fields.py`, which skips the whole projection
  half under `if "--json" not in argv:`
- **When** the new guards run against it
- **Then** they FAIL as assertions (the planted argv returns `[]`), never raise or traceback
- **Test:** `tests/test_gh_json_fields.py::test_a_planted_json_projection_path_is_refused`

### Requirement: an unreadable projection stays tolerated

The membership check SHALL NOT widen into arbitrary `--jq` algebra. When `jq_paths(expr)` returns
None — an expression the grammar cannot read — the check SHALL tolerate it, exactly as before; a
fieldless `gh api` call (`--slurp`, `-f`) SHALL stay exempt.

#### Scenario: an expression the grammar cannot read is not a false red

- **Given** a `--json` argv whose projection `jq_paths` cannot read
- **When** `check_argv()` validates it
- **Then** the membership check adds no problem for that expression, and the fieldless
  `gh api repos/o/r/issues/1/comments --paginate --slurp` call stays exempt
- **Test:** `tests/test_gh_json_fields.py::test_the_json_projection_and_fieldless_api_calls_are_exempt`

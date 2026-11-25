# gh-json-fields

## ADDED Requirements

### Requirement: Registered no-projection Python reads are re-derived from the tree

`scripts/gh_json_fields.py` MUST record the 13 no-projection `gh api` sites that name a REST field in Python, including the `GH_API = ("gh", "api")` tuple splat at `refresh_run_block.py:105` that token-list discovery cannot see. Each record MUST name its script, caller, family, answer root, element vars, reader functions and recorded field set. `api_python_read_problems(tree)` MUST re-derive the picked names from the registered scope — chained `.get("user").get("login")`, `(x or {}).get("login")`, `rows[0].get("number")` and subscript `r["ref"]` included — and require the extracted set to equal the recorded set and be a subset of that family's recorded `API_PYTHON_FIELDS` answer. Attributions MUST be limited to the registered roots and their derived values, so unrelated `.get()` calls in the same function (for example `os.environ.get("ISSUE")`) are not findings.

#### Scenario: all 13 sites re-derive clean on the shipped tree

- **Given** the scripts at the landing head and the `API_PYTHON_READ_SITES` registry
- **When** `api_python_read_problems(tree, file)` runs for every registered site
- **Then** extracted == recorded for all 13, every recorded field is one of its family's recorded REST answer fields, and the invisible `refresh_run_block.py` splat is among them
- **Test:** tests/test_gh_json_fields.py::test_registered_reads_match_tree

#### Scenario: the root filter is not a blanket `.get()` scan

- **Given** `issue_thread.py`, whose `main` reads `os.environ.get("ISSUE", "")` and whose `render` picks comment fields off a different root
- **When** the whole-object site is re-derived
- **Then** only `title` and `body` are attributed to the issue answer and the unrelated picks produce no finding
- **Test:** tests/test_gh_json_fields.py::test_registered_reads_match_tree

### Requirement: A renamed Python-picked REST field is refused at build time

One extra pass in `scan_file` MUST add the Python-read findings to `--scan` without changing any existing signature or the `--jq` path. A renamed field on a registered site MUST produce a finding naming `file:line` and the unrecorded name, for both `.get()` and subscript forms.

#### Scenario: a `.get()` rename on a real copy of the tree

- **Given** a scratch copy of the real `scripts/` tree with `c.get("created_at")` renamed to `c.get("createdAt")` in `comment_watch.py`
- **When** `scan_scripts` runs with the fixed module
- **Then** a finding names `comment_watch.py:69` and `createdAt`; the pinned base module reports no such finding
- **Test:** tests/test_gh_json_fields.py::test_python_pick_rename_is_caught

#### Scenario: a subscript rename on a real copy of the tree

- **Given** the same tree with `r["ref"]` renamed to `r["refX"]` in `issue_queue.py`
- **When** `scan_scripts` runs with the fixed module
- **Then** a finding names `issue_queue.py:240` and `refX`; the pinned base module reports no such finding
- **Test:** tests/test_gh_json_fields.py::test_python_pick_rename_is_caught

### Requirement: The base is pinned and both merge arms stay green

The RED arm MUST load a pre-change module committed into the tree as a recorded blob, never assert unconditionally against the moving `origin/master` ref. The guards MUST fail as assertions (never crash mid-module) when that base module is substituted, and stay green both on the head and with `origin/master` simulated to the fixed head in a temp repository.

#### Scenario: RED on the pinned base and GREEN on the head

- **Given** `tests/fixtures/gh_json_fields_base_1683.py` (blob `9e96236b2aaa20005b9d8fa1be8d91489218c284`) imported as `contract`
- **When** the new guards run
- **Then** the renamed-field and registry assertions FAIL, no traceback aborts the module, and the same guards PASS with the head module
- **Test:** tests/test_gh_json_fields.py::test_python_pick_rename_is_caught

#### Scenario: GREEN after `origin/master` becomes the fixed head

- **Given** a temp repository whose `refs/remotes/origin/master` points at a commit carrying the fixed module
- **When** that simulated ref is read back and the registered-site and rename checks run
- **Then** all 13 sites still re-derive clean and the planted rename is still caught
- **Test:** tests/test_gh_json_fields.py::test_fixed_origin_master_arm_is_green

### Requirement: The `--jq` and `--json` contract path is unchanged

The new Python pass MUST be additive: `--scan` stays exit 0 with 0 findings on the shipped tree, discovery stays 31 `gh api` token-lists (17 projecting, 14 not) with 5 identity `.[]` projections, and the recorded `--json` field sets and `--jq` endpoint families are unchanged.

#### Scenario: the shipped tree still scans clean

- **Given** the unmodified shipped scripts tree
- **When** `python3 scripts/gh_json_fields.py --scan` runs
- **Then** it exits 0 with 0 findings, and the 17 `--jq` sites keep their verdicts
- **Test:** tests/test_gh_json_fields.py::test_shipped_jq_shapes_still_green

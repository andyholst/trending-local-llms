# gh-json-fields

## ADDED Requirements

### Requirement: Identity `--jq .[]` Python reads are registered on the existing registry

`scripts/gh_json_fields.py` MUST add exactly 5 `ApiPythonReadSite` records for the identity `--jq .[]` sites to the EXISTING `API_PYTHON_READ_SITES`, and MUST add `user` and `login` to the EXISTING `issues/{}/comments` entry of `API_PYTHON_FIELDS`. No new family, extractor, signature or CLI flag is allowed; slice A's 13 records MUST remain byte-unchanged in behaviour. Each record MUST name its script, caller, family, answer root, element vars, reader functions and recorded field set, re-derived from the real tree by the unmodified `api_python_read_problems` extractor.

#### Scenario: all 18 registered sites re-derive cleanly on the shipped tree

- **Given** the scripts at commit `6163bed6e4dc8f86d04d32fa24373213016a7912` and the 18-record registry
- **When** `api_python_read_problems(tree, file)` runs for every registered site
- **Then** extracted == recorded for all 18, every recorded field is a member of its family's `API_PYTHON_FIELDS` answer, and the head reports 0 findings on the unmodified tree
- **Test:** tests/test_gh_json_fields.py::test_all_18_registered_reads_match_tree

### Requirement: A renamed identity-picked field is a build-time finding with file:line

Planted renames on the five identity sites MUST be silent on the pinned base module (which has only slice A's 13 records) and MUST produce a `file:line` finding naming the unrecorded field on the head. Guard granularity is the per-site field set, so the three `pipeline_failure_issue.py` readers that all pick `body` are renamed together.

#### Scenario: RED on the pinned base for all five planted renames

- **Given** committed fixture `tests/fixtures/gh_json_fields_base_1711.py` (blob `fd57014f869edee538387d5470ee23f218505e8d`) loaded as `contract`
- **When** each planted tree is scanned with that pinned base module
- **Then** no finding names `bodyX`/`createdAtX`, so the head-only assertions FAIL as assertions (never a traceback)
- **Test:** tests/test_gh_json_fields.py::test_identity_jq_pick_rename_is_caught

#### Scenario: GREEN on the head with file:line for each planted rename

- **Given** the same five planted trees and the head module
- **When** `scan_scripts` runs
- **Then** findings name `announce_image_fallback.py:74 'bodyX'`, `issue_thread.py:85 'createdAtX'`, `owed_rows_check.py:58 'bodyX'`, `pipeline_failure_issue.py:1377 'bodyX'` and `sweep_outcome.py:132 'createdAtX'`, each with the `issues/{}/comments` family
- **Test:** tests/test_gh_json_fields.py::test_identity_jq_pick_rename_is_caught

### Requirement: The whole-object/identity overlap is partitioned so neither half false-reds

The `issue_thread.render` and `owed_rows_check.thread` records MUST carry a `blocked` set naming the whole-object local(s) (`issue`; `issue` and `issue_json`) so those names are excluded from the identity answer's source set. Dropping `blocked` MUST reproduce the measured whole-object `title` false red at `issue_thread.py:80`, proving the partition is load-bearing; with it, the unmodified tree MUST have 0 findings and no double-count.

#### Scenario: the blocked partition removes the whole-object false red

- **Given** the real `issue_thread.py` and the identity record with `blocked={"issue"}`
- **When** the site is re-derived with and without that partition
- **Then** with it there are 0 findings; without it `80: Python read of 'title' … issues/{}/comments` appears; the identity picks at `:84-86` remain red-able
- **Test:** tests/test_gh_json_fields.py::test_all_18_registered_reads_match_tree

### Requirement: The `--scan`, `--json` and `--jq` contract path is unchanged

The new records MUST be additive: `--scan` MUST stay exit 0 with 0 findings on the shipped tree; discovery MUST stay 31 `gh api` token-lists (17 projecting, 14 not) with exactly 5 identity `.[]` projections; and the recorded `--json` field sets and `--jq` endpoint families MUST be unchanged.

#### Scenario: the shipped tree still scans clean with 5 identity `.[]` projections

- **Given** the unmodified shipped scripts tree
- **When** `python3 scripts/gh_json_fields.py --scan` runs and discovery is re-derived
- **Then** exit 0 / 0 findings, 31/17/14 totals, exactly the 5 identity `.[]` projections, and unchanged `--json`/`--jq` verdicts
- **Test:** tests/test_gh_json_fields.py::test_shipped_jq_projections_still_green

### Requirement: Both merge arms stay green with a pinned base

The RED arm MUST load the pre-change module committed into the tree, never assert unconditionally against the moving `origin/master` ref. With `origin/master` simulated to the fixed head in a temp repository, the head arm MUST stay GREEN (18 records re-derive, planted rename caught) while the pinned fixture MUST stay at the pre-slice-B 13 records.

#### Scenario: GREEN after `origin/master` becomes the fixed head

- **Given** a temp repository whose `refs/remotes/origin/master` points at the fixed module
- **When** that simulated ref is read back and both arms run
- **Then** all 18 fixed-head sites re-derive clean, the identity rename is still caught, and no guard asserts a moving ref lacks the seam
- **Test:** tests/test_gh_json_fields.py::test_fixed_origin_master_arm_is_green_1711

### Requirement: One small non-breaking PR closes #1711 in both title and body

The delivery MUST be one additive PR whose branch ends in `-1711`, whose title carries the change and `Closes #1711`, and whose body repeats its own `Closes #1711` line with no second closing reference on that line. `Closes #1711` MUST be present in BOTH title and body, and the PR MUST open READY for review.

#### Scenario: the closing binding matches the branch-encoded issue

- **Given** branch `fix/gh-api-identity-jq-read-guard-1711` and a composed PR title/body
- **When** the closure validator reads them
- **Then** the branch's own issue is closed by its own keyword, exactly once, and no other issue is claimed
- **Test:** tests/test_pr_closure.py::test_the_branch_issue_must_be_closed_by_its_own_keyword

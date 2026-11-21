# findings-dedup

## ADDED Requirements

### Requirement: A filing waits until its issue is discoverable

`already_filed` MUST be able to see an issue the tool itself just created: a read that may
follow a create retries the label list with a pause until the marker is found, and a filing
run MUST NOT report success while its created issue is absent from that list (GitHub's list
index is eventually consistent).

#### Scenario: two immediate-succession invocations file exactly one issue

- **Given** a `gh` whose `issue list` lags a create by a number of seconds
- **When** `make file-findings` runs twice in immediate succession over the same finding
- **Then** exactly one issue is created, the second run reports the first's issue as already
  filed, and the first run re-reads the list until its issue became discoverable
- **Test:** tests/test_file_findings.py::test_two_immediate_invocations_file_exactly_one_issue

#### Scenario: a create that never becomes discoverable is a loud failure

- **Given** a created issue that stays absent from the label list
- **When** the filing run's discoverability check exhausts its attempts
- **Then** the run exits non-zero naming the issue and the duplicate risk, never a false
  success
- **Test:** tests/test_file_findings.py::test_a_create_that_never_becomes_discoverable_fails_loudly

# analysis-findings-issues

## ADDED Requirements

### Requirement: An implementation run records what it found

Every implementation run MUST analyse what it touched — real gaps, technical debt,
data-solidity problems in the crawler/ingest — and MUST record the findings in
`findings.md` at the repo root: one `## <title>` section per finding with
`**Evidence:**` (file:line or command output), `**Why:**` and `**Done when:**`, or
the single line `- none` when it genuinely found nothing.

WHEN the run ends,
THEN `findings.md` exists and every finding in it is specific enough to be worked.

#### Scenario: a missing analysis is loud, not silent

- **Given** an implementation run that finished without writing `findings.md`
- **When** the findings check runs
- **Then** it exits non-zero with a message saying the run must analyse what it touched
- **Test:** `tests/test_file_findings.py::test_missing_findings_file_is_a_loud_failure`

#### Scenario: a vague finding fails the check

- **Given** a `findings.md` whose section has a title but no `**Why:**`
- **When** the findings check runs
- **Then** it exits non-zero and names the section and the missing field
- **Test:** `tests/test_file_findings.py::test_finding_without_why_is_rejected`

#### Scenario: a run that found nothing is a valid outcome

- **Given** a `findings.md` containing only `- none`
- **When** the findings check runs
- **Then** it exits 0 and reports zero findings
- **Test:** `tests/test_file_findings.py::test_none_is_a_valid_empty_analysis`

### Requirement: Every finding becomes its own tracked issue

Each finding MUST be filed as its OWN issue — labelled `tech-debt`, linked back to
the issue/PR that surfaced it — and MUST NOT be fixed inside the change that found
it. Filing MUST be idempotent: the same finding is never filed twice.

WHEN the findings are filed,
THEN each finding without an existing signature marker opens one issue and each one with an existing marker is skipped with a message.

#### Scenario: a finding is filed once, with its evidence

- **Given** a `findings.md` with one complete finding
- **When** the findings are filed
- **Then** exactly one issue is created, labelled `tech-debt`, whose body carries Evidence / Why / Done when and the origin issue/PR
- **Test:** `tests/test_file_findings.py::test_finding_is_filed_once_with_evidence_and_origin`

#### Scenario: a second run does not duplicate the issue

- **Given** an issue that already carries the finding's signature marker
- **When** the findings are filed again
- **Then** no new issue is created and the existing one is reported
- **Test:** `tests/test_file_findings.py::test_already_filed_finding_is_skipped`

### Requirement: The implementer is required to do both

The implementer prompt MUST require the OpenSpec change (created first, indexed,
validated) and the findings file, and the bot MUST file the findings only after
its fix loop ended green, so a run cannot stop at "branch pushed".

WHEN the implementer pipeline runs,
THEN the prompt contains those requirements and the job files the findings when, and only when, the loop is green.

#### Scenario: the prompt carries the OpenSpec and findings rules

- **Given** the Makefile's implementer prompt
- **When** it is read
- **Then** it requires `make openspec-new` before code, `make openspec-index`, `make openspec-check`, and a `findings.md` written after the implementation
- **Test:** `tests/test_workflows.py::test_implement_prompt_requires_openspec_and_findings`

#### Scenario: the bot files the findings only on a green loop

- **Given** the implementer workflow
- **When** its steps are read
- **Then** the findings step runs `make file-findings` and is gated on the fix loop's success, so a red run files nothing
- **Test:** `tests/test_workflows.py::test_issue_bot_files_findings_only_when_green`

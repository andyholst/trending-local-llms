# data-gap-filer-labels-its-issue

## ADDED Requirements

### Requirement: an issue write is made with a token that can write issues

Every CI step that WRITES an issue — creates one, or labels / comments on one —
SHALL use the default `github.token` in a job that declares `permissions: issues:
write`, never the owner PAT (which declares Actions/Contents/Pull-requests/
Workflows and no Issues scope). This holds for the data-gap filing
(`make data-gap-issue`) and for every other issue-writing step, because a token
that cannot write issues is refused or silently ignored — measured twice (#124 for
a comment, #277 for a label).

#### Scenario: the data-gap filing is visible to both bot queues

- **GIVEN** the refresh pipeline's `aggregate` job and its `make data-gap-issue` step,
- **WHEN** the step's token and the job's permissions are read,
- **THEN** the step SHALL use `${{ github.token }}` and the job SHALL declare `issues: write`.

- **Test:** `tests/test_workflows.py::test_issue_writes_use_the_default_token`

#### Scenario: no issue-writing step anywhere reaches for the PAT

- **GIVEN** every `.github/workflows/*.yml`,
- **WHEN** each step whose `run` creates, labels or comments on an issue is collected,
- **THEN** none of them SHALL use `secrets.FIXBOT_DISPATCH_TOKEN`, and each SHALL
  belong to a job that declares `issues: write`.

- **Test:** `tests/test_workflows.py::test_issue_writes_use_the_default_token`

#### Scenario: the class guard is not vacuous

- **GIVEN** the workflows as they are,
- **WHEN** the issue-writing steps are collected,
- **THEN** there SHALL be at least five of them (a scan that finds nothing proves nothing).

- **Test:** `tests/test_workflows.py::test_issue_writes_use_the_default_token`

### Requirement: the filer creates the label before it relies on it

`make data-gap-issue` SHALL ensure the `data-gap-analysis` label EXISTS in the
repository before it files, because GitHub ignores a label the repository does not
have: the create returns 0, the issue is filed unlabelled, and the label the whole
bot chain keys on is missing — the measured cause of both empty queues (#277).
When the label is absent it SHALL create it; when it cannot be created or applied,
the run SHALL fail loudly, quoting `gh`'s own message.

#### Scenario: a repo without the label still ends up with a labelled issue

- **GIVEN** a repository that does not carry `data-gap-analysis` and a create that applies no label,
- **WHEN** the filer runs,
- **THEN** it SHALL create the label, the filed issue SHALL carry it, and the run SHALL exit 0.

- **Test:** `tests/test_data_gap_analysis.py::test_the_filer_creates_the_label_the_bots_trigger_on`

#### Scenario: an uncreatable label fails the run with gh's own words

- **GIVEN** a repository without the label and a `gh label create` that is refused,
- **WHEN** the filer runs,
- **THEN** it SHALL exit non-zero and its message SHALL quote `gh`'s refusal.

- **Test:** `tests/test_data_gap_analysis.py::test_the_filer_creates_the_label_the_bots_trigger_on`

#### Scenario: an unappliable label fails the run with gh's own words

- **GIVEN** a create that drops the label and an `issue edit --add-label` that cannot apply it,
- **WHEN** the filer runs,
- **THEN** it SHALL exit non-zero, name the label and why it matters, and include `gh`'s message.

- **Test:** `tests/test_data_gap_analysis.py::test_a_filed_issue_carries_the_label_the_bots_trigger_on`

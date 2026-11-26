# issue-filers Specification

## Purpose
TBD - created by archiving change other-filers-label-rest. Update Purpose after archive.

## Requirements

### Requirement: Every issue filer applies its label through REST

Each of the four host-side issue filers SHALL apply its queue/verdict/review
label with `gh api -X POST repos/:owner/:repo/issues/<number>/labels -f
labels[]=<label>`. None SHALL use `gh issue edit … --add-label` (GraphQL
`addLabelsToLabelable`), which an owner-PAT-authenticated host cannot call.
After the write, each filer SHALL verify the label is present and fail loudly
if it is not — the existing post-write contract is unchanged.

#### Scenario: The data-gap filer re-applies a dropped label without GraphQL

- **Given** a `gh` that answers `issue view` with no `data-gap-analysis` label
  after `issue create` and refuses `issue edit --add-label` as a GraphQL
  mutation unavailable to the token
- **When** `scripts/data_gap_analysis.py` files the changed gap set
- **Then** the filing exits 0 with the label present, the recorded `gh` calls
  contain a REST `api -X POST …/labels` write, and no call contains
  `--add-label`
- **Test:** tests/test_data_gap_analysis.py::test_a_filed_issue_carries_the_label_the_bots_trigger_on

#### Scenario: The findings filer re-applies a dropped label without GraphQL

- **Given** a `gh` whose `issue view` reports no `tech-debt` label and which
  refuses `issue edit --add-label`
- **When** `scripts/file_findings.py` files a finding
- **Then** the run exits 0, the label is observed on the issue via REST, and no
  `--add-label` call is recorded
- **Test:** tests/test_file_findings.py::test_a_dropped_label_is_reapplied_via_rest_not_graphql

#### Scenario: The reviewer opens its window via REST

- **Given** a refineable issue and a `gh` that records every argv and refuses
  `issue edit --add-label`
- **When** `scripts/issue_review.py --mark` opens the review window
- **Then** the `review-in-progress` label is applied through the REST endpoint,
  no GraphQL add-label mutation is recorded, and the marker comment still
  carries the instant and the run id
- **Test:** tests/test_issue_review.py::test_mark_sets_the_label_and_never_writes_a_body_marker_for_the_window_path

#### Scenario: A refine verdict labels the issue via REST

- **Given** a valid refine verdict and a `gh` whose REST label write applies the
  label while `issue edit --add-label` is refused
- **When** `scripts/issue_verdict.py` applies the verdict
- **Then** the run exits 0, the issue carries `agent:refined`, and no
  `--add-label` call is recorded
- **Test:** tests/test_issue_triage.py::test_refine_posts_one_restatement_and_labels_the_issue

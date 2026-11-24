## ADDED Requirements

### Requirement: The PR-blockage shape is anchored on the failing step region

`failure_shape` SHALL derive its digest from the failing step names, the `make` targets the log
names, and the FAILING STEP region's own quoted lines — everything before the single
`[filer] … FILLER …` marker — and SHALL NOT digest the filler that follows it. A block carrying no
filler marker SHALL be digested whole, so two failures that share GitHub's boilerplate and differ
only in a later line remain two shapes.

#### Scenario: One defect on two branches with divergent chatter

- **Given** two concluded-bad runs of one state-gate failure on two DIFFERENT open branches, whose
  failing regions are byte-identical and whose passing-module chatter differs
- **When** each run's error block is reduced to its shape
- **Then** both runs produce the SAME stable shape, while their whole-block exact digests differ
- **Test:** tests/test_pipeline_failure_issue.py::test_one_state_gate_defect_on_two_branches_files_once_not_zero

#### Scenario: A later-line difference still separates two defects

- **Given** two blocks with no filler marker that are identical inside an 8-line window and differ
  only later
- **When** each block is reduced to its shape
- **Then** the two shapes are different
- **Test:** tests/test_pipeline_failure_issue.py::test_failure_shape_groups_the_same_defect_and_separates_others

### Requirement: A blockage group forms on either dedup axis

`group_pr_blockages` SHALL form a group when the STABLE region anchor matches on at least
`PR_BLOCK_MIN_PRS` distinct OPEN pull requests, OR when the pre-change WHOLE-block exact digest
matches on that many. Groups with the same member set SHALL be emitted once, and the recorded
shape SHALL be the stable one.

#### Scenario: A per-branch master-move race reaches the threshold

- **Given** two red runs of one defect on two different OPEN branches whose whole-block digests
  differ
- **When** the PR-blockage pass groups them
- **Then** one group survives naming both branches, and the filer files ONE issue
- **Test:** tests/test_pipeline_failure_issue.py::test_one_state_gate_defect_on_two_branches_files_once_not_zero

#### Scenario: A lone red PR is never a fleet blockage

- **Given** one red run on one OPEN branch
- **When** the PR-blockage pass groups the items
- **Then** no group survives and nothing is filed
- **Test:** tests/test_pipeline_failure_issue.py::test_group_pr_blockages_needs_two_open_prs_and_drops_closed_branches

### Requirement: A filed PR-blockage issue names every blocked pull request

`compose_body` SHALL accept the blocked branch list and, when it is present, state how many OPEN
pull requests the shape blocks and name each. A caller passing no branches SHALL compose today's
body verbatim.

#### Scenario: The issue carries the fleet-wide scope

- **Given** a blockage group over the branches `ci/a` and `ci/b`
- **When** the filer files the issue
- **Then** the body names both `ci/a` and `ci/b`
- **Test:** tests/test_pipeline_failure_issue.py::test_one_state_gate_defect_on_two_branches_files_once_not_zero

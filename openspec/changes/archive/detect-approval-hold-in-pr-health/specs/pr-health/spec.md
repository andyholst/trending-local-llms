# pr-health

## ADDED Requirements

### Requirement: A head whose every run is `action_required` is the third silence

The sweep MUST flag every OPEN, non-draft PR whose head commit has at least one check run and
whose EVERY run concluded `action_required` (GitHub is holding the branch's own workflows for a
collaborator's approval, so no job executed), with a reason distinct from "no check runs" and
from a conflict, and MUST name in the flag comment the human remedy (approve the pending runs)
without telling anyone to rebase.

#### Scenario: a held PR is flagged with its own reason

- **Given** an open, mergeable PR whose head commit has two runs, both `action_required`
- **When** the sweep runs
- **Then** it exits 1 and names the approval hold, and does NOT report missing runs or a conflict
- **Test:** tests/test_pr_health.py::test_a_pr_whose_runs_are_all_held_for_approval_is_flagged

#### Scenario: a PR whose runs executed stays healthy

- **Given** one PR whose head runs are all `action_required` and another whose runs concluded
  normally
- **When** the sweep runs
- **Then** exactly the held PR is flagged, and the pure decision agrees with the sweep
- **Test:** tests/test_pr_health.py::test_a_held_pr_and_a_ran_pr_are_separated

#### Scenario: the hold comment names the human approval remedy

- **Given** a held PR and `--comment`
- **When** the first sweep runs
- **Then** the posted note carries the registered marker, the approval steps, the rule-6t
  reminder that approving is a collaborator's act, and no rebase hint — and a second sweep
  posts nothing
- **Test:** tests/test_pr_health.py::test_the_hold_comment_names_the_human_approval_remedy

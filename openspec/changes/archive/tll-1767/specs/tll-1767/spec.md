# tll-1767

## ADDED Requirements

### Requirement: The OpenSpec change binds Issue: #1767 and PR: fix/parallel-lane-rule-1767

The change at openspec/changes/tll-1767/ SHALL bind Issue: #1767 and PR: fix/parallel-lane-rule-1767 so that the qa-validate `validate` job's `OpenSpec lifecycle` step (openspec validate --changes) accepts the PR head. The change SHALL carry proposal.md stating `Issue: #1767` and `PR: fix/parallel-lane-rule-1767`, tasks.md with one checked box, and the capability spec.

#### Scenario: the lifecycle step accepts the PR head

- **Given** a PR whose tree contains openspec/changes/tll-1767/ with proposal.md stating `Issue: #1767` and `PR: fix/parallel-lane-rule-1767`
- **When** the qa-validate `validate` job runs its OpenSpec lifecycle step on the pushed head
- **Then** the step passes and the regenerated OPENSPEC.md lists `tll-1767` with Issue: #1767 and PR: fix/parallel-lane-rule-1767
- **Test:** qa-validate `validate` OpenSpec lifecycle step on the pushed head

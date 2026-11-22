## ADDED Requirements

### Requirement: Ownership comes from the GitHub author

The sweep SHALL classify a PR as bot-owned from its `author.is_bot` field, with the legacy branch-prefix list used ONLY when that field is absent. A branch name SHALL never override an explicit author verdict in either direction.

#### Scenario: An agent PR with a fix/ prefix is rebasable

- **Given** a behind-and-clean PR authored by a bot and named `fix/agent-owned`
- **When** `rebase_plan()` classifies it
- **Then** its action is `rebase-if-behind`
- **Test:** tests/test_pr_health.py::test_ownership_is_decided_by_author_not_branch_prefix

#### Scenario: A human PR with a ci/ prefix is report-only

- **Given** a behind-and-clean PR authored by a human and named `ci/human-owned`
- **When** `rebase_plan()` classifies it
- **Then** its action is `human-branch` and the rebaser never rewrites it
- **Test:** tests/test_pr_health.py::test_ownership_is_decided_by_author_not_branch_prefix

#### Scenario: No author data falls back to the prefix

- **Given** a PR object without an `author` field
- **When** ownership is decided
- **Then** the legacy prefix rule applies
- **Test:** tests/test_pr_health.py::test_ownership_is_decided_by_author_not_branch_prefix

### Requirement: The live queries request the author field

Both the sweep's `gh pr list` and the merge gate's `gh pr view` SHALL request `author`, so the pure decision is fed by the real payload. The merge gate's `classify()` SHALL use the same author-based ownership.

#### Scenario: The auto-merge verdict is author-based

- **Given** a bot-authored `rule/agent` PR and a human-authored `tech-debt-human` PR, both behind and clean
- **When** `classify()` runs on each
- **Then** the first verdict is `behind-and-clean-bot` and the second is `human-owned`
- **Test:** tests/test_auto_merge_rebase.py::test_classification_is_pure_and_partitions

### Requirement: The ruled safety partition is unchanged

A CONFLICTING bot PR and a human PR are still never rewritten; only the ownership input changed.

#### Scenario: A conflicting bot PR stays with its fix loop

- **Given** a bot-authored PR whose `mergeStateStatus` is `DIRTY`
- **When** `rebase_plan()` classifies it
- **Then** its action is `conflict`, never `rebase-if-behind`
- **Test:** tests/test_pr_health.py::test_ownership_is_decided_by_author_not_branch_prefix

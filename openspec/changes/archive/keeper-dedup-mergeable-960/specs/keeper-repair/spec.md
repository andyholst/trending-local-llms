# keeper-repair

## ADDED Requirements

### Requirement: Keeper dedup honours only keepers that can land

A keeper repair job that files a generated-artifact keeper PR (`index-repair`,
`architecture-repair`) MUST count as a duplicate suppressor only an OPEN keeper
that is MERGEABLE. An open keeper whose `mergeStateStatus` is `DIRTY` or
`CONFLICTING` builds no merge commit and lands nothing, so it MUST NOT suppress
the fresh keeper the drift needs; the job MUST name that unmergeable keeper in
its log and file the new keeper against the current master tip. A mergeable
open keeper MUST still suppress the new one (one keeper per drift). The
`mergeStateStatus` MUST be read in the same query as the branch name.

#### Scenario: a DIRTY keeper does not suppress the repair the red needs

- **Given** a failed push-to-master whose drift step finds one open keeper PR with `mergeStateStatus=DIRTY` and no mergeable keeper
- **When** the keeper dedup decides whether to file a keeper PR
- **Then** the unmergeable keeper is reported as `UNMERGEABLE` in the job log and a fresh keeper PR is filed against the current tip
- **Test:** `tests/test_workflows.py::test_keeper_dedup_counts_only_mergeable_keepers`

#### Scenario: a mergeable open keeper still suppresses a duplicate

- **Given** the qa-validate keeper steps' dedup code (index-repair and architecture-repair)
- **When** the tests read the workflow text
- **Then** the suppression branch keys on keepers whose `mergeStateStatus` is neither `DIRTY` nor `CONFLICTING`, in a step that fetches `headRefName,mergeStateStatus` beside the exact branch prefix
- **Test:** `tests/test_workflows.py::test_keeper_dedup_counts_only_mergeable_keepers`

#### Scenario: the guard is red on the pre-change dedup

- **Given** the keeper dedup as it was before issue #960 (branch-prefix-only count)
- **When** the new regression runs against that workflow text
- **Then** it fails on both jobs with named checks (dedup reads `mergeStateStatus`; `UNMERGEABLE` is reported; suppression is mergeable-only)
- **Test:** `tests/test_workflows.py::test_keeper_dedup_counts_only_mergeable_keepers`

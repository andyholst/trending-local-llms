## ADDED Requirements

### Requirement: A PR-blockage group subsumes its strict subsets

`group_pr_blockages` SHALL NOT emit two groups for the SAME set of failing runs: when one group's
MEMBER RUN set is a strict subset of another emitted group's member-run set, the subset group SHALL
be dropped and the superset group — the one naming every blocked branch — SHALL survive. Groups
whose member-run sets are disjoint, or overlap without containment, SHALL both survive.

#### Scenario: One defect on three branches with an exact-shape subset

- **Given** one failure shape on three OPEN branches where two runs quote a byte-identical whole
  block and the third differs only in the chatter around the same failing region
- **When** `group_pr_blockages` groups the items
- **Then** exactly one group is emitted — the STABLE-shape group naming all three branches — and
  the exact-shape subset of the first two runs is not emitted as a second group
- **Test:** tests/test_pipeline_failure_issue.py::test_group_pr_blockages_drops_an_exact_subset_of_the_stable_group

#### Scenario: Two distinct defects are not collapsed

- **Given** two different failure shapes, each blocking two OPEN branches with disjoint run ids
- **When** `group_pr_blockages` groups the items
- **Then** both groups survive
- **Test:** tests/test_pipeline_failure_issue.py::test_group_pr_blockages_drops_an_exact_subset_of_the_stable_group

# rulebook-integrity

## ADDED Requirements

### Requirement: no two hard rules share a number

The guard SHALL read `AGENTS.md` §2, collect every rule heading, and fail when two rules share an
id or when the rule set is empty.

#### Scenario: a duplicated rule number is caught

- **GIVEN** a rulebook whose §2 declares `6m.` twice (master before this change),
- **WHEN** the guard collects the ids,
- **THEN** it fails, naming the duplicated id.

- **Test:** `tests/test_rule_numbers.py::test_every_rule_number_is_unique` (verified red on the pre-change rulebook, rule 6c)

#### Scenario: a healthy rulebook passes

- **GIVEN** the rulebook after the renumber,
- **WHEN** the guard runs,
- **THEN** every id is unique and the parsed set is non-empty (the guard is not vacuous).

- **Test:** `tests/test_rule_numbers.py::test_every_rule_number_is_unique`

### Requirement: every citation resolves

Every `rule <id>` citation in the tree SHALL name an id that §2 declares, and the scan SHALL find at
least one citation.

#### Scenario: a dangling citation is caught

- **GIVEN** a tree that cites a rule id §2 does not declare (as it did mid-change: the test cited
  `6o` before the rule was renumbered),
- **WHEN** the guard scans the tree,
- **THEN** it fails, naming the file and the unresolved id.

- **Test:** `tests/test_rule_numbers.py::test_every_citation_resolves_to_a_rule` (verified red on the pre-change tree, rule 6c)

#### Scenario: citations resolve on the fixed rulebook

- **GIVEN** the renumbered rulebook and the updated citation,
- **WHEN** the guard scans the tree,
- **THEN** every citation resolves and the scan reports at least one citation.

- **Test:** `tests/test_rule_numbers.py::test_every_citation_resolves_to_a_rule`

### Requirement: numbering order and contiguity are not asserted

The guard SHALL NOT fail because a rule number is out of order or a number is missing, because §2 is
ordered by topic and a gap makes no citation ambiguous.

#### Scenario: the topic-ordered rulebook passes

- **GIVEN** §2 where `6m` precedes `6h` and no `6a` exists,
- **WHEN** the guard runs,
- **THEN** it passes: only uniqueness and resolvability are invariants.

- **Test:** `tests/test_rule_numbers.py::test_every_rule_number_is_unique`

# commit-authorship

## ADDED Requirements

### Requirement: A commit never credits its own author twice

`scan()` MUST refuse a crediting trailer whose person is the same person as the commit's author or
committer, naming it as a self-credit.

#### Scenario: the measured commit

- **Given** `author=Andy <andy.holst@protonmail.com>` and `Co-authored-by: andyholst <andy@holst.se>`
- **When** the commit is scanned
- **Then** it is refused as crediting its own author a second time, and the rule is named
- **Test:** tests/test_commit_authorship.py::test_a_commit_that_credits_its_own_author_twice_is_refused

#### Scenario: a genuinely different co-author

- **Given** the same author and `Co-authored-by: Asimov Agent <support@docondee.com>`
- **When** the commit is scanned
- **Then** it is NOT a self-credit
- **Test:** tests/test_commit_authorship.py::test_a_commit_that_credits_its_own_author_twice_is_refused

### Requirement: One person, one canonical identity

An author or committer written as a non-canonical spelling of a known person MUST be refused, and
the failure MUST name the canonical `Name <email>` to use.

#### Scenario: a second spelling

- **Given** `author=andyholst <andy@holst.se>`
- **When** it is scanned
- **Then** it is refused and the failure names `Andy Holst <andy.holst@protonmail.com>`
- **Test:** tests/test_commit_authorship.py::test_a_second_spelling_of_a_person_is_refused_with_the_canonical_pair

#### Scenario: the canonical identity and an automation identity

- **Given** `Andy <andy.holst@protonmail.com>`, `Asimov Agent <support@docondee.com>` and a `github-actions[bot]` identity
- **When** they are scanned
- **Then** none is a spelling violation
- **Test:** tests/test_commit_authorship.py::test_a_second_spelling_of_a_person_is_refused_with_the_canonical_pair

### Requirement: The guard fails on the history that produced the issue

The guard MUST flag the self-credited commits present in this repository's own `master`.

#### Scenario: the real history

- **Given** the last 40 commits of the repository
- **When** they are scanned
- **Then** at least five are self-credited and the measured `5690eb8` is among them
- **Test:** tests/test_commit_authorship.py::test_the_real_master_history_would_have_been_caught

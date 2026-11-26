## ADDED Requirements

### Requirement: §7b declares the architect's wiki-maintenance duty

`AGENTS.md` §7b SHALL carry one bold-led bullet stating that `tll-architect` owns wiki/documentation
freshness: measure every documentation claim against the fetched tree, UPDATE a document whose
statement is false, ARCHIVE an obsolete document into `docs/archive/` with a dated marker, FILE one
`enhancement` issue per change with the measured evidence, never invent a value, never hand-edit a
generated artifact, and keep rule 6t's ONE scheduled pipeline via a DAILY CI check and a WEEKLY host
cron.

#### Scenario: A reader of §7b learns the full duty

- **Given** `AGENTS.md` §7b
- **When** it is read
- **Then** it names `tll-architect`, `wiki/documentation freshness`, `DAILY CI check`,
  `weekly host cron`, `UPDATE a document whose statement is false`,
  `ARCHIVE a document whose subject is obsolete`, `docs/archive/`, `dated marker`,
  FILE one `enhancement` issue, `measured evidence`, `Never invent a value`,
  `never rewrite a generated artifact` and `ONE scheduled pipeline`
- **Test:** tests/test_wiki_rulebook.py::test_architect_wiki_role

#### Scenario: Dropping one duty clause reds the pin

- **Given** the §7b region with any one duty needle removed
- **When** the guard function runs
- **Then** it reports exactly that missing needle and fails
- **Test:** tests/test_wiki_rulebook.py::test_architect_wiki_role

### Requirement: §8 carries the wiki-rulebook regression row

`AGENTS.md` §8 SHALL carry one regression-guard row naming `tests/test_wiki_rulebook.py` and its
three functions `test_architect_wiki_role`, `test_wiki_maintenance` and `test_wiki_rulebook`, plus
the `wiki-maintenance` seam and issue `#1773`.

#### Scenario: The §8 row is present and named

- **Given** `AGENTS.md` §8
- **When** the guard reads the row naming `tests/test_wiki_rulebook.py`
- **Then** that row also names all three guard functions, `wiki-maintenance` and `#1773`
- **Test:** tests/test_wiki_rulebook.py::test_wiki_maintenance

#### Scenario: Deleting the row reds the suite

- **Given** an `AGENTS.md` whose §8 no longer carries the `tests/test_wiki_rulebook.py` row
- **When** the guard function runs
- **Then** it fails with `AGENTS.md §8 dropped the wiki-rulebook guard row`
- **Test:** tests/test_wiki_rulebook.py::test_wiki_maintenance

### Requirement: The declaration and every pre-existing §7b rule survive

The single `Rule 3c note:` line SHALL gain one clause recording that the architect wiki-maintenance
rule was added by issue #1773 and is review-required, appended at the END. The additive edit SHALL
not remove or narrow any pre-existing §7b rule.

#### Scenario: The declaration clause and the existing rules are intact

- **Given** the landed `AGENTS.md`
- **When** the guard reads the `Rule 3c note:` line and the §7b region
- **Then** the clause names `issue #1773`, the wiki-freshness bullet is present, and every
  pre-existing §7b needle (`Comment on the issue BEFORE you do the work`, `The planner runs
  make dispatch-check`, `Fetched-base sync is mandatory`, `Lanes change locally and PUSH;
  CI verifies`) is still present
- **Test:** tests/test_wiki_rulebook.py::test_wiki_rulebook

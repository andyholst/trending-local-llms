# auto-merge-index-partition

## ADDED Requirements

### Requirement: rule 6s records the human-owned index ruling

AGENTS.md rule 6s states that the report-only partition for a human-owned branch is
an explicit OWNER RULING (issue #1089), not an accident of `classify`: a behind
human-owned branch is reported and never rewritten, so `auto-merge-rebase` leaves its
cut-time `OPENSPEC.md` alone, and the declared repair for the residual stale index is
the event-driven index keeper of rule 6q. The section names the issue that asked for
the ruling, so a later reader can trace the decision to its thread.

WHEN rule 6s is read
THEN it names issue #1089 as the ruling on the human-owned partition,
AND it states that a human-owned branch is never rewritten,
AND it names the index keeper as the declared repair.

#### Scenario: the ruling is present in rule 6s

- **Given** the repository's `AGENTS.md` on this tree
- **When** `tests/test_agents_rows.py::test_the_human_owned_index_ruling_is_recorded` reads `rule_section("6s")`
- **Then** the section carries the `#1089` ruling phrase, the never-rewritten statement and the index-keeper repair
- **Test:** `tests/test_agents_rows.py::test_the_human_owned_index_ruling_is_recorded` — real `rule_section("6s")` reader over the shipped rulebook

#### Scenario: the ruling cannot be dropped silently

- **Given** a tree whose `AGENTS.md` rule 6s has the ruling sentence removed
- **When** the same test runs
- **Then** it fails, naming the missing phrase
- **Test:** `tests/test_agents_rows.py::test_the_human_owned_index_ruling_is_recorded` — the assertion is on the exact phrase, so a deletion is red

### Requirement: the merge gate's behaviour is unchanged

`scripts/auto_merge_rebase.py` keeps its verdict set and its report-only partition:
`human-owned` is still reported and never rewritten, and no branch is rebased by this
change. The ruling is a RECORDING, not a behaviour change.

WHEN `scripts/auto_merge_rebase.py` classifies a PR
THEN the verdict set is unchanged,
AND a human-owned branch is still reported and left byte-identical.

#### Scenario: the existing auto-merge-rebase guards still pass

- **Given** the repository's `tests/test_auto_merge_rebase.py`
- **When** it runs against this tree
- **Then** every verdict assertion — including `verdict=human-owned` and the untouched branch — is green
- **Test:** `tests/test_auto_merge_rebase.py::test_human_owned_behind_branch_is_reported_and_untouched` — real seam over a planted PR payload

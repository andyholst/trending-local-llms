## ADDED Requirements

### Requirement: The implementer skill states the RED-first verification discipline

The tracked `tll-implementer` skill SHALL require every acceptance criterion added by a change to be locked by a test that fails on `git show origin/master:<product-file>` and passes on the fixed head, and SHALL require RED-verification in a scratch tree cut at the fetched base before committing.

#### Scenario: The tracked skill carries the clause

- **Given** the tracked skill at `agents/tll-implementer/skills/tll-implementer/SKILL.md`
- **When** the offline guard reads it
- **Then** the RED-first clause is present, the following `Post the result on the issue` step is numbered 8, and `## This lane` appears exactly once
- **Test:** tests/test_red_first_skill.py::test_implementer_skill_states_red_first

### Requirement: Forward host notes are landed additively, not by wiping

A host diverged skill SHALL be classified against the base blob before any copy: a pure-addition forward note is preserved with a timestamped backup and routed to master through a reviewed PR, never deleted to force the fleet-sync gate green.

#### Scenario: Pure addition is not mistaken for staleness

- **Given** a host skill that is base plus added lines with zero deletions
- **When** the divergence is classified before copying
- **Then** it is treated as forward work, backed up, and landed additively with only the genuinely-new clause
- **Test:** tests/test_red_first_skill.py::test_pure_addition_is_forward_work_not_staleness

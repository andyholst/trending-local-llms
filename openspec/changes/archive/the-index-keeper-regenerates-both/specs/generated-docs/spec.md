# generated-docs

## ADDED Requirements

### Requirement: Every generated description has a keeper on a slot that converges

`architecture-bot.yml` MUST regenerate `ARCHITECTURE.md` and `OPENSPEC.md`, gate on a change to
either, and commit both — on an hourly slot — while still opening no PR and no closing keyword when
neither changed.

#### Scenario: a merge of two concurrent changes staled the index

- **Given** a tree whose `OPENSPEC.md` lists one change fewer than `openspec/changes/**` holds
- **When** `architecture-bot` runs
- **Then** `make openspec-index` rewrites it, the drift gate reports `changed=true`, and the PR stages both files
- **Test:** tests/test_architecture_bot.py::test_the_keeper_regenerates_both_generated_documents

#### Scenario: nothing changed

- **Given** both files already match the tree
- **When** the bot runs
- **Then** it is a green no-op: no branch, no PR
- **Test:** tests/test_architecture_bot.py::test_the_shipped_steps_actually_commit_push_and_open_a_pr

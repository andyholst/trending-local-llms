# architecture-description

## ADDED Requirements

### Requirement: a cadence claim in the description must be a cadence the workflow declares

`ARCHITECTURE.md` §4 and `AGENTS.md` §6b state how each pipeline starts. Every cron slot quoted
for a pipeline, every cadence word ("weekly", "daily", "hourly", "twice-an-hour", "cron",
"scheduled") attached to one pipeline in a §4 heading parenthetical or a §6b rulebook bullet,
every dispatch claim, and every counted claim ("N have a cron") is compared with that workflow's
own `on:` block by `make architecture-check`. A sentence that calls an owner-dispatched alarm
"the weekly sweep", or credits a dispatched sweep with a cron slot GitHub no longer owes it, is a
red gate. A line stating that a cadence was REMOVED is history, not a claim, and general prose
that names no pipeline is out of scope.

#### Scenario: a cron slot quoted for a pipeline that declares no schedule is red

- **Given** a fixture whose only workflow declares `workflow_dispatch:` while §4's heading for it quotes `13 * * * 3`
- **When** `make architecture-check` runs its cadence guard
- **Then** the gate exits non-zero naming the slot and the pipeline
- **Test:** `tests/test_architecture.py::test_a_cron_claim_for_a_dispatch_only_pipeline_is_reported` — real guard on a fixture tree, RED

#### Scenario: a cadence word attached to a dispatched pipeline is red

- **Given** a §4 heading that calls a dispatch-only pipeline "the weekly sweep"
- **When** the cadence guard runs
- **Then** it reports the claim against the workflow's own `on:` block
- **Test:** `tests/test_architecture.py::test_a_weekly_word_attached_to_a_dispatch_only_pipeline_is_reported` — real guard on a fixture tree, RED

#### Scenario: a cron slot the pipeline really declares is green

- **Given** a fixture whose workflow carries `schedule: cron '30 5 * * 3'` and whose §4 heading quotes that slot
- **When** the cadence guard runs
- **Then** it reports nothing
- **Test:** `tests/test_architecture.py::test_a_cron_slot_the_pipeline_really_has_is_green` — real guard on a fixture tree, GREEN

#### Scenario: a counted cron claim is verified against the tree

- **Given** docs that say "Eight have a cron" in a tree with no scheduled workflow, then the same docs corrected to "One has a cron" with one scheduled workflow
- **When** the cadence guard runs on each state
- **Then** the first is red naming the claimed and actual counts and the second is green
- **Test:** `tests/test_architecture.py::test_the_counted_cron_claim_is_verified_against_the_workflows` — real guard on a fixture tree, RED then GREEN

#### Scenario: a rulebook bullet's cadence claim is read across its wrapped line

- **Given** an `AGENTS.md` §6b bullet whose cadence claim and cron slot continue on the line after the pipeline's name
- **When** the cadence guard runs
- **Then** both the cadence word and the quoted slot are reported against that bullet's pipeline
- **Test:** `tests/test_architecture.py::test_the_rulebook_bullet_cadence_claim_is_reported_including_its_wrapped_line` — real guard on a fixture tree, RED

#### Scenario: a sentence documenting the removal is not a claim

- **Given** a dispatch-only workflow and a sentence reading "Its `23 7 * * 1` cron slot was removed by issue #1029"
- **When** the cadence guard runs
- **Then** it reports nothing
- **Test:** `tests/test_architecture.py::test_a_line_saying_the_cadence_was_removed_is_history_not_a_claim` — real guard on a fixture tree, GREEN

#### Scenario: the shipped description passes its own cadence guard

- **Given** `ARCHITECTURE.md` and `AGENTS.md` rewritten to the tree's truth (one cron pipeline, the rest owner-dispatched)
- **When** `make architecture-check` runs
- **Then** the cadence guard reports nothing and the gate exits 0
- **Test:** `tests/test_architecture.py::test_the_shipped_documents_pass_the_cadence_guard` — real guard on the real repository, GREEN

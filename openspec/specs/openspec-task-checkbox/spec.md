# openspec-task-checkbox Specification

## Purpose
TBD - created by archiving change single-checkbox-vocabulary. Update Purpose after archive.

## Requirements

### Requirement: The task-box vocabulary has exactly ONE definition

The character set inside a task checkbox and the line shape that makes one MUST be
defined once — in `scripts/task_boxes.py` — and every reader of a `tasks.md` MUST
import it. No reader may keep a private spelling of the box regex or its own
comparisons for what a state means.

#### Scenario: no script re-spells the vocabulary

- **Given** every file under `scripts/`
- **When** the wiring guard scans for a box-pattern literal (`[-*+]` followed by a bracketed character class)
- **Then** it is found only in `scripts/task_boxes.py`, and both readers import it from there
- **Test:** tests/test_task_boxes.py::test_the_box_vocabulary_has_exactly_one_home

#### Scenario: the pattern is composed from the vocabulary, not beside it

- **Given** `scripts/task_boxes.py`
- **When** the guard reads `BOX_CORE` / `box_pattern()`
- **Then** the compiled pattern embeds `BOX_STATES` itself, so adding a state there changes every reader's pattern by construction
- **Test:** tests/test_task_boxes.py::test_the_pattern_is_composed_from_the_states_string

### Requirement: Both readers classify every state in the vocabulary the same way

`check_openspec_tasks` (the completion gate) and `openspec_index` (the index
generator) MUST agree, for every state character in `BOX_STATES`, whether the box
is open, checked, or blocked.

#### Scenario: a fixture holding every state is read by both

- **Given** a `tasks.md` holding one box per state in the vocabulary (open, `x`, `X`, `~`) plus non-task bullets and a fenced sample
- **When** both readers run on it for real
- **Then** they see the same boxes, and each state counts as checked / blocked / open exactly as `scripts/task_boxes.py` classifies it
- **Test:** tests/test_task_boxes.py::test_both_readers_classify_every_state_in_the_vocabulary_the_same_way

#### Scenario: a state added in the ONE place is seen by both readers

- **Given** copies of `task_boxes.py` and both readers in a scratch tree, with one new state character added to `BOX_STATES` in the copied vocabulary and nowhere else
- **When** both copied readers run on a fixture using `- [<new state>]`
- **Then** both see it as a task box and classify it identically — and a reader carrying its own private regex would fail this scenario
- **Test:** tests/test_task_boxes.py::test_a_state_added_in_the_one_place_is_a_box_for_both_readers

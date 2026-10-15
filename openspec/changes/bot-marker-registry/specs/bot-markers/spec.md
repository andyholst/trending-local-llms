# bot-markers

## ADDED Requirements

### Requirement: every bot marker is defined once and reads back

`scripts/bot_markers.py` SHALL be the single definition of every bot marker's name and shape, and a
marker a writer emits SHALL parse back to the same bot, kind and timestamp.

#### Scenario: a written marker round-trips

- **GIVEN** the registry's `(bot, kind)` pairs,
- **WHEN** each marker is written by the registry's own writer and read back by its parser,
- **THEN** the bot, the kind and the timestamp survive, and an absent run id reads as `None`.

- **Test:** `tests/test_bot_markers.py::test_every_registered_marker_round_trips`

### Requirement: the two reviewer markers are never confused

The `issue-review` (a review is in flight) and `issue-review: window` (a reply already exists)
markers SHALL be distinct, because one is a prefix of the other.

#### Scenario: a window marker does not read as a start marker

- **GIVEN** a body carrying the reviewer's window marker,
- **WHEN** it is read as the reviewer's start kind and as its window kind,
- **THEN** it matches only its own kind, and the start marker likewise.

- **Test:** `tests/test_bot_markers.py::test_the_two_reviewer_markers_are_not_confused`

### Requirement: a placeholder stamp is not a marker

A marker whose timestamp is malformed SHALL NOT be reported as a marker, because a reader that
accepts one decides freshness on a value that is not a time.

#### Scenario: a placeholder is refused

- **GIVEN** bodies that look like markers but carry `x` or a word where `<ISO8601Z>` belongs,
- **WHEN** they are parsed,
- **THEN** none of them yields a marker.

- **Test:** `tests/test_bot_markers.py::test_a_placeholder_is_not_a_marker`

### Requirement: a registered marker has a writer, or names the issue that lands one

A marker registered as written SHALL appear somewhere in the tree; a marker with no writer yet SHALL
name the issue that lands it, and no key SHALL be both.

#### Scenario: a written marker has a producer

- **GIVEN** the registry's `WRITTEN` set,
- **WHEN** each marker's literal is looked for in the tree,
- **THEN** it is found, and every `DECLARED_BY` entry carries its issue number.

- **Test:** `tests/test_bot_markers.py::test_every_written_marker_has_a_writer`

### Requirement: the human table and the machine registry agree

AGENTS.md rule 6j SHALL name exactly the markers the registry knows, so the documented contract and
the enforced one cannot drift.

#### Scenario: AGENTS.md names every registered marker

- **GIVEN** the AGENTS.md rule-6j table,
- **WHEN** every marker name in the registry is looked up in it,
- **THEN** each one is named there.

- **Test:** `tests/test_bot_markers.py::test_agents_md_table_names_the_same_markers`

### Requirement: the queue reads markers through the registry

`scripts/issue_queue.py` SHALL read every marker through `scripts/bot_markers.py` and SHALL keep the
reviewer union (start **or** window) explicit, not by string prefix.

#### Scenario: the implementer still defers to a live reviewer window

- **GIVEN** an issue carrying a reviewer marker, and one carrying a window marker,
- **WHEN** the implementer's pick reads the queue,
- **THEN** both are held, and a marker from the reading run itself is not held.

- **Test:** `tests/test_issue_review.py` (suite) + `tests/test_workflows.py::test_issue_review_bot`

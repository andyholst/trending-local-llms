# bot-markers

## ADDED Requirements

### Requirement: A marker written outside the registry is refused

The bot-marker guard MUST also fail when a tracked text file writes a marker that belongs to a
registered bot family and is not declared in `bot_markers.REGISTRY`, naming the marker.

#### Scenario: a planted marker in a known family is caught

- **Given** the literal `<!-- issue-bot-not-a-registered-marker: 2026-10-15T09:30:00Z -->`
- **When** the reverse scan runs
- **Then** the name is reported
- **Test:** tests/test_bot_markers.py::test_every_marker_the_tree_writes_is_registered

#### Scenario: a dedup key or an alarm marker is not a bot window

- **Given** `<!-- tech-debt-signature: abc123 -->` and `<!-- queued-run-alarm -->`
- **When** the reverse scan runs
- **Then** neither is reported
- **Test:** tests/test_bot_markers.py::test_every_marker_the_tree_writes_is_registered

#### Scenario: the real tree is clean

- **Given** every tracked text file in this repository
- **When** the reverse scan runs
- **Then** no marker literal is unregistered
- **Test:** tests/test_bot_markers.py::test_every_marker_the_tree_writes_is_registered

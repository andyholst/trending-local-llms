## ADDED Requirements

### Requirement: The comment fetch asks GitHub for newest-first comments

`scripts/watch_monitor.py::fetch_payload` SHALL request both `issues` and `pulls` comment pages
with `per_page=100&sort=created&direction=desc`, so the newest comments are in the response and
a `C:` marker can fire for a comment posted after the oldest 100.

#### Scenario: The real fetch pins descending order

- **Given** the real `fetch_payload` with a stub `gh` CLI on its `client` seam
- **When** the comment pages are requested
- **Then** both request paths carry `sort=created&direction=desc` and the newest comment is in the returned rows
- **Test:** tests/test_watch_monitor.py::test_comment_fetch_requests_newest_first

#### Scenario: A comment newer than the 100th-oldest wakes the lane

- **Given** a migrated cursor at the old frozen id and the newest-first payload
- **When** `marker_state` diffs that payload
- **Then** a `C:` marker is emitted for the new comment and the stale oldest-100 backlog is not re-emitted
- **Test:** tests/test_watch_monitor.py::test_comment_fetch_sees_a_new_comment_outside_the_oldest_100

### Requirement: The cursor migration baselines without flooding

`marker_state` SHALL treat a state file that predates the newest-first repair as a one-time
migration: seed the cursor to the newest id seen, emit no stale `C:` markers, and record the
migration so the next tick emits only genuinely newer comments.

#### Scenario: The first repaired tick is quiet

- **Given** a pre-repair state carrying the frozen cursor but no migration marker
- **When** the newest-first payload is diffed
- **Then** no `C:` marker is emitted, the cursor is seeded to the newest comment, and the migration marker is recorded
- **Test:** tests/test_watch_monitor.py::test_comment_cursor_migration_baselines_without_flood

#### Scenario: The next genuinely-new comment still wakes the lane

- **Given** the migrated state
- **When** a comment newer than the seeded cursor appears
- **Then** exactly one `C:` marker names it
- **Test:** tests/test_watch_monitor.py::test_comment_cursor_migration_baselines_without_flood

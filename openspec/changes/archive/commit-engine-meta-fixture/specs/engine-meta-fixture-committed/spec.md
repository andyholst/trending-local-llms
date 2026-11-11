# engine-meta-fixture-committed

## ADDED Requirements

### Requirement: A refresh PR commits the engine-metadata fixture it captured

The refresh `aggregate`'s commit step MUST name `tests/fixtures/github_meta.json`
in BOTH its change check (`git diff --quiet -- …`) and its `git add …` list, so
a refresh that auto-registered an engine (and so `make engine-meta-capture`
recorded its GitHub metadata — issue #334) commits that fixture it wrote, and a
change consisting only of the fixture still opens a PR instead of printing "No
data changes" over a dirty tree.

WHEN the refresh aggregate registers an engine and captures its metadata into
the fixture,
THEN the refresh PR carries that fixture, so qa-validate's `make test`
classifies the engine against real captured metadata instead of red.

#### Scenario: the fixture is in the commit step's change test and stage list

- **Given** `.github/workflows/refresh-bot.yml`
- **When** its "Commit + open PR if changed" step is read
- **Then** both the `git diff --quiet` change test and the `git add` list name
  `tests/fixtures/github_meta.json`
- **Test:** `tests/test_engine_registry.py::test_capture_meta_keeps_the_fixture_covering_the_registry`

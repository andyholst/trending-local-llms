# engine-meta-capture

## ADDED Requirements

### Requirement: The offline fixture is kept covering every registered engine

`capture_meta(store, path, fetch)` MUST record GitHub metadata (`full_name`,
`description`, `topics`) for every engine in the store's registry whose repo slug
is absent from the fixture, and MUST write the file only when something was
missing. It MUST take the slug and the metadata through the registry's own
`repo_slug` / `fetch_repo_meta` pair, MUST preserve `_source` and existing
entries, and MUST NOT invent an entry for a repo the fetch could not read (that
is a loud `WARN`, leaving the fixture honest). A second run MUST add nothing.

WHEN a refresh auto-registers a new engine,
THEN the fixture gains its real metadata and `make test`'s
"a registered engine is never refused" check keeps passing.

#### Scenario: a registered engine the fixture lacks is added

- **Given** a store whose registry names `lightseekorg/tokenspeed` and a fixture that does not
- **When** `capture_meta` runs
- **Then** it returns that slug and the fixture now carries its description and topics
- **Test:** `tests/test_engine_registry.py::test_capture_meta_keeps_the_fixture_covering_the_registry`

#### Scenario: an unreadable repo is not invented

- **Given** a registry engine whose `/repos` fetch returns nothing
- **When** `capture_meta` runs
- **Then** no fixture entry is written for it and the other entries are untouched
- **Test:** `tests/test_engine_registry.py::test_capture_meta_keeps_the_fixture_covering_the_registry`

#### Scenario: a second run adds nothing

- **Given** a fixture that already covers the registry
- **When** `capture_meta` runs again
- **Then** it returns an empty list and rewrites nothing
- **Test:** `tests/test_engine_registry.py::test_capture_meta_keeps_the_fixture_covering_the_registry`

### Requirement: The capture runs where an engine is registered

The capture MUST be reachable through a make target (`make engine-meta-capture`)
and MUST be run by the refresh aggregate **after** `make merge-fetch` — the merge
is what registers an engine — and before `qa-report`, which runs `make test`. A
capability no target runs is dead code (rule 6d); a target no pipeline runs is a
defect.

WHEN the refresh aggregate has merged a leg that registered an engine,
THEN it records that engine's metadata before it runs the suite.

#### Scenario: a make target exists and the pipeline calls it

- **Given** the Makefile and `.github/workflows/refresh-bot.yml`
- **When** both are read
- **Then** `engine-meta-capture` exists and its `_` recipe runs `scripts/engine_registry.py --capture-meta`, and the aggregate calls `make engine-meta-capture` after `make merge-fetch`
- **Test:** `tests/test_engine_registry.py::test_capture_meta_keeps_the_fixture_covering_the_registry`

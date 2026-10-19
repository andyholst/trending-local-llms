# readme-render

## ADDED Requirements

### Requirement: A README can be rendered without ingesting or snapshotting

`scripts/update_trending.py --render-only` (and `make render-readme`) MUST regenerate
`README.md` from the store as of the store's own `generated_utc` and MUST NOT modify
`data/models.json` or write anything under `data/snapshots/`.

#### Scenario: rendering the real store

- **Given** a copy of the real store and README addressed through `TRENDING_DATA_DIR` / `TRENDING_README`
- **When** `--render-only` runs
- **Then** it exits 0, the store's bytes are unchanged, and no snapshot exists
- **Test:** tests/test_render_only.py::test_render_only_touches_the_readme_and_nothing_else

#### Scenario: a hand-edited README

- **Given** a README whose table header was edited by hand
- **When** `--render-only` runs
- **Then** the README is regenerated to the store's output
- **Test:** tests/test_render_only.py::test_render_only_regenerates_a_stale_readme

### Requirement: Rendering is a no-op when nothing changed

The rendered README MUST keep the `> Last generated:` line already on disk, so re-running
the target over the same store produces a byte-identical file.

#### Scenario: the same store rendered twice

- **Given** an unmodified README and store
- **When** `--render-only` runs
- **Then** the README is unchanged
- **Test:** tests/test_render_only.py::test_render_only_touches_the_readme_and_nothing_else

#### Scenario: the timestamp line survives

- **Given** a README carrying `> Last generated: …`
- **When** `--render-only` runs
- **Then** that exact line is still present
- **Test:** tests/test_render_only.py::test_render_only_keeps_the_last_generated_line

### Requirement: The target is a Makefile pair and is documented

`make render-readme` MUST be the docker wrapper of a host recipe `_render-readme` that runs
the flag, and both MUST be described in `ARCHITECTURE.md`.

#### Scenario: the wiring is read

- **Given** the repository's Makefile and ARCHITECTURE.md
- **When** the guard reads them
- **Then** the two recipes exist with those bodies and `render-readme` appears in the description
- **Test:** tests/test_render_only.py::test_the_target_is_wired_as_a_makefile_pair

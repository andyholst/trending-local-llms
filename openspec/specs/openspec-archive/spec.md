# openspec-archive Specification

## Purpose
TBD - created by archiving change fix-openspec-archive-newline-1782. Update Purpose after archive.

## Requirements

### Requirement: archive creation leaves every created text file newline-terminated

`make openspec-archive NAME=<change>` SHALL end with a deterministic seam that appends a final newline to every text file it created under `openspec/changes/archive/<change>/` that lacks one, including files that are still untracked, so the delivery's first `make lint` is green without a manual `lint-fix` (rule 6i; issue #1782). Files already ending in a newline, empty files and binary (NUL-bearing) files SHALL be left byte-identical, and the seam SHALL be idempotent.

#### Scenario: the CLI writes an archived .openspec.yaml without a final newline

- **Given** a planted archive dir `openspec/changes/archive/<name>/.openspec.yaml` whose last byte is not `0x0a`, plus a `proposal.md` that already ends with a newline
- **When** the real seam `scripts/openspec_archive_newline.py --name <name> --root <tmp>` runs
- **Then** `.openspec.yaml` ends with a single appended `0x0a`, `proposal.md` is byte-identical, and a second run appends nothing

- **Test:** tests/test_openspec_archive_newline.py::test_the_seam_repairs_a_planted_no_newline_archive

#### Scenario: the seam is wired after the archive CLI, not before

- **Given** the `openspec-archive` recipe in the `Makefile`
- **When** a regression test reads that recipe block
- **Then** it invokes `scripts/openspec_archive_newline.py` after `openspec archive $(NAME) -y`, so the repair sees the CLI's output

- **Test:** tests/test_openspec_archive_newline.py::test_the_archive_recipe_wires_the_seam

#### Scenario: a missing archive dir is refused loudly

- **Given** a root with no `openspec/changes/archive/<name>/` directory
- **When** the seam runs with that name
- **Then** it exits non-zero naming the missing path instead of reporting a vacuous clean

- **Test:** tests/test_openspec_archive_newline.py::test_a_missing_archive_dir_is_refused

#### Scenario: the CLI date-prefixes the archive directory

- **Given** the CLI archived the change to `openspec/changes/archive/<YYYY-MM-DD>-<name>/` (the shape measured on 2026-11-26)
- **When** the seam runs with `<name>` and no exact `<name>/` directory exists
- **Then** it resolves the date-prefixed directory, repairs a no-newline file inside it, and announces the directory name

- **Test:** tests/test_openspec_archive_newline.py::test_a_date_prefixed_archive_dir_is_found

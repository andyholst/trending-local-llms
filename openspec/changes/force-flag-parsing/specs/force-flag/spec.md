# force-flag

## ADDED Requirements

### Requirement: An off value for FORCE is never read as on

Every entry point that accepts `--force` MUST parse the caller's VALUE, not the
presence of the flag: `0`/`false`/`no`/`off`/empty are off, `1`/`true`/`yes`/`on` are
on, a bare `--force` is on, and anything else fails loudly. `publish` must not rebuild
or push when the value is off.

#### Scenario: FORCE is an off value

- **Given** the base image's hash tag is published and the caller passes `FORCE=0` (rendered by the Makefile as `--force=0`)
- **When** `publish` runs
- **Then** it reports the tag is already published, builds nothing and pushes nothing
- **Test:** tests/test_ensure_image.py::test_force_reaches_the_script_as_a_value_not_a_bare_flag

#### Scenario: the value arrives as a separate argument

- **Given** `publish --force 0`
- **When** the script parses its arguments
- **Then** the value is read as off and nothing is rebuilt
- **Test:** tests/test_ensure_image.py::test_force_reaches_the_script_as_a_value_not_a_bare_flag

### Requirement: A valueless --force means ON and never crashes

`decide` MUST accept a bare `--force` (no value, or followed by another option) as ON,
and MUST NOT raise `IndexError` for it.

#### Scenario: decide is given a bare flag

- **Given** `decide --force --dow 1` on a revision whose tags are absent
- **When** the script parses its arguments
- **Then** it exits 0 and reports `built=yes`
- **Test:** tests/test_ensure_image.py::test_force_reaches_the_script_as_a_value_not_a_bare_flag

### Requirement: The Makefile forwards FORCE's value

The `publish-agent-image` recipe MUST pass the value of `FORCE` to the script
(`--force=$(FORCE)`), because `$(if $(FORCE),…)` alone keeps only its non-emptiness.

#### Scenario: the target is inspected

- **Given** the repository's Makefile
- **When** the guard reads the `publish-agent-image` recipe
- **Then** it carries `--force=$(FORCE)` and not a bare `--force`
- **Test:** tests/test_ensure_image.py::test_force_reaches_the_script_as_a_value_not_a_bare_flag

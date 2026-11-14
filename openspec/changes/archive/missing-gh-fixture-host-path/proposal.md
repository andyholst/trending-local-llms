# Proposal: missing-gh-fixture-host-path

Issue: #895
PR: #927

## Why

`tests/test_openspec_archive_check.py::_run` PREPENDS the fixture bindir to the
host PATH, so the `test_a_missing_gh_is_loud` empty-bindir run still resolves the
developer's real `/opt/homebrew/bin/gh`. The module reports two host-only FAILs
(`missing gh: exits 2` answered 1, and the real gh's verdict leaking into the
second assertion) while CI's gh-less image is green — measured this session
against origin/master. A suite that reds only on developer machines trains people
to ignore it, and the exit-2 "tool missing is loud" contract is never exercised
where most edits happen.

## What Changes

- `_run` gains a `bare_path` shape that REPLACES PATH with the fixture bindir;
  the missing-gh test runs with it. Prepend stays the default for every
  stub-resolution test, so none is weakened.
- The module must pass green on a host that has `gh` installed.

## Impact

- Affected specs: `testing` (host-portable fixture environments)
- Affected code: `tests/test_openspec_archive_check.py` only (no sibling suite
  asserts a missing-tool contract through a prepended PATH — audited this change)
- Not covered: the container's gh-less-ness itself, `make test` wrapper behavior
  (#911), and the broader container-assuming fixtures (#890/#889) — those keep
  their own issues.

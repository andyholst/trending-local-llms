## Tasks — #1160: record every gh `--json` field set and scan every call site

### Contract

- [x] `scripts/gh_json_fields.py` records the real CLI's `Available fields:` answer for `run list`, `run view`, `pr list`, `pr view`, `issue list`, `issue view`, `label list`, `secret list`, `workflow list`, `repo view` (transcribed 2026-11-20)
- [x] `FIELD_SETS` is the ONE table; `SUPPORTED_BY_COMMAND` stays as the alias the #1158 tests import
- [x] `command_path()` resolves a recorded command as a prefix, so `gh run view 123 --json jobs` is `run view`

### Scan

- [x] `gh_requests()` reads EVERY `gh … --json …` request in a module, resolving the field list from a literal or a known module constant
- [x] `scan_file()` / `scan_scripts()` name `file:line`, the command and the field; an argparse `--json` flag is not a request; an unreadable list or an unrecorded command is a finding
- [x] `make check-gh-json-fields` is green on this tree (all 52 `--json` requests validated)

### Guard

- [x] `tests/test_gh_json_fields.py::test_every_recorded_field_set_is_the_real_cli_answer` pins every set against a transcribed CLI answer
- [x] `tests/test_gh_json_fields.py::test_the_scan_reads_every_subcommand_not_only_run_list` drives the REAL scan RED on a planted unknown field in EACH subcommand, and GREEN on a supported request and on an argparse flag
- [x] The stale "run view is unrecorded" assertion is corrected (it is recorded, and `jobs` is valid)

### Rulebook

- [x] `AGENTS.md` §8's `tests/test_gh_json_fields.py` row carries issues #1158/#1160 and names the full subcommand surface

### Verification

- [x] `make test` green
- [x] `make validate` green
- [x] `make lint` green
- [x] `make openspec-index` then `make openspec-check` green
- [x] `make architecture-check` green (after `make architecture-refresh` — the script docstring changed, §10 stales)

### Scope boundary

- No change to any call site's field list (the tree is already green).
- No change to `gh api` calls (no `--json` field list) or to unrecorded subcommands.

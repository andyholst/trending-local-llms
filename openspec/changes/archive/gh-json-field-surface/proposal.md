# gh-json-field-surface — record every gh `--json` field set and scan every call site

Issue: #1160
PR: #1167

## Why

`scripts/gh_json_fields.py` (issue #1158) records gh's own `Available fields:` answer for
`run list` only, and `scan_scripts()` reads only `gh run list` call sites. The tree makes
**52** `gh … --json …` requests across at least ten subcommands, so the other ~50 reads are
validated by nothing: a field gh cannot answer fails only at RUN time, which is exactly where
#1158 hid for the whole life of the ghost alarm (`htmlUrl` on `run list`, `make test` green,
the alarm naming no ghost). A contract that covers one subcommand is a contract that gives
false confidence about the rest.

Measured on this tree: `grep -rn '"--json"' scripts/ | grep -vc gh_json_fields` = 52, and
unvalidated examples include `scripts/pr_health.py:421` (`pr list --json number,title,
headRefName,isDraft,mergeable,mergeStateStatus,…`), `scripts/pr_health.py:184`
(`pr view --json comments`), `scripts/issue_verdict.py:202` (`issue view --json state`),
`scripts/code_review.py:338` (`workflow list --json name,path`) and
`scripts/data_gap_analysis.py:1339` (`issue list --json number,state,url,closedAt`).

## What Changes

- `scripts/gh_json_fields.py` records the real CLI's `Available fields:` answer for every
  subcommand the tree calls: `run list`, `run view`, `pr list`, `pr view`, `issue list`,
  `issue view`, `label list`, `secret list`, `workflow list`, `repo view`.
- `scan_scripts()` / `scan_file()` read EVERY `gh … --json …` request in `scripts/`, resolve
  the command from the literal subcommand tokens, and check every field against that
  command's set — naming `file:line`, the command and the field.
- An argparse `--json` flag (no field list, no gh command) is not a gh request and is not
  read as one; a `--json` whose field list the scan cannot read, or whose command the
  contract does not name, is a FINDING (never a silent pass).
- `tests/test_gh_json_fields.py` pins every recorded set against a transcribed CLI answer
  and drives the REAL scan RED on a planted unknown field in EACH subcommand.

## Impact

- `scripts/gh_json_fields.py` grows from one set to ten; `SUPPORTED_BY_COMMAND` becomes an
  alias of the one `FIELD_SETS` table (rule 6d: one implementation, many readers).
- `command_path()` now matches a recorded command as a PREFIX, so
  `gh run view 123 --json jobs` resolves to `run view` rather than `run view 123`.
- No workflow, Makefile target or data contract changes: `make lint` already bundles
  `check-gh-json-fields`, and `make check-gh-json-fields` is unchanged.
- Not covered: `gh api` calls (no `--json` field list — the endpoint names the fields) and
  any gh subcommand the tree does not call (still no opinion, never a false red).

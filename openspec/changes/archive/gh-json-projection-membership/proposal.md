# Proposal — enforce the `--json … -q|--jq …` exemption's stated reason

Issue: #1676
PR: #1679

## Why

`scripts/gh_json_fields.py::check_argv()` exempts a `-q|--jq` projection whenever the SAME argv
carries `--json`, on the stated reason that "that half already validated the field this
projection re-reads" (issue #1668, PR #1670, landed as `e93bc67d`). Nothing enforced it:
`check_argv` validates the `--json` field list and then skips the whole projection half under
`if "--json" not in argv:`. Measured on `origin/master` = `e93bc67d`,
`python3 scripts/gh_json_fields.py --check-argv 'gh pr list --json number -q .title'` exits 0,
while gh answers objects carrying only `number`, so `.title` yields `null` at RUN time — the
exact build-time-vs-run-time class #1158/#1160 were filed for. It is LATENT: the five shipped
composite sites (`openspec_archive_check.py:108`, `issue_verdict.py:417`, `issue_queue.py:194`,
`bot_health.py:183`, `keeper_pr.py:161`) are all self-consistent today, so enforcing the reason
changes no live call.

## What Changes

- In `check_argv()`, when the SAME argv carries `--json <fields>` AND a `-q|--jq <expr>`, parse
  the listed fields through the existing `parse_fields()` seam and require every path
  `jq_paths(expr)` reads to name one of them (the TOP-LEVEL segment — `.headRefName` reads the
  `headRefName` field). A path outside the list is refused, naming the expression, the path and
  the listed fields.
- Keep the boundaries: `jq_paths` returning None stays tolerated; arbitrary `--jq` algebra
  (`.[] | select(…)`, `//` fallbacks) is NOT widened into — the one membership mechanism is the
  whole guard; the four `repo view … -q .nameWithOwner` sites and `keeper_pr`'s array projection
  stay green.
- RED-first guards in `tests/test_gh_json_fields.py`: a planted
  `gh pr list --json number -q .title` FAILS against `git show
  origin/master:scripts/gh_json_fields.py` (assertion, not traceback) and PASSES here, plus a pin
  keeping the five shipped composite shapes green.
- `ARCHITECTURE.md` §6 `scripts/gh_json_fields.py` row names the enforcement; `findings/1676.md`
  records the hole and the owed `AGENTS.md` §8 row.

## Impact

No data format, contract, image, workflow or product-behaviour change: the validator and its
tests only. Every recorded `--json` set and every `API_SHAPES` family stays pinned byte-for-byte;
the tree scan stays green. A future `gh <cmd> --json <fields> -q <path>` whose projection reads a
field the argv does not list reds `make lint` instead of shipping a silent `null`.

## Not covered

- Widening the guard into arbitrary `--jq` algebra (`.a // .b` fallbacks, pipes the grammar cannot
  read): the reviewer's boundary; `jq_paths` returns None for what it cannot read and that stays
  tolerated.
- Recording GitHub's nested answer shape behind a `--json` field (`.actor.login` off a listed
  `actor`): the top-level field is the contract's unit; a deeper read of a LISTED field stays
  green.
- Editing `AGENTS.md`: its §8 row becomes review-required again and that write is a rule-3c human
  act — carried as the owed-row finding in `findings/1676.md`.

# Proposal — gh api `--jq` field contract

Issue: #1668
PR: #1670

## Why

`make lint`'s `check-gh-json-fields` (`scripts/gh_json_fields.py`, issues #1158/#1160) records the
fields every `gh <cmd> --json <field>` call in `scripts/` may ask for, so a field gh cannot answer
fails at BUILD time instead of RUN time. `gh api <path> --jq '<expr>'` names REST fields the same
way and was outside that contract: measured on `4e98ede4`, 17 `gh api … --jq` calls across 7
endpoint families were scanned by nothing. The residual that filed this is
`scripts/pr_health.py::read_run_identity` (issue #1646), which reads
`.actor.login + "|" + (.actor.type // "") + "|" + (.triggering_actor.login // "")` off
`repos/<o>/<r>/actions/runs/<id>` with no validation — a renamed REST field would surface only in
production, the exact failure class #1158/#1160 were filed for.

## What Changes

- Add `API_SHAPES` to `scripts/gh_json_fields.py`: one entry per REST endpoint family the tree
  reads, keyed by the endpoint path TAIL (so `{repo}`, `{owner}/{repo}` and a concrete slug
  resolve to one family), each recording `array` and the dotted paths the tree reads.
- Teach `check_argv()` and `scan_scripts()` to read `gh api <path> --jq/-q <expr>` calls through
  the AST (f-string endpoint templates resolved; local/module string bindings resolved) and refuse
  an unrecorded path, naming the family, the path, `file:line`.
- Loud, never silent: an unrecorded endpoint family, an endpoint or expression the scan cannot
  read, and a root path read from an array answer are all findings.
- Two documented exemptions: a `--jq`/`-q` projection beside a `--json` field list (the `--json`
  half already validated that field), and a `gh api` call carrying no field expression
  (`--slurp`, `-f`, `-X POST`).
- Regression guards in `tests/test_gh_json_fields.py` that FAIL on `git show
  origin/master:scripts/gh_json_fields.py` (which has no `API_SHAPES`), plus the recorded-family
  pin and a non-vacuous discovery count.
- `ARCHITECTURE.md` §3/§6 rows and the Makefile target comment name the `--jq` surface (rules
  6h/6d).

## Impact

No data format, contract, image, workflow or product-behaviour change: the validator and its tests
only. Every existing recorded `--json` set stays pinned byte-for-byte, and the scan is green on
this repository's 17 real `gh api … --jq` reads. A future `gh api … --jq` read of a field the
contract does not record reds `make lint` until the endpoint's read surface is recorded — the same
"record first" rule `--json` already applies.

## Not covered

- Recording GitHub's FULL recursive answer shape (~1000 paths across these seven endpoints): it
  would record fields no reader touches and rot silently when GitHub adds one. The recorded
  surface is the read surface.
- A `--jq` path grammar over PROJECTED output (`gh <cmd> --json … --jq …`): out of scope, exempt.
- Editing `AGENTS.md`: its §8 row for `tests/test_gh_json_fields.py` becomes incomplete, and that
  write is a rule-3c human act — carried as a blocked task box and an owed-row finding instead.

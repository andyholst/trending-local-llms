# Proposal: ghost-alarm-gh-field-contract

Issue: #1158
PR: #1159

## Why

`scripts/ghost_run_alarm.py` — the only alarm that flags a `qa-validate`
`pull_request` run which concluded carrying ZERO jobs (the state that leaves
`gh pr checks` answering "no checks reported" and auto-merge blocked, issue
#1115) — asked `gh run list` for `htmlUrl`, a field gh HAS NEVER HAD. The read
therefore failed on every call (`Unknown JSON field: "htmlUrl"`), the alarm
printed `READ FAILED` and exited 2, and it never once named a ghost — while
`make test` stayed green because the test stub `gh` answered ANY requested field.

Measured on this repository (2026-11-20, `gh run list
--repo andyholst/trending-local-llms --json htmlUrl`): gh refuses the field and
prints its own answer set (`… url …`). A gh request that gh itself would refuse
was living in a shipped alarm, invisible to every gate.

While the alarm was being fixed, the live run exposed a second half of the same
defect: gh answers `run list --json` with an ARRAY and `run view --json jobs`
with the OBJECT `{"jobs": […]}`. A read that answered `[]` for any shape it did
not recognise made EVERY completed run look like a ghost — 50 false ghosts
printed in one 168 h window, versus the 3 real `action_required`-with-zero-jobs
runs the same command reports once the answer shape is checked.

## What Changes

- New `scripts/gh_json_fields.py`: the ONE recorded gh `--json` field contract.
  `RUN_LIST_FIELDS` is gh's own recorded answer set; `request()` refuses a
  field gh cannot answer at request-BUILD time; `check_argv()` validates a whole
  `gh … --json …` argv (the seam the test stub calls); `scan_scripts()` reads
  every `gh run list` call in `scripts/` through the AST and reports the file,
  the line and the refused field; an unreadable `--json` expression is a
  finding, never a silent pass.
- `make check-gh-json-fields` (internal `_check-gh-json-fields`) bundled into
  `make lint` — the first gate of `qa-validate`'s `validate` job and of
  `scripts/fix_loop.sh` — so the scan is a stage CI runs (rules 6d/6m).
- `scripts/ghost_run_alarm.py` builds `RUNS_JSON` through `request()` (asks for
  `url`, never `htmlUrl`), validates every gh argv through `check_argv()` before
  calling gh, and checks the ANSWER's shape: an array where an array is expected,
  a `{"jobs": […]}` object where the jobs array is expected, anything else is a
  loud `READ FAILED` exit 2. A missing `gh` binary is the same loud exit 2
  instead of a traceback.
- The ghost alarm's test stub `gh` now validates every `--json` request through
  `check_argv`, so the stub cannot answer a query the real gh refuses — the
  property that kept #1158 green for the whole life of the alarm.

## Impact

- `scripts/gh_json_fields.py` (new), `scripts/ghost_run_alarm.py` (reads).
- `Makefile`: `_check-gh-json-fields` + public `check-gh-json-fields`, bundled
  into `lint:`.
- `tests/test_gh_json_fields.py` (new) and the ghost half of
  `tests/test_auto_merge_rebase.py` (stub contract, answer-shape and gh-missing
  cases).
- `AGENTS.md` §8 gains the guard row; `ARCHITECTURE.md` §? target table and §6
  script table gain their rows.
- No data, no contract (`data/*.json`), no pipeline job changes.

## Not covered

- `gh run view --json` field sets beyond `jobs` (the contract records only the
  commands the tree actually calls; an unrecorded command gets no opinion, so a
  new request cannot produce a false red).
- Whether the 3 real ghosts measured today get their heads re-pushed: that is the
  #1115 rebaser's job (`make pr-health REBASE=1`), not this change's.
- `gh api` calls (a different field vocabulary, `--jq`-filtered).

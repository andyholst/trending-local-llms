# Proposal: refresh-run-block-uses-gh-api

Issue: #320

## Why

`scripts/refresh_run_block.py` reads the run and its jobs through `_gh_json`, whose
docstring says *"One `gh api` read"* — but the argv it built had **no `api`
subcommand**:

```python
def _gh_json(args: list[str]) -> dict:
    """One `gh api` read. ..."""
    out = subprocess.run(["gh", *args], capture_output=True, text=True)   # <-- no "api"
```

`gh repos/<o>/<r>/actions/runs/<id>` is not a command, so `gh` answers `unknown
command "repos/…" for "gh"` and the read raises. Reproduced on the host,
deterministically:

```
$ GITHUB_REPOSITORY=andyholst/trending-local-llms GITHUB_RUN_ID=38889575999 \
    python3 scripts/refresh_run_block.py render
[refresh-run-block] gh repos/andyholst/trending-local-llms/actions/runs/38889575999 failed:
  unknown command "repos/andyholst/trending-local-llms/actions/runs/38889575999" for "gh"
RC=1
```

…and in production on the scheduled `refresh-bot` run
[38889575999](https://github.com/andyholst/trending-local-llms/actions/runs/38889575999):
**every other job succeeded** — `guard`, `openspec-image`, `build`, all four
`search (nvidia|metal|cpu|amd)` legs, `test-image` — and only `aggregate` failed,
at `make refresh-run-block`:

```
aggregate  make: *** [Makefile:695: refresh-run-block] Error 1
aggregate  ##[error]Process completed with exit code 2.
```

`aggregate` composes the window block BEFORE the commit/PR step, so the pipeline
has never opened a refresh PR since the block landed (#199 / PR #295): the data is
fetched, merged, and then thrown away with the ephemeral runner.

### Why the tests did not catch it

`tests/test_refresh_run_block.py` stands in for `gh` with a stub CLI on `PATH` (the
permitted EXTERNAL stand-in). That stub was `#!/bin/sh` + `echo '{}'` — it printed
`{}` whatever it was asked, so a missing subcommand was invisible. The suite tested
the *rendering*, never that the read is a valid `gh` command.

## What Changes

- **`scripts/refresh_run_block.py`** — the argv prefix is named once, `GH_API =
  ("gh", "api")`, and `_gh_json` uses it. The loud failure names the full command
  (`gh api repos/… failed: …`), so the next reader sees the real argv.
- **`tests/test_refresh_run_block.py`** — a new `test_the_read_is_a_valid_gh_command`
  whose stub ENFORCES the argv contract: it answers only `gh api …` and otherwise
  exits 1 with `unknown command "…" for "gh"`, exactly as `gh` does. Verified RED on
  `origin/master`'s script (`FAIL the read is a valid gh api command … gh repos/…`)
  and green with the fix.

## Impact

Compatibility: a bug fix — no interface changes. `make refresh-run-block` renders
again, so `refresh-bot`'s `aggregate` job can reach its commit/PR step. No target,
job, image or script name changes, so `ARCHITECTURE.md` needs no edit beyond the
script row it already has.

## Not covered

- **The `aggregate` job's OTHER red output on that run** — `QA FAILED: 7 issue(s)`
  from the soft `_validate`, and a PARTIAL mirror outage (`queries=24 with-hits=3
  outage=18 refused=0 failed=1`). Both are by design non-fatal (the refresh opens a
  PR so fix-bot can repair it); neither is this defect.
- **Whether a refresh run then produces a PR end-to-end** is verified after this
  merges, by the next cron run.

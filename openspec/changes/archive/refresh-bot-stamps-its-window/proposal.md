# refresh-bot stamps its refresh window on the PR it opens (issue #199)

**Issue:** [#199](https://github.com/andyholst/trending-local-llms/issues/199)
**Capability:** `bot-coordination`

## Why

`refresh-bot.yml` runs four real Hermes searches in parallel (~12 min) and only THEN does
`aggregate` open a PR — and only when there is new data. Until that PR exists, **nothing a reader
can open says a refresh is running**, and the PR itself carried no timestamps at all:

```
--body "Hermes CLI refresh (deepseek-v4.1-flash via Nous). Three separate per-backend searches
(NVIDIA, Metal, CPU), ... Closes #1"
```

So *which run wrote this, and when did each leg start?* was answerable only from the Actions API,
which a reviewer reading the PR page cannot see. The PR rewrites `data/**` and `README.md`, and a
reviewer's verdict ("already fixed", "the value is in the store") is checked against `master` — so a
verdict taken while a refresh is in flight can be invalidated by that PR landing minutes later. This
is the same race #179 pinned for the issue body, one artifact over (#177 is the overlap half; this
is the readable-window half).

## What Changes

- **`scripts/refresh_run_block.py`** — the ONE composer:
  - `render(...)` is pure, so a fixed fixture renders exactly the expected block;
  - `fetch(...)` reads the run's **REAL job timestamps** from `gh api` (the run's `run_started_at`
    and each job's `started_at`) — never a wall clock at PR-open time;
  - `current_block()` is what both surfaces call, returning `""` only when there is no run to
    describe (a local run) and **raising** when the read fails — a window we cannot read must never
    print as a clean one.
  - The marker line is written by the **shared helper** (`scripts/bot_markers.py`, #197), so
    `parse_markers`/`read_marker` read it like every other bot marker.
- **`make refresh-run-block`** runs it (host-side, like `data-gap-issue`: `gh` lives on the runner).
- **`refresh-bot.yml`'s `aggregate` PR step** composes the block into the PR body via the target
  (`--body-file`), inside the data-changed branch only — a rebuild-only run opens no PR and stamps
  nothing.
- **`scripts/data_gap_analysis.py`** puts the SAME block at the top of the gap issue it files, so an
  issue filed BY a refresh can be told apart from one filed by an earlier run.
- **`scripts/bot_markers.py`** moves `(refresh-bot, run)` from `DECLARED_BY` to `WRITTEN`.
- **`tests/test_refresh_run_block.py`** (into `make _test`) — a recorded capture of a real run
  renders exactly the expected block; legs are matched by the job NAME, not a position; a leg that
  is missing reads `unknown`; a failed `gh` read is loud; the workflow wires it only on the PR path;
  the gap filer carries the same block.
- `AGENTS.md` §6b refresh-bot bullet + §8 row; `ARCHITECTURE.md`'s target, `aggregate` and script rows.

## Impact

One extra block at the top of each refresh PR body and each gap issue. That is the point: the window
becomes readable where the reader already is. Nothing else changes — the merge path, the search legs
and the "never merge" behaviour are untouched, and the block is a timestamp a reader interprets, not
a lock.

## Not covered

- The overlap conflict itself (#177: two refresh PRs racing the generated store/README/baseline) —
  this makes the window visible, it does not serialise runs.
- Announcing on a pre-existing PR/issue when a refresh begins with no artifact yet: a refresh cannot
  announce on an artifact it has not created. The PR body block is the honest surface.
- `qa-validate`'s `bot-merge` marker — registered, writer not yet landed.

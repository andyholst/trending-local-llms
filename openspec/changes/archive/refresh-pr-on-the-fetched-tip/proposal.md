# Proposal: refresh-pr-on-the-fetched-tip

Issue: #177 (`tech-debt: Two overlapping refresh PRs conflict on the generated store, README and baseline`)

## Why

A refresh PR is entirely GENERATED files — `data/models.json`, `README.md`,
`data/snapshots/*`, `data/gap_baseline.json` — that every other merge rewrites. So a green
refresh PR can become unmergeable without any defect in it: PR #164
(`ci/trending-refresh-20261014-1153`) was rebased twice inside one hour, once onto `dce40a6`
(conflicts in `README.md`, `data/models.json`, `data/gap_baseline.json`) and again onto
`3f3688c` after #168 landed, and the second run's `auto-merge` had already failed with
`GraphQL: Pull Request has merge conflicts` while `validate` and `live-smoke` were green.

`refresh-bot`'s `aggregate` advances its clean checkout when it STARTS (`make base-advance`,
#448), but the four search legs ran before it and the merge, the data-gap filing and the
commit run after it — tens of minutes in which `master` merges — so the branch is cut from a
base the queue has already left. The runs are queued (`concurrency: refresh-bot`); their
PRs were never serialised against merges.

## What Changes

- **`scripts/refresh_base.py`** (the one implementation, rules 6d/6m) reuses
  `worktree_base.py`'s fetch/seam and gains two decisions:
  - `sync` — fetch the base; when the tree is behind it, reset the GENERATED files onto the
    fetched tip while KEEPING the run's raw snapshots and `data/gap_baseline.json`, and
    report the oldest snapshot's stamp. The caller re-runs `make merge SINCE=<stamp>`, so
    the store, README and baseline are RE-DERIVED on the current base instead of applied
    from an older one — nothing tries to apply our version of a file the merge owns, so
    there is no whole-file conflict to resolve. Refuses a HEAD with commits of its own and a
    dirty path outside the generated set: a reset never discards somebody's real edit.
  - `require-tip` — fetch the base and FAIL unless it is already contained in `HEAD`: the
    guard that stops a queued refresh from opening a PR against a `master` it has left.
- **`make refresh-sync` / `make refresh-require-tip`** — host targets beside `base-*`.
- **`make merge` forwards `SINCE=`** (only when set, rule 3d) so a re-derivation can
  re-ingest exactly this run's data even when the base's `generated_utc` is newer (#175).
- **`refresh-bot.yml`'s commit step**: sync + re-merge BEFORE the branch is cut,
  `require-tip` after the commit and BEFORE the push/PR, and "no data changes after the
  sync → no PR" instead of a failed commit.
- **`tests/test_refresh_base.py`** drives the real script against real git repositories
  (sync moves and keeps, no-op on the tip, refuses foreign dirty paths and own commits,
  `require-tip` red on a stale branch and green after a sync, fetch failure is loud) and
  pins the Makefile/pipeline wiring and its order.

## Impact

`scripts/refresh_base.py` (new), `Makefile` (`refresh-sync`, `refresh-require-tip`,
`merge`/`_merge` `SINCE=`), `.github/workflows/refresh-bot.yml`, `tests/test_refresh_base.py`,
`ARCHITECTURE.md` (target rows + the generated §10 inventory), `OPENSPEC.md`.

## Not covered

- **The AGENTS.md rows** (§6b's refresh description and the §8 guard table) — AGENTS.md is a
  protected file in the implementation environment; the wording is filed as its own finding
  and tracked on an issue (rule 6g, rule 3c), never folded into this change.
- **The window after the PR exists.** `master` can still merge between the guard and
  `auto-merge`; that is `auto-merge`'s conflict, and #475's repair loop. This change removes
  the long window (the search legs + merge + filing) and refuses to publish from one.
- **A conflict driver or per-model files.** The issue offers that as the alternative; the
  re-derivation path is the smaller change and keeps the store model.
- **The refresh's raw snapshots are not re-fetched**: a sync keeps what the legs captured.

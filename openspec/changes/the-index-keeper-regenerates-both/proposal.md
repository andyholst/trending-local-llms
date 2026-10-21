# Proposal: the-index-keeper-regenerates-both

Issue: #526 (measured: master red at run 39625708799 — `OPENSPEC.md` said 111 active, the disk held 112)

## Why

`OPENSPEC.md` is generated from `openspec/changes/**`. Two changes that merge an hour apart each
regenerate it over a tree that contains only ITS OWN new change, so both write the same count. The
squash merge keeps one file, the other change's row is missing, and `make openspec-index-check`
reds **every** `qa-validate` push run on master:

```
[openspec-index] FAIL OPENSPEC.md is stale or missing (112 active, 6 archived on disk)
[openspec-index]   the count line says 'Active changes: **111** · archived: **6**'
```

Neither PR was wrong, and no PR can repair it afterwards: `pr-health`, `fix-bot` and `pr-closure` all
work on PRs, and a red **push** to master has no PR. The repo has had this class once before (#304,
repaired by #455 — which fixed the *message*, not the recurrence).

## What Changes

- **`architecture-bot` becomes the keeper of BOTH generated descriptions.** It already regenerates,
  verifies, and opens a PR only when a file changed; it now runs `make openspec-index` beside `make
  architecture-refresh`, and its drift gate + commit cover `ARCHITECTURE.md` **and** `OPENSPEC.md`.
- **Its slot is HOURLY** (`13 * * * *`, an odd minute) instead of daily `13 5 * * *`: a stale index
  reds master, so a daily sweep would leave it red for up to a day. The run is cheap — two
  generators, two checks, no model — and a no-drift run stays a green no-op with no branch.
- **The PR it opens still carries no closing keyword** (it implements no issue — `pr_closure`
  refuses one that claims to), which the tests assert.
- **`OPENSPEC.md` on master is regenerated in this change**, so merging it clears the current red.

## Impact

`.github/workflows/architecture-bot.yml`, `ARCHITECTURE.md` (§10 regenerated + the job's prose),
`OPENSPEC.md`, `tests/test_architecture_bot.py`. No new target, no new job, no model.

## Not covered

- **Preventing the staleness at merge time.** There is no merge queue on this repository, and a bot
  that pushed to `master` is forbidden by §2 rule 1. A convergence window of at most one hour is the
  honest bound — the next merge of two concurrent changes will produce the same stale file, and this
  bot repairs it without a human.

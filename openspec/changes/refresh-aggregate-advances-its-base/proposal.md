# Proposal: refresh-aggregate-advances-its-base

Issue: #448 (filed first, with the measurement)

## Why

`refresh-bot`'s `aggregate` job asserts its base with `make base-check`, which
**refuses** a checkout that is not the freshly fetched tip. That refusal is the
right answer for a job with work in the tree (`issue-bot` implements, `fix-bot`
repairs); in `aggregate` it is a scheduled data loss:

- the job checks out `github.sha` — the branch head **at trigger time** — then
  the four search legs run for ~40 minutes;
- `master` is merged into routinely (9 merges in 12 h on 2026-10-20), so by the
  time `aggregate` starts the checkout is **behind by construction**;
- `make base-check` refuses, and the job dies **before it has written anything**
  (the raw snapshots arrive afterwards as artifacts), throwing away every green
  search leg.

Measured — run 39329834698 (2026-10-19T21:44Z): `guard`, `openspec-image`,
`build`, `test-image` and **4/4 search legs succeeded**, then

```
REFUSED: STALE: this checkout is NOT the freshly fetched origin/master.
  HEAD                      d7277577  (2 commit(s) behind, 0 ahead)
  origin/master (fetched)   b0012e9f
```

No PR was opened, nothing was merged, and the README stayed at
`2026-10-19 19:24 UTC` while the pipeline reported every leg healthy.

## What Changes

- **`scripts/worktree_base.py` gains `advance`** — fetch the base, and when HEAD
  is a strict ANCESTOR of the fetched tip and the tree is clean, reset to the tip
  and prove it (`advanced=<n>`); refuse a dirty tree or a HEAD carrying commits
  the base does not have. One implementation (rule 6d/6m), next to `check`.
- **`make base-advance`** — the public target, a host target like `base-check`
  (git and its credentials live on the runner).
- **`refresh-bot`'s `aggregate` runs `make base-advance`** instead of
  `make base-check`, with the reason in the step's comment. `issue-bot`'s
  `implement` job keeps `base-check`: it has work in the tree and a stale base
  there is a real defect.
- **`AGENTS.md` §6n gains the rule** — a job that has written nothing yet
  ADVANCES to the fetched tip instead of refusing; §8's guard row records what
  goes red. Rule 3c: this changes the rulebook's behaviour, so the issue carries
  the note and the AGENTS.md diff is review-required.
- **`ARCHITECTURE.md`** documents the new target, the changed `aggregate` job and
  the script's new mode (rule 6h).
- **Tests** (`tests/test_worktree_base.py`, against real git repositories): the
  measured shape advances; a fresh checkout is a no-op; a dirty tree is refused
  and survives; a diverged HEAD is refused; the Makefile seam names the mode.

## Impact

`scripts/worktree_base.py`, `Makefile` (one target), `.github/workflows/refresh-bot.yml`
(one step), `AGENTS.md` (§6n + §8), `ARCHITECTURE.md`, `tests/test_worktree_base.py`,
`OPENSPEC.md`, this change. No new image, stage or secret.

## Not covered

- **`issue-bot` / `fix-bot` are untouched.** They carry work in the tree, where
  refusing is correct; giving them an advance path would let a repair silently
  move the base under its own loop.
- **The dropped 06:00 synthetic `schedule` run** (no refresh ran between
  2026-10-19T21:44Z and 17:43Z) is a separate gap: a cron that never STARTS is not
  visible to `queued-alarm`, which only reads runs that exist. Filed as its own
  issue.

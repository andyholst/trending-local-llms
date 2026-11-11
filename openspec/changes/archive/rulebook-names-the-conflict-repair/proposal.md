# Proposal: rulebook-names-the-conflict-repair

Issue: #476 (the §6b/§8 wording `repair-a-conflicted-pr` — #475, PR #478 — owed and could not write)

## Why

PR #478 made a bot PR that cannot merge a REPAIR instead of a dead end: the silent-PR sweep
dispatches `fix-bot` for a `ci/…` branch, `scripts/fix_loop.sh` merges the fetched base before
its first round, keeps a CONFLICTED merge and hands its hunks to a Hermes round, completes the
merge when the index comes back clean, and `--abort`s it if the last round cannot resolve it.
The code is on `master`; the RULEBOOK is not. `AGENTS.md` §6b still describes `fix_loop.sh` as
"run the deterministic checks → … → re-check" with no base merge and no conflict path, and §8 has
no row for the guards, so a reader (and the next agent) cannot tell that a conflicting bot PR is
repaired by automation or which guard catches a regression in it. `AGENTS.md` is a protected file
and the write was refused in the implementing run (approval did not return), so the gap was
tracked as its own `tech-debt` issue rather than smuggled in — the shape #310/#391/#400/#369
already established.

## What Changes

- **`AGENTS.md` §6b**: a paragraph after the `fix-bot.yml` bullet naming the conflict-repair path —
  the sweep dispatches `fix-bot` for a `ci/…` branch (capped at 2 `fix-bot:` commits), the loop
  merges the fetched base before its first round, a CONFLICTED merge is KEPT with its hunks handed
  to the round (generated artifacts REGENERATED, never hand-merged), the merge is COMPLETED when
  the index comes back clean, and it is `--abort`ed if the last round cannot resolve it, so nothing
  half-merged is pushed; a human's branch is reported, never dispatched to.
- **`AGENTS.md` §8**: a row for the conflict-repair path — a conflicted base merge aborting instead
  of being repaired, a round leaving conflict markers behind, a branch pushed half-merged, an
  unresolved conflict reported as green, and the sweep dispatching a repair onto a human's branch.
- **`tests/test_agents_rows.py`**: the owed row is PINNED, not promised — `#476` joins the
  "rows this session owed" table with the phrase that describes its guard AND a §6b check, so the
  wording cannot rot back to prose (the module's whole purpose).

## Impact

`AGENTS.md` (§6b + §8), `tests/test_agents_rows.py`, this change and the regenerated `OPENSPEC.md`.
No code, no target, no pipeline, no image — a description change plus the pin that keeps it true.

## Not covered

- **The repair behaviour itself** — it shipped in #478 and is specified by
  `openspec/changes/repair-a-conflicted-pr`; this change only names it in the rulebook.
- **The approval gate that refused the first write** — a headless run's `AGENTS.md` write is still
  gated; the issue-bot PR is the reviewable path (rule 3c: the wording is review-required).
- **A non-conflicting behind base** — `auto-merge` already handles it, and §6n covers the
  branch-cut half; nothing new is claimed here.

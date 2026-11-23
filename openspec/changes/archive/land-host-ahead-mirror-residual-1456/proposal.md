# Proposal: land-host-ahead-mirror-residual-1456

Issue: #1456
PR: #1465

## Why

`make fleet-host-sync-check BASE=origin/master` reds on four lanes because each
host `agents/<lane>/skills/<lane>/SKILL.md` copy carries pitfall notes that no
merge has landed yet, while the same host copies are also BEHIND master in other
places (they lack the `#1423`/`#1427` text `tests/test_fleet_lifecycle.py`
pins). PR #1465 originally carried the dedupe of the three duplicated planner
bullets too; that half landed separately as #1468 (`d609921d`), so this change is
the RESIDUAL only — the additive host-ahead notes, with nothing removed.

## What Changes

- `agents/tll-planner/skills/tll-planner/SKILL.md`: the host-only sub-bullet on
  measuring a divergence against the RIGHT repo path lands once.
- `agents/tll-implementer/skills/tll-implementer/SKILL.md`: the `PYTHON_RUN`
  routing-measure bullet and the three tail bullets (mutually-exclusive dispatch
  criteria, pre-emption by a newer overlapping dispatch, lossy host-copy unions)
  land once.
- `agents/tll-reviewer/skills/tll-reviewer/SKILL.md`: the review-method notes
  (`FETCH_HEAD`, stale-base `validate` verdict, both-polarities proof, union
  duplicate probe, detached-worktree pin module, auto-merge while reviewing) land
  once, and the `SKIP`-is-not-a-pass sentence joins the local-green note.
- `agents/tll-pr-rebase/skills/tll-pr-rebase/SKILL.md`: five operational notes
  land once (shared remote-tracking ref, unstaged regenerated file, containerised
  `openspec-index`, no owner PAT on a host, master's stale generated count line).
- Master's own text is kept verbatim; the only removed line in the whole change is
  the shorter wording of the reviewer's local-green note, replaced by its host
  superset.

## Impact

- Four mirrored lane contracts under `agents/`; no script, workflow, data or
  contract change, so no consumer breaks and the diff stays additive.
- Every host-only line is now present in the tree, so a host that refreshes FROM
  this tree reaches 0 divergences at `make fleet-host-sync-check` instead of
  deleting rules the guard pins.
- The host machine name is reconciled out of the shared mirrors (`asimov@mac`),
  matching the issue's "no machine name" target state.

## Not covered

- The dedupe of the three duplicated planner bullets — landed by #1468 (`d609921d`).
- Editing `agents/*/SOUL.md` or `AGENTS.md` §7b/§8 (rule-3c protected; untouched).
- Refreshing the host profiles themselves — a host action outside this tree write.
- Any change to the seam's comparison semantics.

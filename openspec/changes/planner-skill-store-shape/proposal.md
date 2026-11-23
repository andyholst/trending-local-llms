# Proposal: planner-skill-store-shape

Issue: #1390

## Why

A fleet-sync repair on 2026-11-23 reverted a `MEASURED` correction that a host had applied to the
`tll-planner` profile. I verified the correction against the live store: it is right, and the tracked
skill in `master` is wrong. Since the #689 split, `data/models.json` has a top-level `engines` registry
and a **`models` list** whose per-(model, engine, source_post) measurement rows live in
`engagement.seen_posts[]` — a model row has no `engines[]` array. But `SKILL.md` lines 39, 320 and 329
still teach an `engines[]` array, so the planner counts rows that do not exist and can report a false
store loss. The host-only correction could not be the fix: it diverged from base and was re-sync'd
(backed up at `~/.hermes/profiles/tll-planner/...bak-fleetsync-20261123T104338Z`); the correction must
land in the reviewed tree.

## What Changes

- Correct all three store-shape passages in `agents/tll-planner/skills/tll-planner/SKILL.md` to the
  measured #689 shape (`models` is a list; rows are `engagement.seen_posts[]` with their counters).
- Add `tests/test_planner_skill_store_shape.py`, which reads the REAL `data/models.json` and
  `SKILL.md` directly (no stand-ins, rule 6m): one test asserts the actual store shape; the other
  asserts the skill describes `seen_posts[]` and carries none of the stale `engines[]` phrasings.

## Impact

Docs and tests only. No production seam, Makefile target, workflow, contract, store value or image
changes — no rule 6b contract edit and no additive/rule-3b data change. The test makes a future
store-shape drift fail loudly instead of silently misleading the planner lane. No `AGENTS.md` rule
changes; no rule-3c row is owed.

## Not covered

- The separate host-only "orchestration authority" directive that diverged in the same sync. That is
  an owner ruling, explicitly NOT decided or landed here; it stays in its timestamped backup.
- The #689 store split itself and the #979/#1182 rollups — already landed; out of scope.
- No lane behaviour change beyond reading the correct store shape; no new make target (rule 6d).

# Proposal: engine-check-repeat-warn

Issue: #972

## Why

`make engine-check` WARNs on unregistered engine spellings and exits 0 every
single time: its own summary line reads "will FAIL validation unless
registered", yet validation has been green for weeks with the same WARNs
repeating. The measured case (issue #972): `mlx.fast: no-repo` appears in 49
raw captures (the whole `data/raw` history) with zero rows in the store — the
spelling recurs capture after capture and every gate, the check itself
included, stays green while the decision silently ages. The check knows the
decision but not its AGE, so "unresolved for one refresh cycle" is invisible
to every gate.

## What Changes

- `scripts/engine_registry.py` `main()` gains a first-seen window: the first-seen
  date of each unregistered engine spelling is the OLDEST dated capture in
  `data/raw` naming it (the `<backend>-YYYYMMDD-HHMMSS.json` filename date —
  captures are written once at search time and never rewritten, rule 3b), so
  no new state file is introduced.
- A WARN first seen within `--refresh-window-days` (default 7, the weekly
  refresh cadence) stays NEW: reported, exit 0 — one refresh cycle of grace
  for a genuinely new engine.
- A WARN first seen OLDER than the window is a REPEAT: the line names its
  first_seen date and age, a summary names the repeat engines and their three
  resolutions, and the check EXITS 1. `make engine-check` already runs after
  every refresh search leg and before the next refresh, so the repeat now reds
  the pipeline that let it age.
- A spelling a human declined via `NON_ENGINE_REPOS` / `NON_ENGINE_NAMES` is
  SETTLED: it reports `OK … (declared refusal — settled)`, is no longer a WARN,
  and its age can never red the check. `--now YYYY-MM-DD` overrides today for
  deterministic runs.

## Impact

- `scripts/engine_registry.py` — `capture_date()`, `engine_first_seen()`,
  `decision_settled()`, the new `--refresh-window-days` / `--now` flags in
  `main()`. No new make target: `make engine-check` already runs (refresh-bot
  after each search leg, and the aggregate stage).
- `tests/test_engine_registry.py` — five new tests (repeat fails, new passes,
  declined never repeats, oldest-dated-capture wins, shipped `data/raw` has no
  stale WARN) and updated assertions on the CLI-branch test.
- `AGENTS.md` §6 refresh-workflow text and §8 guard row; `ARCHITECTURE.md` §5
  (`engine-check` target row) and §6 (`engine_registry.py` row).

## Not covered

- Renaming or registering engine spellings themselves — resolving a repeat
  (register / alias in `ENGINE_NAME_ALIASES` / decline in `NON_ENGINE_*`) is
  the human or implementer decision the red check forces, not this change.
- Mutating or deleting old raw captures — first-seen reads history
  (rule 3b: history is never rewritten).
- Undated captures: named with `first seen unknown`, reported, never counted
  as a repeat (age is unprovable from them).

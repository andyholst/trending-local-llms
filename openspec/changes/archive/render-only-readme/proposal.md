# Proposal: render-only-readme

Issue: #195 — `tech-debt: A generated-README change forces a store timestamp bump and a snapshot write`

## Why

`README.md` is generated, and the only reachable way to regenerate it was `make merge`:
`scripts/update_trending.py` with no flag ingests `data/raw/*`, stamps
`store["generated_utc"] = now`, writes `data/models.json`, renders the README **and** writes
a new `data/snapshots/trending-<UTC>.json`.

So a change that only edits the README template carried:
- a `data/models.json` diff whose only content was a new timestamp, and
- a snapshot containing no new data — indistinguishable in the history from a real ingest.

Measured twice in this repository (issue #179's template change: `generated_utc`
`17:36:44Z` → `21:59:33Z` plus `trending-20261014-215933.json`), and again while fixing
#260 in this session, where the only honest way to refresh one backend cell was to render
the README by hand.

## What Changes

- **`scripts/update_trending.py --render-only`**: renders `README.md` from the store **as of
  the store's own `generated_utc`** — the exact as-of `check_readme_generated` re-renders
  with — and returns before the ingest, the timestamp bump, the store write and the
  snapshot. A store with no usable `generated_utc` is a loud error (`run make merge`).
- **The `> Last generated:` line is preserved** from the README on disk. `render_readme`
  stamps the wall clock there; a docs change must not move a timestamp, and this makes a
  re-run a **no-op** (the gate already strips that line, so correctness is unaffected).
- **`make render-readme`** (docker wrapper) over the host recipe `_render-readme`, the same
  pairing every other public target uses.
- **The README gate names the right repair**: `check_readme_generated`'s failure message now
  says `make render-readme` (template/docs, no snapshot) **or** `make merge` (new data),
  and its OK line no longer claims `make merge` produced the file.
- **`tests/test_render_only.py`** drives the real script through its own
  `TRENDING_DATA_DIR` / `TRENDING_README` seams against a copy of the real store: the store
  is byte-identical afterwards, no snapshot is written, a re-run changes nothing, a
  hand-edited README is repaired, the timestamp line is kept, and the Makefile/ARCHITECTURE
  wiring exists.

Verified RED against the pre-change script (6 failures — the flag did not exist, so the
README was never regenerated) and GREEN after (`PASSED 11 | FAILED 0`).

## Impact

`scripts/update_trending.py` (one flag, one branch), `scripts/validate.py` (one message),
`Makefile` (`_render-readme` + `render-readme`), `ARCHITECTURE.md` (§3 target table, rule
6h), a new `tests/test_render_only.py`, this OpenSpec change and the regenerated
`OPENSPEC.md`.

## Not covered

- **Using the new target in the README gate itself.** The gate re-renders in memory and
  compares; it needs no write, and pointing it at a target would be slower without being
  more correct. What it lacked was the right repair in its message, which it now names.
- **A "render without touching the store" path for the SNAPSHOT history.** Snapshots stay
  the record of a real ingest; a docs change should not create one, which is exactly what
  this change stops requiring.

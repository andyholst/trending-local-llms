# Proposal: all-quarantined-capture-is-an-alarm

Issue: tech-debt — "A capture where EVERY row is quarantined still exits 0 and reports
'the rest of the capture still merges'" (filed while implementing #381; surfaced by PR #623).

## Why

`scripts/self_correct_raw.py` gates its non-zero exit on the count of snapshots that could be
READ, never on the number of model rows that SURVIVED correction. Measured against the real
command (temp `TRENDING_DATA_DIR`, one snapshot, 3 models, none in the store, none carrying
`hf`): `rc: 0`, every row `QUARANTINED: … hf missing (cannot derive)`, the final line
`SELF-CORRECT OK: … the rest of the capture still merges` — and `models left: []`. The
aggregate then opens no PR (there is no new data) and nothing is red: an empty refresh is a
green no-op. The mirror defect of issue #381, which was right that ONE bad row must not
discard a whole refresh — its inside-out now hides a capture where the search leg wrote
nothing usable.

## What Changes

- **`scripts/self_correct_raw.py` (`main()`)** counts, per readable snapshot, the model rows
  that SURVIVED correction (`len(models)` of the corrected snapshot on disk) and sums them
  across the capture. When the capture read at least one snapshot but ZERO rows survived,
  it prints a distinct, grep-able `CAPTURE UNUSABLE:` line naming the fact (and whether any
  was quarantined) and returns **1** — the state genuinely needing a re-search. `make
  correct-raw` is a hard step of the `aggregate` job, so a non-zero exit makes the empty
  refresh a red pipeline, not a silent no-PR.
- **`scripts/self_correct_raw.py`** module docstring (§ "Exit 0 = … non-zero = …") updated
  to name the third non-zero state.
- **Tests:** `tests/test_raw_quarantine.py` gains a case that drives the REAL command
  (`run_correct_raw`) over an all-bad snapshot (every row un-derivable `hf`, none resolves to
  the store): it must exit non-zero with the `CAPTURE UNUSABLE` line, every row still reported
  `QUARANTINED`, and no model left in the snapshot — while the existing partial-quarantine
  tests keep asserting exit 0 (one bad row still never discards the healthy remainder).

## Impact

`scripts/self_correct_raw.py`, `tests/test_raw_quarantine.py`, this OpenSpec change and the
regenerated `OPENSPEC.md`. No new target, stage, workflow or image: the behaviour lives in the
existing `correct-raw` target the aggregate already runs and returns non-zero through it
(`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **A capture whose snapshots are all genuinely EMPTY (no rows captured, nothing quarantined)
  also reaches the `CAPTURE UNUSABLE` branch** — it is the same "empty refresh is an alarm"
  outcome. It is not separately tested beyond the all-quarantined case; the per-leg outage /
  `--require-hits` live-smoke classification remains the primary voice for a mirror that is
  down, and this branch is the aggregate-side backstop.
- A single quarantined row beside surviving rows keeps exiting 0 (issue #381's contract is
  unchanged) — this change only fires when the capture ends with ZERO usable rows.
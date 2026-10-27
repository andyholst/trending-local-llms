# Make `correct-raw` say WHY an `hf` was missing, from the run's own output

Issue: #382

## Why

`scripts/self_correct_raw.py` (`make correct-raw`, the aggregate's normalisation
step) reports a quarantined model in ONE loud line — model, reason and source
posts (issue #381):

```
QUARANTINED: nvidia-20261020-120000.json/sloppy: hf missing (cannot derive); excluded from this snapshot — the rest of the capture still merges (post(s): https://lightbrd.com/a/status/1)
```

That line cannot tell the two causes apart, and they need opposite fixes:

- the post the row cites **states no HF repo** → nothing was omitted; the model
  simply cannot be tracked yet (leave the gap), and
- the row **had** the repo (`why`/`quant`/`formats[]`/an unreducible `hf`) and
  the agent never copied it into `hf` → strengthen the prompt.

`data/raw/*.json` keeps the measurement but not the post text, so the evidence
is only in the run's log — and once that log ages out, the occurrence is
unreproducible. Measured while implementing #378 (surfaced by PR #379): the same
run printed `CANNOT_DERIVE: <model>: hf missing (cannot derive)` with nothing
beside it, and telling the two cases apart meant fetching the post by hand.

## What Changes

- **`scripts/self_correct_raw.py`** — the `QUARANTINED:` line for an
  un-derivable `hf` now carries a bracketed DIAGNOSIS of what the row and its
  snapshot actually carried, so the artifact alone decides which fix applies:
  - an HF repo LINK anywhere in the row (`why`, `quant`, `note`, `hardware` …)
    → names the field and the captured token, and says it never reached `hf`;
  - an `hf` value that was captured but is not an `owner/repo` id → says it was
    malformed, not absent;
  - no top-level `hf` but a `formats[i].hf` → says the repo was in the row;
  - no token in this row but one in ANOTHER model's row of the same snapshot →
    says so, so a leg that lost the field everywhere is distinguishable from a
    post that states none;
  - nothing anywhere → `no HF-shaped token anywhere in the snapshot — it states
    no repo, so none was omitted`.
  Every value quoted is the captured text, bounded (never the whole row), and
  nothing is invented: the diagnosis reports what the artifact holds and never
  guesses a repo id.
- **`tests/test_raw_quarantine.py`** — the diagnosis is locked per branch of the
  rule, driven through the REAL command (a temp `TRENDING_DATA_DIR`), including
  that the report stays bounded.
- **`ARCHITECTURE.md`** (`correct-raw` target row + the `scripts/` table) and
  **`AGENTS.md`** §8's `test_raw_quarantine.py` row describe the diagnosis in the
  same change (rules 6c/6h).

## Impact

The refresh aggregate's log only. The quarantined-row SET is unchanged (a row is
excluded exactly as before), the exit code is unchanged (0 with quarantined rows,
1 only when no snapshot could be read), the snapshot write/invalidation rule is
unchanged, and no stored value is touched — so `check_no_value_loss` (rule 3b)
is untouched.

## Not covered (out of scope)

- **Re-searching a quarantined model, or repairing it automatically.** The
  diagnosis makes the gap actionable; it does not fetch, guess or invent an `hf`.
- **A per-leg summary of every diagnosis.** One line per quarantined model is
  the existing contract; aggregating them into a run-level verdict is a
  different change (and the fix loop reads per-line output).
- **Strengthening the search prompt so `hf` is never dropped.** That prompt
  change needs the diagnosis evidence to say which leg fails and why — this
  change is what produces it.
- **The `-2`/`-3` same-second snapshot suffixes and other `correct-raw`
  behaviours** — untouched.

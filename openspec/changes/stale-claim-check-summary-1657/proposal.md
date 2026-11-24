# Proposal: stale-claim-check-summary-1657

Issue: #1657

## Why

`#1265` §3B exempts a run-bearing claim whose evidence is still LIVE at ANY age; #1635 landed
that exemption in the decision (`ae574e3c`). But the offline `--check` summary line — the one
printed contract a host actually reads — was never updated: it still ends the live-run clause with
`(x2 when the claim carries a run id)`, which describes only the pre-#1635 doubled pair. A reader
concludes every `R:<id>` / `PR #<n>` claim is bounded by exactly the doubled 180/360 pair, so the
line understates the shipped rule and would not reveal a regression back to "doubled grace only".
The module docstring and both `ARCHITECTURE.md` rows were updated by #1635; this single printed
line was missed. Reported by `tll-reviewer` on `asimov@mac`.

## What Changes

- `scripts/stale_claim_sweep.py`: the `--check` summary's live-run clause becomes
  `(x2 when the claim carries a run id, unless its evidence is still LIVE, #1265 §3B)`. Output
  prose only — no decision logic.
- `tests/test_stale_claim_sweep.py`: the offline-contract test now pins that exact phrase beside the
  doubled pair, so the printed contract cannot drift back to the pre-#1635 wording. RED-first:
  the new assertion fails on `ae574e3c` and passes on this head.

## Impact

Docs-only and non-breaking: the three-refusal tuple (`AUTHORITY_LIMITS`), the pinned grace pairs,
the floors, the `S:` vocabulary and every exit code are untouched. No data, contract, format,
target, workflow or host-profile change; no new make target, no schedule. One small delivery.

## Not covered

- No change to the sweep decision, the liveness resolver, the claim-id derivation or dedup.
- No `AGENTS.md` §7b/§8 text and no `agents/*/SOUL.md`: the owed §8 row is tracked by #1621.
- No PING/RELEASE comment, no state file and no new sweep stage.

# Proposal: stale-claim-thresholds-1626

Issue: #1626
PR: #1630

## Why

Child 1 landed (`#1610`, PR #1617): the stale-claim sweep exists and is green, but its two grace
thresholds are literals inside the function and its three authority refusals are not pinned
anywhere. The design (`#1265` §5 Child 2) calls for pinning them so two hosts cannot drift onto
different verdicts for the same thread — the whole point of putting the decision in ONE seam
(rule 6d). Without a floor, a later edit can silently tighten the grace and sweep an active lane;
without named limits, a reader cannot enumerate what the seam refuses.

## What Changes

- Move both threshold pairs into **pinned module constants** in `scripts/stale_claim_sweep.py`
  with matching `Makefile ?=` overrides: `STALE_AFTER_SECONDS`/`RELEASE_AFTER_SECONDS`
  (90/180 min, SILENT) and `LIVE_RUN_STALE_SECONDS`/`LIVE_RUN_RELEASE_SECONDS` (180/360 min,
  the doubled pair a run-bearing claim gets), plus per-bound FLOOR constants.
- Add the **three authority refusals** as first-class, named behaviour (`AUTHORITY_LIMITS` =
  `human`, `live-run`, `terminal`): a human/owner claim is never swept; a live-run/open-PR claim
  is never swept under the SILENT bounds (it gets the doubled pair); a terminal thread (closed
  issue or a newer `done`/`handover`/`pr`/`reviewing`/`status` comment) is never swept.
- Extend `--check` with floor assertions mirroring
  `tests/test_watch_monitor.py::test_the_rulebook_names_the_claim_settle_window`: the pinned
  constants must sit at or above their floors and every `--*-after` override below a floor is
  refused, while the floors themselves are accepted.
- Tests: the pinned pairs, the floors, the Makefile overrides, the three refusals at one age,
  and the proof assertion (a human claim and a live-run claim at 120 min emit NO line while a
  silent claim past the threshold emits one `S:<issue>:<claim-id>:stale`).

## Impact

No behaviour change beyond making the existing rules explicit and tested: the emitted marker
lines, the doubling rule, the refusals and the read-only property are unchanged. No data format,
contract, image, workflow trigger or rulebook text changes — this child pins and tests; Child 4
owns the rule-3c writing half and its rulebook rows.

## Not covered

- No AGENTS.md / §7b / §8 / §6w / §6j text (rule 3c: no agent behaviour changes here).
- No PING or RELEASE comment, no state file, no `S:` marker registration (Children 3–4).
- No change to the emitted verdict vocabulary, the `claim-id` derivation or the dedup contract.
- No CI dispatch, no merge, no `master` push, no collaborator grant, no new Actions schedule.

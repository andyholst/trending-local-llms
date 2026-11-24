# Proposal: rulebook-dispatch-guard-1586

Issue: #1586
PR: #1600

## Why

`AGENTS.md` carried **zero** hits for `dispatch-check`, `dispatch_guard` and
`ACTIVE_LANE_CEILING`: the planner's ONE pre-dispatch seam existed only in the Makefile,
`ARCHITECTURE.md` §10 and the planner skill, while the rulebook a reader consults never named it.
The guard itself landed through #1416/#1458/#1569, so the RULE was present and only its rulebook
half was missing — measured at base `6e50fc25`: §7b had no dispatch-guard bullet and §8 had no row
for `tests/test_dispatch_guard.py`, whose real suite already ran 102 checks green.

## What Changes

- Add ONE bold-led bullet to `AGENTS.md` §7b, between the implementer-PR handover bullet and the
  planner-delegation bullet, naming all four refusal classes (CLOSED issue, bound PR already
  MERGED, the ONE `ACTIVE_LANE_CEILING` default 3, a `--claim` overlapping an ACTIVE lane's path)
  plus the cross-host newer-claim refusal, and the exit contract 0 allow / 1 refuse / 2 undecidable.
- Append ONE clause to the single `Rule 3c note:` line recording that the dispatch-guard rule was
  added by this issue and is review-required.
- Add ONE row to `AGENTS.md` §8 immediately before the `tests/test_fleet_lifecycle.py` row, naming
  `tests/test_dispatch_guard.py`, its five real test functions and `make dispatch-check`.
- Add TWO names-only pin functions to the EXISTING `tests/test_dispatch_guard.py`
  (`test_rulebook_section_7b_carries_the_dispatch_guard_bullet`,
  `test_rulebook_section_8_carries_the_dispatch_guard_row`) and register both in `main()`. The pins
  assert only NAMES, never prose, so rewording the §8 row cannot red them and deleting it can.

## Impact

Purely additive documentation plus a test pin: no schema, contract, API, table, data shape, workflow
or Makefile change, and no dead code. No protected instruction file other than `AGENTS.md` is
touched; the owner authorized the `AGENTS.md` write (#1591). Disjoint from #1482 (a different §7b
region, a different §8 row after `tests/test_architecture.py`) and #1589 (its bullet before the
implementer-PR bullet, its row after `tests/test_continuous_queue_guard.py`). The one shared surface
is the `Rule 3c note` line, handled as an ordering append at the true end of the line.

## Not covered

- No change to `scripts/dispatch_guard.py`, `make dispatch-check`, the registry, the workflows or
  `ARCHITECTURE.md` — the guard and its wiring already exist and stay untouched.
- No new cron or GitHub Actions schedule, no label change, no data write.

# Proposal: fleet-mirror-union-no-duplicates

Issue: #1469
PR: #1475

## Why

`tests/test_fleet_lifecycle.py::test_second_batch_host_ahead_notes_are_landed` (PR #1463)
asserts needle PRESENCE per lane plus exactly ONE count for a single unrelated bullet. A
union that duplicates or interleaves any OTHER bullet therefore stays green: measured at
PR #1463's head `b2a26036`, the module exited 0 while the same tree grew five planner
phrases from one copy at base `84cace0b` to two and added a dangling second `chasing it.`
in the implementer mirror. `qa-validate` was green over that union and auto-merge landed it,
so the pin is blind to the exact class the issue was written to prevent.

## What Changes

- Add the pinned pre-union base revision (`UNION_BASE_SHA = 84cace0b…`) and the four mirrors
  the 2026-11-23 union wrote into (`UNION_MIRRORS`).
- Add `mirror_units()` / `unexpected_growth()`: the multiset of non-trivial whole lines AND
  punctuation-split clauses of a mirror, compared base -> head. A unit absent at base is a
  legitimate new note (0 -> 1); a unit present at base that appears MORE times at head is a
  duplicated/interleaved bullet and fails the test, naming the mirror, the unit kind and the
  counts.
- Extend `test_second_batch_host_ahead_notes_are_landed` so every landed note needle is
  asserted EXACTLY ONCE, keeping the existing presence checks and the #1463 single-bullet
  count pin verbatim.
- Add a RED-first self-test for the detector: a pure addition is silent, an exact repeated
  bullet and an interleaved repeated clause both go red.

## Impact

Test-only: no production code, data, contract, workflow or generated artifact changes. The
guard reads the REAL mirror files and the REAL pinned git revision (no mocks, rule 6m) and is
green only once master's mirror dedupe (#1456/#1468) has landed — which is the state the
assertion describes. An unreadable or empty base blob FAILS loudly rather than passing
vacuously.

## Not covered

- No mirror CONTENT change: the dedupe itself belongs to #1456/#1468.
- No AGENTS.md/ARCHITECTURE.md change (no target, stage, pipeline or image is added).

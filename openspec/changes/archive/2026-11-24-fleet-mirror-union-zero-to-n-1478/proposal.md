# Proposal: fleet-mirror-union-zero-to-n-1478

Issue: #1478

## Why

`unexpected_growth()` in `tests/test_fleet_lifecycle.py` reports a unit only when it was
already present at the pinned pre-union base:

    if head_n > base_counts.get((kind, unit), 0) and base_counts.get((kind, unit), 0) > 0

So a clause that did NOT exist at base `84cace0b38f4667eb55a7edfa1466c59ac1cec00` and that a
later union introduces TWICE (`0 -> 2`) returns `[]`. The test's own name and docstring claim
the stronger property — no non-trivial line or clause may GROW its copy count between the
pinned base revision and this tree — but the historical duplicates it was written for were all
`1 -> 2` (#1463 shipped green over those), so the `0 -> N, N >= 2` shape a future union can
produce is invisible to it.

## What Changes

- Extend `unexpected_growth()` to also flag a unit ABSENT at the pinned base when it appears
  two or more times at head (`base_count == 0 and head_n >= 2`). The new case is SCOPED so it
  cannot manufacture a false positive out of legitimate prose:
  - a whole `line` unit always qualifies;
  - a `clause` unit qualifies only when the repeats are co-located INSIDE ONE source line
    (intra-line duplication). A clause that merely recurs across two DIFFERENT bullets keeps
    the existing `base_count > 0` rule and stays silent.
- Delete the genuine debris the strengthened predicate exposes in
  `agents/tll-reviewer/skills/tll-reviewer/SKILL.md` — one bullet that carried
  `Quote the module's exit code NEXT TO the duplication you measured.` twice (an exact
  duplicate, no rule content lost).
- Extend `test_the_union_growth_detector_fires_on_a_planted_duplicate` RED-first with the
  planted intra-line `0 -> 2` case and a LOCKED false-positive case proving two distinct
  bullets sharing a clause do NOT flag.

## Impact

Test-only plus one lane-mirror dedupe: no production code, data, contract, workflow or
generated artifact behaviour changes. The guard reads the REAL mirror files and the REAL
pinned git revision (rule 6m — no mocks). Without the reviewer-mirror cleanup the strengthened
predicate reds its own tree, so the two edits are one change.

## Not covered

- No mirror CONTENT beyond removing the one duplicated sentence; a wider mirror edit belongs
  to its own issue.
- No AGENTS.md/ARCHITECTURE.md change (no target, stage, pipeline job or image is added), so
  no rulebook row is owed.

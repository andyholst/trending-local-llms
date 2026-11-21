# coverage-gap-builders-announce — the gap builders return; only announce() prints (issue #1173)

Issue: #1173
PR: #1187

## Why

`scripts/coverage_gap.py::declare_gap` BUILDS and PRINTS the gap line in one call, so every call
site — including a guard test's own demonstration — writes a `[coverage-gap]` line into the
module's stream, and `scripts/run_tests.sh` counts any line with the prefix as a declared gap
(issue #1147's counting half). Measured in the test container (issue #1173's comment): the real
container has `hermes` on PATH, so `tests/test_agent_skills.py` declares NOTHING legitimately,
yet `make test` answered `coverage-gap 2 declared` — two phantom gaps, both printed by demo calls
inside guard tests. The suite then under-reports REAL gaps: a verdict that already carries phantoms
no longer tells a reader which halves actually ran. Issue #1178 captured one demo call with
`redirect_stdout` — a call-site patch that leaves the builder printing, so the next demo, the next
module, the next agent re-creates the phantom. The seam itself must make the leak impossible.

## What Changes

- `scripts/coverage_gap.py`: `declare_gap` builds a line and RETURNS it quietly (no print);
  `declare_bypass_gap` and `external_binary_gap` likewise return quietly. A new `announce(line)`
  is the seam's ONLY print of a gap line — the only path by which a gap reaches the runner's
  stream — and its name states the act.
- The two real halves — `tests/test_agent_skills.py`'s register declaration and its teardown
  permission declaration — announce explicitly: `announce(declare_…(...))`. A guard that did not
  run announces; a demo that merely builds leaks nothing.
- `tests/test_test_container_identity.py`: the planted modules and subprocess programs move to
  the announce shape, and THREE new guard tests lock the split:
  `test_the_gap_builders_return_quietly_and_only_announce_prints`,
  `test_a_call_that_never_announced_declares_nothing_to_the_runner` (the phantom class itself:
  a module that calls the builders without announcing declares 0 gaps), and
  `test_the_seam_prints_gap_lines_only_through_announce_and_the_real_halves_announce` (source
  half: the seam prints the prefix exactly once, in `announce`; both real halves announce).
- `AGENTS.md` §8: the `tests/test_test_container_identity.py` row carries issue #1173 and the
  rule (rule 3c — review-required).

## Impact

- No new make target, pipeline job or image; the seam is already bundled into `make test` (rule 6d).
- The runner (`scripts/run_tests.sh`) does not change: its counting stays prefix-based, and the
  phantom class is removed at the SEAM, not by teaching the runner to guess which line is real.
- Existing tests updated in the same commit (rule 6b): the planted-module sources, the subprocess
  programs of the #1171 and #1172 tests, and the two source assertions that pinned the old shape.
- Not covered: making the runner distrust gap lines that appear in a guard-test module (the
  alternative Done-when in the issue — the seam-side fix was chosen; the runner keeps one simple
  contract: announce to be counted).

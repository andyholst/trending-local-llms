# coverage-gap-multi-binary — the seam declares N external CLIs in one line

Issue: #1171
PR: #1178

## Why

`coverage_gap.external_binary_gap(guard, binary, why)` names ONE binary per line (issue #1154).
A module that drives two external CLIs needs two declarations, and a module that shells out
through a wrapper script (`scripts/hermes_smoke.sh`) fails inside the wrapper before the module
can declare anything — the declaration is per-guard, not per-invocation. The seam should make
the general shape obvious, or the next module re-learns the hard way.

## What Changes

- `scripts/coverage_gap.py::external_binary_gap(guard, binary, why)` accepts a single name OR a
  sequence. It PROBES each with `shutil.which`, declares ONE line naming only the binaries this
  identity lacks, and returns `""` (printing nothing) when every binary is present — so a module
  may call it unconditionally.
- `tests/test_agent_skills.py` drops its own `shutil.which("hermes")` and lets the seam probe.
- `tests/test_test_container_identity.py`:
  - gains a guard test that drives the REAL seam in a subprocess with a stub CLI on `PATH` and
    a missing one, asserting one line names only the missing binary, the singular/plural
    wording, and that an all-present call declares nothing.
  - the issue #1154 guard stops probing `hermes` by NAME: the container HAS a real `hermes`, so
    that assertion was green on the host and red in the container. It now probes a binary that
    ships nowhere (`tll-absent-cli-1171`), and the real-`hermes` half is still driven with
    `PATH` cut.
- `AGENTS.md` §8: the `tests/test_test_container_identity.py` row carries issue #1171.

## Impact

- No new make target, pipeline job or image; the seam is already bundled into `make test`
  (rule 6d).
- Not covered: a scanner that refuses a module shelling out to an undeclared external binary
  (the issue's alternative Done-when); the tuple shape is the chosen half.

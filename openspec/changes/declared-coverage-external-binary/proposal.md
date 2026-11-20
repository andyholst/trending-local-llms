# declared-coverage-external-binary — a module declares the half that needs a CLI this identity lacks

Issue: #1154

## Why

The owner directive of 2026-11-15 moved agent work onto the host (no agent may dispatch a
pipeline), so a host `make test` is the only local verification an implementation run has.
Measured on a host with no `hermes` on `PATH`: `python3 tests/test_agent_skills.py` exits 1
with `FAIL register: --check fails on an unregistered home (exit 1) rc=2 [hermes-skills] the
\`hermes\` CLI is not on PATH …` and then a traceback
(`FileNotFoundError: <tmp>/hermes/config.yaml`), while the same module is green inside the CI
test container where the CLI exists. Three verdicts were red for a reason the pipeline would
never report, so an agent spends its repair budget on a missing binary — or learns to distrust
the local gate and push unverified. It is the coverage-blindness class #1147 filed for the
container side: a guard's real reach depends on which identity ran it, and nothing in the
verdict said so.

## What Changes

- `scripts/coverage_gap.py` gains `external_binary_gap(guard, binary, why)`: the ONE seam a
  module uses to declare a half that needs an external binary this identity does not have.
  The `BYPASS_PHRASE` travels inside the line, so the runner counts it as a DECLARED gap
  (green, named in `[harness] coverage-gap N declared`) and a bare `SKIP` stays a refusal.
- `tests/test_agent_skills.py`'s `test_setup_registers_the_directory_and_reads_it_back` runs
  its Makefile-wiring checks always, then declares the `hermes-skills register half` gap and
  returns when `shutil.which("hermes")` is None — instead of driving the real CLI into a
  `FileNotFoundError`.
- `tests/test_test_container_identity.py` pins the seam (line shape, runner counting) and
  drives the REAL module with the CLI's directory stripped from `PATH` (rule 6m: real code,
  no stand-in), asserting it stays green and declares the half.

## Impact

- No change to the runner: it already counts any line carrying `GAP_PREFIX`.
- No new target, so no ARCHITECTURE.md §6 target row; §10 regenerates because
  `scripts/coverage_gap.py`'s docstring changed (rule 6h).
- Not covered: other external-binary classes (a stale base image, a missing credential) —
  those have their own documented seams.

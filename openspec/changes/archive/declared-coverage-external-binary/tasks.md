## Tasks — #1154: declare the half that needs a CLI this identity lacks

### Seam

- [x] `scripts/coverage_gap.py::external_binary_gap(guard, binary, why)` — GAP_PREFIX + BYPASS_PHRASE inside the line
- [x] The runner needs no change: it already counts any GAP_PREFIX line as a declared gap

### Module

- [x] `tests/test_agent_skills.py` runs its `setup:` wiring checks always, then declares the `hermes-skills register half` and returns when `shutil.which("hermes")` is None
- [x] No `FileNotFoundError` traceback on a host without the CLI

### Guard

- [x] `tests/test_test_container_identity.py::test_an_external_binary_gap_keeps_a_host_run_green_and_is_counted` — line shape, runner counting, and the REAL module driven with the CLI's PATH entry stripped
- [x] A bare `SKIP` (no seam) is still refused (the pre-existing #1147 guard, unchanged)

### Rulebook

- [x] `AGENTS.md` §8's `tests/test_test_container_identity.py` row carries issue #1154 and names the external-binary seam

### Verification

- [x] `make test` green
- [x] `make validate` green
- [x] `make lint` green
- [x] `make openspec-index` then `make openspec-check` green
- [x] `make architecture-check` green (after `make architecture-refresh` — the coverage_gap docstring changed)

### Scope boundary

- No change to the runner's counting (already generic over GAP_PREFIX).
- Other external-binary classes (a stale base image, a missing credential) keep their own seams.

## Tasks — #1172: a present-but-broken CLI is a real failure, not a gap

### Seam

- [x] `external_binary_usable(binary) -> bool` — presence only, never executes the binary
- [x] `PRESENCE_IS_PRESUMED_USABLE = True` names the boundary
- [x] `external_binary_gap` probes through the one function

### Tests

- [x] `test_a_present_but_broken_cli_is_a_real_failure_not_a_declared_gap` — real seam in a
      subprocess with a stub `hermes` that exits 1; real `hermes_skills_register.py` driven by it
- [x] The absent-CLI contract (#1154) is unchanged and still locked

### Rulebook (rule 3c — review-required)

- [x] `AGENTS.md` §8: the `tests/test_test_container_identity.py` row carries issue #1172
- [x] The rule-3c notice is posted on issue #1172 naming the section and why

### Verification

- [x] `make test` green (container `make _test`)
- [x] `make validate` green (`QA PASSED`)
- [x] `make lint` green (rc=0)
- [x] `make openspec-index` then `make openspec-check` green
- [x] `make architecture-check` green (after `make architecture-refresh`)

### Scope boundary

- No new make target, pipeline job or image (rule 6d).
- The issue's first Done-when branch (the seam EXECUTES a probe command) is deliberately NOT
  taken: a probe that runs an arbitrary CLI at import time is a side effect and would launder a
  real failure into a coverage gap.

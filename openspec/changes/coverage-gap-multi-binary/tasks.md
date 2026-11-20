## Tasks — #1171: the coverage-gap seam declares N external CLIs in one line

### Seam

- [x] `external_binary_gap(guard, binary, why)` accepts `str | Sequence[str]`
- [x] It probes each binary with `shutil.which`; only the missing ones are named
- [x] Two missing → plural wording; one missing → singular
- [x] All present → returns `""` and prints nothing

### Module

- [x] `tests/test_agent_skills.py` drops its own `shutil.which("hermes")`; the seam probes

### Tests

- [x] `tests/test_test_container_identity.py::test_the_seam_declares_several_external_binaries_in_one_line_and_probes_them` — real seam in a subprocess with a stub on `PATH`
- [x] The existing guard test now asserts the module keeps no `which` of its own

### Rulebook (rule 3c — review-required)

- [x] `AGENTS.md` §8: the `tests/test_test_container_identity.py` row carries issue #1171
- [x] The rule-3c notice is posted on issue #1171 naming the section and why

### Verification

- [x] `make validate` green — `QA PASSED`
- [x] `make lint` green
- [x] `make openspec-index` then `make openspec-check` green
- [x] `make architecture-check` green (after `make architecture-refresh`)
- [x] `make test` green — the container `make _test`: 140 modules passed, 0 failed (the host runner lacks `markdown-it-py`)

### Scope boundary

- No new make target, pipeline job or image (rule 6d).
- The issue's alternative Done-when — a scanner refusing a module that shells out to an
  undeclared external binary — is NOT covered.

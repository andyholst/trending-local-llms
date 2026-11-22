# Proposal: nerve-check-test-value-marker

Issue: #1277
PR: #1283

## Why

`scripts/nerve_key_check.py::scan_tree` flags every credential SHAPE in every
tracked pipeline file with no exemption, while `scripts/check_secret_output.py`
accepts a deliberate test value when its file carries the sanctioned marker
`secret-output: test value` (`TEST_VALUE_MARKER`, the ONE definition). A test
file that follows the rulebook's own advice therefore reds `make nerve-check`
while passing `make check-secret-output` — measured on PR #1274 head
`4da3154a`: `tests/test_agent_hermes_smoke.py` carries the marker and a
`sk-…` literal; qa-validate run `45003287466` job `validate` failed with
`tests/test_agent_hermes_smoke.py: anthropic/openai key at offset 3179`,
while the same file passed the secret-output step.

## What Changes

- `nerve_key_check` imports `TEST_VALUE_MARKER` from `check_secret_output`
  (one definition — never a second literal) and `scan_tree` skips the SHAPE
  scan for a file whose text carries it, exactly as `check_secret_output`
  exempts that file.
- `tests/test_nerve_key_wiring.py` locks it: a marked file carrying a
  key-shaped literal is exempt, an unmarked file with the same literal is still
  a finding, the marker is the imported constant (no re-spelled literal), and
  the guard is RED on the pre-change tree.

## Impact

- `scripts/nerve_key_check.py` — one import plus one exemption in `scan_tree`.
- `tests/test_nerve_key_wiring.py` — one new test function.
- No make target, workflow, contract or rulebook change.

## Not covered

- Exempting a marked file from the OTHER nerve checks (Dockerfile / Makefile /
  workflow): the marker is a test-file convention and those checks read
  different files.
- A real credential committed into a marked file: the marker is the rulebook's
  declared trust boundary, identical to `check-secret-output`.

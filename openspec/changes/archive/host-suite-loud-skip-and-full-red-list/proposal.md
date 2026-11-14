# Proposal: host-suite loud skip and full red list

Issue: #890
PR: #945

## Why

Issue #890: the host `make test` misleads its operator. `scripts/run_tests.sh`
stops at the first red, so discovering every host-vs-container false red takes
several re-run cycles (measured during #636: three cycles). And
`tests/test_hermes_update_needed.py` crashes with `FileNotFoundError: 'faketime'`
on a host without libfaketime — a traceback instead of a signal that the gate's
precondition is missing. (The third #890 item — the `missing gh` fixture — is
already satisfied on this tree: `test_a_missing_gh_is_loud` runs the script with
PATH *replaced* by an empty dir.)

## What Changes

- `scripts/run_tests.sh` runs **every** discovered module even after a failure,
  shows each failing module's output, and ends with the full `FAILED:` list
  once. Exit codes are unchanged (0 green, 1 any red, 2 usage).
- `tests/test_hermes_update_needed.py` checks its `faketime` precondition up
  front and prints a loud `SKIP:` naming the missing tool, exiting 0, instead
  of raising `FileNotFoundError`.
- New `tests/test_test_runner.py` locks both behaviours against the **real**
  runner: a fixture tests-dir with several red modules must report ALL of them
  in one pass, and the update gate with `faketime` off PATH must exit 0 naming
  the SKIP (external-system stand-ins only, rule 6m).

## Impact

- Affected specs: `test-harness` (new capability).
- Affected code: `scripts/run_tests.sh`, `tests/test_hermes_update_needed.py`,
  new `tests/test_test_runner.py`.
- No make target, workflow, image or data change; CI behaviour is unchanged
  (a green suite stays identical; a red one now lists every red module).

## Not covered

- Fixing the fixtures that assume container tooling (PATH-prepend stubs that
  could pick up host binaries). #890 permits the explicit loud SKIP instead;
  per-fixture PATH replacement is left to future changes if a false red appears.

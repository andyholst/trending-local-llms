# Proposal: agent-shell-keys-loud-skip-946

Issue: #946
PR: #948

## Why

`make test` on the host is red on a gate that can never run there. `tests/test_agent_shell_keys.py`
drives the real Hermes terminal probe through `scripts/agent_shell_keys_check.py`, and the host's
Hermes install cannot build its own terminal environment — measured 2026-11-14: the probe runs
under `~/.hermes/hermes-agent/venv/bin/python` and dies inside Hermes's own import chain
(`hermes_yaml.py` → `ModuleNotFoundError: No module named 'ruamel'`), reported as
`the Hermes terminal probe produced no result (rc=1): read_interrupted`. Eight checks failed on the
host every host run — environment facts, not repo defects — diluting the loudest host signal,
exactly the class issue #890 removed for `faketime` and #895 addresses for `gh` fixtures.

The existing NO-SKIP policy is right where CI runs (the pinned test image carries the same Hermes
the bots run) and must stay authoritative there. The gap: OUTSIDE that image there is no way to say
"this machine's Hermes install cannot resolve the probe" loudly without pretending the gate ran.

## What Changes

- `scripts/agent_shell_keys_check.py` gains the decision (rule 6d, one implementation): when the
  probe cannot run because the local Hermes checkout/interpreter is absent or cannot import its own
  terminal env (`WIRING_UNRESOLVABLE`: `ModuleNotFoundError` / `ImportError` / `No module named` /
  the checkout-or-interpreter messages), and the environment is OUTSIDE the pinned test image
  (`in_container()`: the Makefile's own `IN_CONTAINER` when given — "overridable for the tests
  only" — else `/.dockerenv`, since `DOCKER_RUN` forwards no such env), the check prints a LOUD
  `SKIP [wiring]` line naming the gate's authoritative home and exits 0. Inside the marker the same
  failure stays exit 2 FATAL. A credential not set remains exit 2 everywhere; a probe failure that
  is NOT an import/wiring class remains exit 2 everywhere.
- `tests/test_agent_shell_keys.py` reports the two real-probe groups as loud `skip` lines when the
  script says `SKIP [wiring]`, counts them in a new SKIPPED total, and adds
  `test_probe_wiring_unresolvable_decides_loudly_by_container_marker`: a fixture Hermes checkout
  whose `tools/environments/local.py` cannot import (the measured host class) is driven through the
  REAL script with `IN_CONTAINER=0` → exit 0 + loud SKIP, and `IN_CONTAINER=1` → exit 2 FATAL —
  same assertions on the host and in CI. The fixture stands in for the EXTERNAL Hermes install only
  (rule 6m); the decision code is the product's.
- The module docstring and the script docstring state the policy both ways.

## Impact

- `scripts/agent_shell_keys_check.py`, `tests/test_agent_shell_keys.py`.
- Capability: `bot-agent-run-safety` (same as #359's `agent-shell-keys` change).
- No Makefile, workflow or contract change: `make agent-shell-keys-check` stays a `DOCKER_RUN`
  wrapper, so a host invocation of the TARGET still runs the gate inside the container, and
  qa-validate's `live-smoke` leg is untouched.

## Not covered

- Fixing the HOST's Hermes install (its missing `ruamel` dep) — that is the user's machine, not the
  repo; the gate only stops lying about it.
- Any other test module's host-skip policy (#895's `gh` fixtures, #890's `faketime`).

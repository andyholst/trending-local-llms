# Tasks: agent-shell-keys-loud-skip-946

- [x] `scripts/agent_shell_keys_check.py`: classify an unresolvable Hermes terminal probe
      (`WIRING_UNRESOLVABLE`) and the environment (`in_container()`: `IN_CONTAINER` when given,
      else `/.dockerenv`) — verified by the fixture runs both ways
- [x] SKIP decision: outside the marker the unresolvable probe exits 0 with a loud `SKIP [wiring]`
      line; inside it the same failure stays exit 2 `FATAL`; a missing credential and a non-import
      probe failure stay exit 2 everywhere — verified (`IN_CONTAINER=0` → exit 0 SKIP,
      `IN_CONTAINER=1` → exit 2 FATAL, through the real script)
- [x] `tests/test_agent_shell_keys.py`: the two real-probe groups report the script's skip as a
      counted loud `skip` line (`probe_skipped`), summary prints `SKIPPED` — verified on the host
      (PASSED 37 | SKIPPED 2 | FAILED 0, exit 0)
- [x] Guard test `test_probe_wiring_unresolvable_decides_loudly_by_container_marker` drives the
      REAL script against a fixture Hermes checkout whose terminal env cannot import (the measured
      host class), both container markers, sentinel never printed — verified green
- [x] Module and script docstrings state the policy both ways
- [x] Host run of the module exits 0 with FAILED 0 (the 8 host reds this issue measured are gone)
- [ ] `make lint`, `make openspec-check` and `make openspec-index-check` green on the branch
- [ ] CI green on the PR and the change archived (PR recorded) at the merge head

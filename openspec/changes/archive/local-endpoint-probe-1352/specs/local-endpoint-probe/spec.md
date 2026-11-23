## ADDED Requirements

### Requirement: The chain's local tier is probed with a capped timeout and the result is recorded

`local-endpoint-probe` SHALL read the `local_fallback` step's OWN `base_url` and `model` from
`agents/model_chain.json` (the ONE chain), POST a one-token chat completion with a CAPPED timeout
(`LOCAL_PROBE_TIMEOUT_SECONDS`, default 20), and record the result in the chain's `measured.local`
as `last_probe` plus an additive `probe_history`. The local tier is credential-less, so the seam
SHALL read, name and print no credential. A 2xx payload carrying a `choices` list is `ok`; any
other outcome is `DOWN` and is still recorded, because the outage IS the signal.

#### Scenario: A live local endpoint is recorded as ok

- **Given** a scratch tree whose `local_fallback` tier points at a REAL local HTTP server that answers `200 {"choices": [{"message": {"content": "pong"}]}`
- **When** `local-endpoint-probe --probe` runs
- **Then** it exits 0 and writes `measured.local.last_probe` with `ok: true`, `http: 200`, the tier's endpoint and model, and an additive `probe_history` row
- **Test:** tests/test_local_endpoint_probe.py::test_a_live_endpoint_is_probed_recorded_and_reported

#### Scenario: A dead local endpoint is recorded as DOWN, not silently dropped

- **Given** a scratch tree whose `local_fallback` tier points at a port where nothing listens
- **When** `local-endpoint-probe --probe` runs
- **Then** it exits 1, prints `DOWN`, and still records `measured.local.last_probe` with `ok: false`
- **Test:** tests/test_local_endpoint_probe.py::test_a_dead_endpoint_is_recorded_as_down_and_the_check_reports_it

#### Scenario: A slow local endpoint cannot hang the seam

- **Given** a REAL local HTTP server that delays its answer past the timeout pin
- **When** `local-endpoint-probe --probe --timeout 1` runs
- **Then** it exits 1 well before the server answers, and the recorded `latency_s` respects the cap
- **Test:** tests/test_local_endpoint_probe.py::test_a_slow_endpoint_is_capped_by_the_timeout_pin

### Requirement: The offline check refuses a missing or drifted record and reports staleness without touching the endpoint

`local-endpoint-probe-check` SHALL run offline (no network) and read the committed record. It
SHALL exit 1 when `measured.local.last_probe` is absent, or when its `endpoint`/`model` no longer
match the chain's `local_fallback` tier (the record did not follow the chain). It SHALL exit 2 when
the chain or the record cannot be read. When the record is present and matching it SHALL exit 0
and print the state and age, marking `STALE` loudly when the age exceeds
`LOCAL_PROBE_MAX_AGE_HOURS` — a stale record is REPORTED, never a merge gate, so auto-merge cannot
depend on a host box.

#### Scenario: A chain that was never probed is refused

- **Given** a scratch tree whose chain carries no `measured.local.last_probe`
- **When** `local-endpoint-probe-check` runs
- **Then** it exits 1 and names the `make local-endpoint-probe` remedy
- **Test:** tests/test_local_endpoint_probe.py::test_a_missing_record_is_refused_and_a_drifted_record_is_refused

#### Scenario: A record that did not follow the chain is refused

- **Given** a recorded probe whose endpoint no longer equals the chain's `local_fallback` `base_url`
- **When** `local-endpoint-probe-check` runs
- **Then** it exits 1, naming both the recorded and the current endpoint
- **Test:** tests/test_local_endpoint_probe.py::test_a_missing_record_is_refused_and_a_drifted_record_is_refused

#### Scenario: A stale record is reported loudly but does not fail

- **Given** a present, matching record whose `at` is older than `LOCAL_PROBE_MAX_AGE_HOURS`
- **When** `local-endpoint-probe-check` runs
- **Then** it exits 0 and prints `STALE` with the age in hours
- **Test:** tests/test_local_endpoint_probe.py::test_a_stale_record_is_reported_loudly_without_failing

#### Scenario: An unreadable chain is a loud exit 2

- **Given** a truncated or missing `agents/model_chain.json`
- **When** `local-endpoint-probe-check` (or `--probe`) runs
- **Then** it exits 2 with `UNDECIDABLE`, never a silent clean
- **Test:** tests/test_local_endpoint_probe.py::test_an_unreadable_chain_is_exit_2_never_a_silent_clean

### Requirement: The offline half is wired to a gate and the live half is not

`local-endpoint-probe-check` SHALL be reachable from `make lint` (the first gate of
`qa-validate`'s `validate` job and of `scripts/fix_loop.sh`), and no workflow SHALL reach
`scripts/local_endpoint_probe.py` past the Makefile. The LIVE `local-endpoint-probe` SHALL NOT be
wired into any merge gate, and the pins SHALL be read from the ONE Makefile so a weakened cap or
staleness window is refused.

#### Scenario: The gate wiring is present and the live probe is not a merge gate

- **Given** the repository's Makefile and workflows
- **When** the wiring check runs
- **Then** `make lint` calls `local-endpoint-probe-check`, the internal recipe runs the script, no workflow names the script, and `qa-validate.yml` does not run the live probe
- **Test:** tests/test_local_endpoint_probe.py::test_the_seam_is_wired_where_it_bites

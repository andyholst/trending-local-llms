## ADDED Requirements

### Requirement: One starved leg is a note when the mirror answered another leg

`smoke_search.py::main` SHALL collect every leg's probe outcomes and SHALL treat
a leg whose entire query set missed the budget as a non-blocking `QUERY-STARVED`
note when at least one other leg in the SAME run got an HTTP 200 from the mirror.
The note SHALL name the leg and state that another leg proved the mirror
reachable. A run in which NO leg proved reachability SHALL still fail with the
#258 majority verdict; the #858 answered-but-empty vocabulary gate is unchanged.

#### Scenario: One dead leg with a healthy leg is not a source outage

- **Given** a scripted transport where all cpu queries time out while nvidia, metal and amd answer HTTP 200
- **When** `main()` evaluates all four legs
- **Then** it exits 0, prints `QUERY-STARVED` naming cpu, and prints no `leg(s) failed` line
- **Test:** tests/test_smoke_search.py::test_one_query_starved_leg_is_not_a_source_outage

#### Scenario: A per-backend invocation proves the source with a canary

- **Given** `main()` is invoked with `--backend cpu` (as qa-validate does — one process per leg) and every cpu query misses
- **When** the nvidia canary query answers HTTP 200 from the same mirror
- **Then** cpu exits 0 with a `QUERY-STARVED` note, while a canary that also misses leaves the #258 block in force
- **Test:** tests/test_smoke_search.py::test_a_single_backend_invocation_uses_the_canary

#### Scenario: A mirror that answers nothing still blocks

- **Given** a scripted transport where every query of every leg times out
- **When** `main()` evaluates all four legs
- **Then** it exits 2 with the `a MAJORITY of budget-missed queries is a dead or unreachable source` verdict
- **Test:** tests/test_smoke_search.py::test_a_full_outage_still_blocks_every_leg

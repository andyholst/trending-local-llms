## ADDED Requirements

### Requirement: Both grace pairs are pinned and overridable

The sweep SHALL carry BOTH grace pairs as pinned module constants — `STALE_AFTER_SECONDS` /
`RELEASE_AFTER_SECONDS` = 90/180 minutes for a SILENT claim, and `LIVE_RUN_STALE_SECONDS` /
`LIVE_RUN_RELEASE_SECONDS` = 180/360 minutes (the doubled pair) for a claim whose own text carries
a CI run id or a PR number — with a matching `Makefile ?=` override per bound and a per-bound
floor the offline contract refuses to cross.

#### Scenario: The silent pair is 90/180 minutes

- **Given** the module's pinned constants
- **When** the contract test reads them
- **Then** the SILENT pair is exactly 90/180 minutes
- **Test:** tests/test_stale_claim_sweep.py::test_the_threshold_pairs_are_pinned_with_floors_and_makefile_overrides

#### Scenario: The live-run pair is the doubled 180/360 minutes

- **Given** the module's pinned constants
- **When** the contract test reads them
- **Then** the LIVE-RUN pair is twice the SILENT pair, exactly 180/360 minutes
- **Test:** tests/test_stale_claim_sweep.py::test_the_threshold_pairs_are_pinned_with_floors_and_makefile_overrides

#### Scenario: Every bound sits at or above its floor

- **Given** the four pinned bounds and their four floors
- **When** the contract test compares them
- **Then** no pinned bound is below its floor
- **Test:** tests/test_stale_claim_sweep.py::test_the_threshold_pairs_are_pinned_with_floors_and_makefile_overrides

#### Scenario: The Makefile carries the same seconds

- **Given** the `stale-claim-sweep` recipe and its four `?=` knobs
- **When** the contract test reads the Makefile
- **Then** each knob equals the module constant it overrides and the recipe forwards all four
- **Test:** tests/test_stale_claim_sweep.py::test_the_threshold_pairs_are_pinned_with_floors_and_makefile_overrides

#### Scenario: The offline contract refuses a weaker floor

- **Given** `--check` invoked with a bound one second below its floor
- **When** the offline contract runs
- **Then** it exits 2, and the floor value itself is accepted with exit 0
- **Test:** tests/test_stale_claim_sweep.py::test_the_threshold_pairs_are_pinned_with_floors_and_makefile_overrides

### Requirement: The three authority limits refuse a claim

The sweep SHALL name its three authority limits (`AUTHORITY_LIMITS` = `human`, `live-run`,
`terminal`) and SHALL emit NOTHING for a claim under the human or terminal limit, and NEVER apply
the SILENT bound to a claim under the live-run limit.

#### Scenario: A human claim and a live-run claim at the same age emit nothing

- **Given** four open threads with a 120-minute-old newest claim — one by a lane outside the
  fleet, one carrying `R:<id>`, one carrying `PR #<n>`, one closed — beside a silent claim of the
  same age
- **When** the pure decision runs
- **Then** the human, live-run, open-PR and terminal threads emit NO line while the silent claim
  emits one `S:<issue>:<claim-id>:stale`
- **Test:** tests/test_stale_claim_sweep.py::test_the_three_authority_limits_emit_nothing_at_the_same_age

#### Scenario: The three limits are enumerated in one place

- **Given** the module's `AUTHORITY_LIMITS`
- **When** the contract test reads it
- **Then** it is exactly `("human", "live-run", "terminal")`
- **Test:** tests/test_stale_claim_sweep.py::test_the_three_authority_limits_emit_nothing_at_the_same_age

# card-scope-gate

## ADDED Requirements

### Requirement: A stated pool total counts as the VRAM of the run

`hardware_vram_gb()` MUST return the total GPU memory a hardware string states, taking
an explicit `<n> GB total` over any per-card size and applying a multiplier written
either before (`2x 3090`) or after (`32GB x8`) the size.

#### Scenario: the pool total is stated in the string

- **Given** the hardware text `Radeon Pro V620 32GB x8 (256GB total, homelab cluster)`
- **When** `hardware_vram_gb()` reads it
- **Then** it returns 256, not the per-card 32
- **Test:** tests/test_trend_score.py::test_vram_parsing

#### Scenario: the multiplier follows the size

- **Given** `32GB x8` and `24GB x2`
- **When** `hardware_vram_gb()` reads them
- **Then** they return 256 and 48
- **Test:** tests/test_trend_score.py::test_vram_parsing

### Requirement: AMD datacenter V-series hardware is never in scope

A measurement whose hardware names a Radeon Pro V-series part (V620/V520/V340) MUST be
out of scope whatever its stated memory, while Radeon Pro W-series workstation cards
stay in scope.

#### Scenario: a multi-card V620 pool is out of scope

- **Given** a measurement on `Radeon Pro V620 32GB x8 (256GB total, …)`
- **When** `in_scope()` evaluates it
- **Then** it is False
- **Test:** tests/test_trend_score.py::test_a_multi_card_pool_is_never_a_card_you_can_buy

#### Scenario: a single V620 is out, a W7900 is in

- **Given** measurements on `Radeon Pro V620 32GB` and `Radeon Pro W7900 48GB`
- **When** `in_scope()` evaluates them
- **Then** the V620 is False and the W7900 is True
- **Test:** tests/test_trend_score.py::test_a_multi_card_pool_is_never_a_card_you_can_buy

### Requirement: The figure a card owner reads is the best IN-SCOPE one

Where a model has both a cluster figure and an in-scope figure, `best_in_scope()` MUST
return the in-scope measurement.

#### Scenario: the cluster is faster than the card

- **Given** a model measured at 100 t/s on a 256 GB V620 pool and 58 t/s on a Strix Halo
- **When** `best_in_scope()` chooses the figure for the most-loved cell
- **Then** it returns the 58 t/s measurement
- **Test:** tests/test_trend_score.py::test_a_multi_card_pool_is_never_a_card_you_can_buy

# card-fit

## ADDED Requirements

### Requirement: Tiers above 48 GB are answered with evidence

The README MUST render the 64/128/256/512 GB tiers, each with rows from the store or a named
collection gap, using a ladder whose evidence is the run's total memory or the model's weight
footprint, and `check_card_tables` MUST validate those tiers with that ladder — never with the card
rule.

#### Scenario: a model that needs more than a consumer card

- **Given** a model whose weights are 111 GB, served on a machine with 128 GB
- **When** the tiers are computed
- **Then** it is placed in the 128 GB tier as `ran-on` and not in the 64 GB tier
- **Test:** tests/test_card_fit.py::test_above_48_gb_needs_more_than_a_consumer_card

#### Scenario: a model that fits a card is not listed above 48 GB

- **Given** an 8B model with a 2 GB footprint, served on a 64 GB Mac mini
- **When** the 64 GB tier is computed
- **Then** it is not placed there
- **Test:** tests/test_card_fit.py::test_above_48_gb_needs_more_than_a_consumer_card

#### Scenario: a weight footprint that contradicts the model is refused

- **Given** a 9B model stating 2 GB of weights and a measurement claiming 493 GB
- **When** the footprint is read
- **Then** the model's own footprint is used and that measurement places nothing
- **Test:** tests/test_card_fit.py::test_a_weight_footprint_that_contradicts_the_model_is_refused

#### Scenario: the validator catches a falsified above-48-GB row

- **Given** a rendered README whose 128 GB row was changed
- **When** `check_card_tables` runs
- **Then** it fails naming `card-fit[above-48]` and the tier
- **Test:** tests/test_card_fit.py::test_the_validator_catches_an_above_48_gb_row_that_disagrees

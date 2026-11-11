# card-fit

## ADDED Requirements

### Requirement: A model with no card-tier row is named, and the reason is split

The `readme` stage MUST report every model that places in no card tier, split into
`unified memory / CPU-only` (not a gap) and `no card figure collected` (a search target),
and MUST name the actionable models.

#### Scenario: the two reasons

- **Given** a model that ran on an 8 GB card, one measured only on Apple Silicon, one only on CPU, one on a B300, and one on a 96 GB GPU
- **When** `card_gap_reason()` is asked
- **Then** the first has no gap, the Metal and CPU models are `unified memory / CPU-only`, and the datacenter and above-tier models are `no card figure collected`
- **Test:** tests/test_card_gap_report.py::test_the_two_reasons_are_told_apart

#### Scenario: the report

- **Given** that fixture store
- **When** the report runs
- **Then** it counts 4 of 5 with no row, splits 2/2, names only the two actionable models, and lists no placed model
- **Test:** tests/test_card_gap_report.py::test_the_report_names_the_models_it_can_act_on

#### Scenario: a degenerate store

- **Given** an empty store or a model with no measurements
- **When** the report runs
- **Then** it reports and never raises
- **Test:** tests/test_card_gap_report.py::test_the_report_never_fails_and_survives_a_degenerate_store

### Requirement: The report is wired into a stage CI runs

The check MUST be registered under `readme`, and that stage MUST be selected by a make target
(rule 6d).

#### Scenario: the wiring is read

- **Given** `scripts/validate.py` and the `Makefile`
- **When** the guard reads them
- **Then** the check is registered under `readme` and `--only readme` exists
- **Test:** tests/test_card_gap_report.py::test_the_check_is_wired_into_the_readme_stage

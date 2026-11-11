# vram-tier

## ADDED Requirements

### Requirement: The vram_tier vocabulary is reported, never silently accepted

`validate.py` MUST print, on every `data`-stage run, the `vram_tier` distribution, every
unit-less value (a spelling of `NNGB`) and every value outside the documented categories,
and MUST NOT fail the run for any of them.

#### Scenario: a store with a unit-less and an out-of-category value

- **Given** models whose `vram_tier` values are `48`, `48GB`, `9GB` and `CPU`
- **When** the data stage runs
- **Then** the report names `48` as unit-less and `9GB` as outside the categories, does not report `48GB` or `CPU`, and the run exits 0
- **Test:** tests/test_vram_tier_vocabulary.py::test_the_report_names_the_distribution_and_the_two_defect_shapes

#### Scenario: a degenerate store

- **Given** an empty store, a model without the key, or a junk value
- **When** the data stage runs
- **Then** it reports and never raises
- **Test:** tests/test_vram_tier_vocabulary.py::test_the_check_never_fails_a_run

### Requirement: The store carries no unit-less tier

Every `vram_tier` in `data/models.json` MUST carry its unit (`NNGB`) or be `CPU`; a bare
number is the same category misspelled.

#### Scenario: the real store

- **Given** `data/models.json`
- **When** the guard inspects it
- **Then** no model's `vram_tier` is a bare number
- **Test:** tests/test_vram_tier_vocabulary.py::test_the_real_store_has_no_unitless_tier

### Requirement: The report is wired into a stage CI runs

The check MUST be registered under the `data` stage, and that stage MUST be selected by a
make target (rule 6d).

#### Scenario: the registration is read

- **Given** `scripts/validate.py` and the `Makefile`
- **When** the guard reads them
- **Then** the check is registered under `data` and `--only data,removal` exists
- **Test:** tests/test_vram_tier_vocabulary.py::test_the_check_is_wired_into_the_data_stage

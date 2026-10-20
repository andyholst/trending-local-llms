# card-fit

## ADDED Requirements

### Requirement: A split requirement names both halves

A `vram_min` that states a GPU capacity **and** system RAM MUST render as `<n>GB + system
RAM` with `declared` evidence, and MUST NOT be published as the bare capacity.

#### Scenario: the store's prose value

- **Given** `vram_min` = `"system RAM holds the expert set (32GB GPU + system RAM)"`
- **When** `vram_need()` is asked
- **Then** it returns `("32GB + system RAM", "declared")`
- **Test:** tests/test_card_fit.py::test_vram_need_prefers_what_the_source_states

#### Scenario: values that are not a split

- **Given** `"16GB RAM"` and `"8GB RAM (no GPU)"`
- **When** `vram_need()` is asked
- **Then** each returns its plain capacity, because neither names a GPU capacity the model needs
- **Test:** tests/test_card_fit.py::test_vram_need_prefers_what_the_source_states

### Requirement: Prose requirements are reported

The `data` stage MUST print every `vram_min` that is not a plain capacity, and MUST NOT fail
for it.

#### Scenario: the report

- **Given** a store with `"8GB"`, `"32GB GPU + system RAM"` and `"CPU"`
- **When** the data stage runs
- **Then** only the prose value is named
- **Test:** tests/test_vram_tier_vocabulary.py::test_the_vram_min_report_names_prose_values

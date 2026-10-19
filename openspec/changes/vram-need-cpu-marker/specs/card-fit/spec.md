# card-fit

## ADDED Requirements

### Requirement: A CPU-only declaration is a stated requirement, not a gap

When `vram_min` declares that no GPU is needed (`CPU`, `cpu only`, `CPU-only`), the model's
least requirement MUST render as `CPU only` with the `declared` evidence, and MUST NOT fall
through to the coarse tier, the smallest card it ran on, or `not stated`.

#### Scenario: the three marker spellings

- **Given** models whose `vram_min` is `CPU`, `cpu only` and `CPU-only`
- **When** `vram_need()` is asked
- **Then** each returns `("CPU only", "declared")`
- **Test:** tests/test_card_fit.py::test_vram_need_prefers_what_the_source_states

#### Scenario: a prose requirement that mentions system RAM

- **Given** `vram_min` = `"system RAM holds the expert set (32GB GPU + system RAM)"`
- **When** `vram_need()` is asked
- **Then** it is NOT read as CPU-only (that value names a GPU too)
- **Test:** tests/test_card_fit.py::test_vram_need_prefers_what_the_source_states

#### Scenario: the README cell

- **Given** a CPU-only model in the store
- **When** the README is rendered
- **Then** its most-loved VRAM cell reads `**CPU only**`, never `not stated`
- **Test:** tests/test_card_fit.py::test_vram_need_prefers_what_the_source_states

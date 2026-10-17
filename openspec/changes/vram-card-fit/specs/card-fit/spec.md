# card-fit

## ADDED Requirements

### Requirement: A card owner can see what fits their VRAM tier

The README MUST carry a generated card-fit section with one table per VRAM tier
(8 / 12 / 16 / 24 / 32 / 48 GB) and an anchor index to each, so a reader who owns a
card can find their tier in one click. The low end this index prioritises MUST be
stated as a gaming laptop, 8-24 GB of VRAM. A model MUST be listed in a tier only
with evidence, and the evidence MUST be shown in the row.

WHEN a reader opens the README,
THEN the card-fit section lists, per tier, the fastest model with evidence for a card
of that size, with its engine, hardware, quant and the evidence behind the claim.

#### Scenario: a run on a 12 GB card qualifies 12 GB and 24 GB, never 8 GB

- **Given** a model with a measurement whose hardware is a 12 GB card
- **When** the fit of that measurement is evaluated for each tier
- **Then** it qualifies 12 GB and 24 GB as `ran-on`, and 8 GB not at all
- **Test:** `tests/test_card_fit.py::test_ran_on_is_proved_by_the_run`

#### Scenario: a bigger card does not qualify a smaller tier

- **Given** a measurement on a 32 GB card whose post states a 5.95 GB weight footprint
- **When** the fit is evaluated for 16 GB and for 8 GB
- **Then** 16 GB is not `ran-on`, and 8 GB is `weights-only` — labelled as such in the README, never sold as a fit
- **Test:** `tests/test_card_fit.py::test_a_bigger_card_does_not_qualify_a_small_tier`

#### Scenario: an empty tier says so instead of reading as "nothing fits"

- **Given** a store with no measurement having evidence for a tier
- **When** the README is rendered
- **Then** that tier carries a named collection gap, pointing at the searches that would fill it
- **Test:** `tests/test_card_fit.py::test_the_readme_shows_the_card_view`

### Requirement: A datacenter figure is never "what fits your card"

A measurement on datacenter hardware MUST never place a model in a card tier, and
MUST never be the figure a card owner reads in the most-loved table. The speed bonus
and the displayed best cells MUST use the same scope gate, so the two can never
disagree. A datacenter SKU family is named by its FAMILY: a bare `B300` counts.

WHEN a model's only figure is a datacenter one,
THEN it appears in no card tier and in no most-loved best cell, while it keeps its row in the backend table.

#### Scenario: a bare B300 is datacenter hardware

- **Given** a measurement whose hardware reads "single NVIDIA B300 GPU (datacenter)"
- **When** the scope gate is evaluated
- **Then** it is out of scope, earns no speed bonus, and places its model in no card tier
- **Test:** `tests/test_card_fit.py::test_a_datacenter_figure_never_places_a_model`

#### Scenario: Apple Silicon and CPU are judged by unified memory, not by a card tier

- **Given** a model measured only on Apple Silicon
- **When** the card tiers are derived
- **Then** it is placed in no card tier, and its figure is still rendered in the Metal table
- **Test:** `tests/test_card_fit.py::test_apple_and_cpu_are_not_card_tiers`

### Requirement: The most-loved VRAM cell states the least amount needed to run

The most-loved `VRAM` cell MUST state the least VRAM needed to run the model, derived
from what the source states (`vram_min`), then the coarse `vram_tier`, then the
smallest card it was measured on, and it MUST name which of those the claim rests on.
Where nothing supports a claim it MUST say so rather than print a category.

WHEN the store carries a coarse tier smaller than the model's own stated minimum,
THEN the published requirement is the stated minimum, and the cell names its evidence.

#### Scenario: the stated minimum wins over a smaller category

- **Given** a model with `vram_min` "32GB" and `vram_tier` "16GB"
- **When** its requirement is derived
- **Then** the answer is 32GB, identified as declared by the source
- **Test:** `tests/test_card_fit.py::test_vram_need_prefers_what_the_source_states`

#### Scenario: unknown is reported, never invented

- **Given** a model whose source states no VRAM and whose hardware names no card
- **When** its requirement is derived
- **Then** the answer is `unknown` and the README cell says so
- **Test:** `tests/test_card_fit.py::test_vram_need_prefers_what_the_source_states`

### Requirement: The card-fit tables are validated, not trusted

The card-fit section MUST be verified against the ONE derivation the renderer uses:
every model the derivation places in a tier is present in that tier's rendered rows,
in the same order, with an evidence tag; an empty tier is a loud collection gap; and
the anchor index links every tier. The check MUST be reachable from a make target CI
runs (rule 6d).

WHEN a README drops a model from a tier, or loses the section, or loses an anchor,
THEN `make validate` fails and names what is missing.

#### Scenario: a dropped row fails the gate

- **Given** a rendered README with one tier row removed by hand
- **When** the validation runs
- **Then** it fails, naming the tier whose rows differ from the store's evidence
- **Test:** `tests/test_card_fit.py::test_the_validator_catches_a_dropped_row`

#### Scenario: the searches ask for the low-end cards

- **Given** the four search legs and the bounded smoke
- **When** they are read
- **Then** each names gaming-PC cards (3060 / 4060 / 4060 Ti / 4070, Radeon 6600 / 7600 / 9060 XT) and the `8gb`/`16gb vram` sizes
- **Test:** `tests/test_card_fit.py::test_the_low_end_is_a_gaming_laptop`

### Requirement: A footprint can be recorded per measurement

The measurement item of both contracts MUST declare OPTIONAL `weight_gb`,
`context_tokens`, `system_ram_min` and `storage_offload`, so a post can state the
footprint of the run behind a t/s figure. The keys MUST NOT be `required`, and no
existing key MUST be renamed or removed (rule 3b).

WHEN a raw snapshot states a per-measurement weight footprint,
THEN it survives ingest into the store and is accepted by both contracts.

#### Scenario: the per-measurement keys are optional and additive

- **Given** the store and search contracts
- **When** the measurement item is inspected
- **Then** the four footprint keys are declared as optional and none is in a `required` list
- **Test:** `tests/test_card_fit.py::test_a_bigger_card_does_not_qualify_a_small_tier`

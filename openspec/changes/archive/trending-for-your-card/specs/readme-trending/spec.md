# readme-trending

## ADDED Requirements

### Requirement: A datacenter class of machine never earns speed or a best cell

`in_scope()` MUST refuse a measurement whose hardware names a datacenter class rather than a card
(a `datacenter` / `data centre` phrase, with or without a named SKU), so the measurement earns no
speed bonus and is never the "best" figure a card owner is shown. It MUST stay in the store and in
its backend table.

#### Scenario: the measured 28,340 t/s aggregate

- **Given** a measurement on `datacenter GPUs, 512 concurrent requests` at 28,340 t/s and one on an RTX 5090 at 500 t/s
- **When** the scope gate and the speed bonus are asked about the model
- **Then** the datacenter measurement is out of scope, `best_in_scope()` is the 5090 figure, and the speed bonus is `log2(1 + 500/10)`
- **Test:** tests/test_trending_for_your_card.py::test_a_datacenter_class_never_earns_speed

#### Scenario: a spelled class

- **Given** hardware reading `Data Center cluster, 8 nodes`
- **When** the scope gate is asked
- **Then** it is out of scope, exactly like `single NVIDIA B300 GPU (datacenter)`
- **Test:** tests/test_trending_for_your_card.py::test_a_datacenter_class_never_earns_speed

### Requirement: Each card tier is ranked by a trend computed for that tier

The README MUST carry `## 🔥 Trending for your card` ABOVE the most-loved list, one `### Up to <N> GB`
table per tier in `CARD_TIERS_GB` (low end first), each ranked by the model's 7-day buzz plus a speed
bonus earned only by the best measurement that **ran on a card ≤ N GB**. A model with no post in the
window is not in these tables. Only models with tier evidence appear.

#### Scenario: the tier-local bonus

- **Given** a model with buzz 10, a 500 t/s RTX 5090 run and a 50 t/s RTX 3060 12 GB run
- **When** the 8 GB and 32 GB tiers are ranked
- **Then** the 8 GB row has no speed term (no measurement at ≤ 8 GB) and the 32 GB row earns `log2(1 + 500/10)`
- **Test:** tests/test_trending_for_your_card.py::test_the_tier_bonus_never_comes_from_a_bigger_card

#### Scenario: evidence only

- **Given** a model whose only card measurement is a weights-only fit, and one with a proved run
- **When** the tier rows are computed
- **Then** the weights-only model earns no speed term and is rendered as `weights-only`, never as a measured fit
- **Test:** tests/test_trending_for_your_card.py::test_the_tier_bonus_never_comes_from_a_bigger_card

### Requirement: The most-loved VRAM cell names the card the headline came from

The most-loved `VRAM` cell MUST keep the least VRAM the model needs (with its evidence) AND name the
hardware the headline in-scope figure ran on.

#### Scenario: a 5090 headline on a model that fits 16 GB

- **Given** a model stating 16 GB whose best in-scope figure ran on an RTX 5090 32 GB
- **When** the most-loved row is rendered
- **Then** the cell starts with `**16GB**` and names `RTX 5090 32GB`
- **Test:** tests/test_trending_for_your_card.py::test_the_vram_cell_names_the_measured_card

### Requirement: The validator catches a tier table that is not its own ranking

`validate.check_card_trending` MUST run in the `readme` stage (a stage a make target selects) and
MUST fail when the section is missing, when a tier heading is missing or out of order, when a tier's
rows differ from `tier_trending_rows()`, when the shown tier trend is not the tier-local one, or when
an empty tier is not a named collection gap.

#### Scenario: a falsified README

- **Given** a rendered README with one tier row removed and one trend score edited
- **When** the check runs
- **Then** it fails naming the tier, and an untouched README passes
- **Test:** tests/test_trending_for_your_card.py::test_the_validator_catches_a_falsified_tier

### Requirement: The shipped store and README satisfy the section

The real `data/models.json` and the real `README.md` MUST satisfy the gate — no fixture-only claim.

#### Scenario: the shipped tree

- **Given** the repository's own store and README
- **When** the check and the tier derivation run
- **Then** every tier listed in the README is exactly what `tier_trending_rows()` produces, and no
  datacenter figure is the best cell of any row
- **Test:** tests/test_trending_for_your_card.py::test_the_shipped_readme_and_store

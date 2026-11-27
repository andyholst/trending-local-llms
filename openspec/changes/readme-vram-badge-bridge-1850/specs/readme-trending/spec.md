# readme-trending

## ADDED Requirements

### Requirement: the trending intro bridges the VRAM badge and the tier-qualifying cell

The "🔥 Trending for your card — low end first" intro in `README.md` MUST state that the `VRAM` badge is the model's least-needed VRAM and the card behind its headline figure, while the tier and speed bonus come from the card in the "Best t/s that fits" cell; it MUST say that a larger headline card in the badge does not mean the row is misplaced, and MUST link to [🖥️ Pick your card](#-pick-your-card--what-fits-your-vram) for the tier rule. Because this intro is generated, the SAME sentence MUST live in the `trending_card_section()` string in `scripts/update_trending.py` so `make render-readme` preserves it.

#### Scenario: a reader sees a badge larger than the table band

- **Given** the "Up to 8 GB" table shows Qwen3.8-27B with a 12GB badge / "headline on NVIDIA DGX Spark (GB10)"
- **When** the reader reaches that row after the section intro
- **Then** the intro explains the badge is the model's least-needed VRAM and headline card, while the 8 GB tier was earned by the smaller card in "Best t/s that fits", and points to "🖥️ Pick your card" for the tier rule
- **Test:** tests/test_card_fit.py::test_a_bigger_card_does_not_qualify_a_small_tier

#### Scenario: the next render keeps the bridge

- **Given** the sentence is present in both the README intro and the generator's intro string
- **When** `make render-readme` runs again on the shipped tree
- **Then** the README stays byte-identical with the sentence intact and no table row, number or badge changes
- **Test:** tests/test_readme_render.py::test_validator_accepts_generated_readme

# data-gap-analysis

## ADDED Requirements

### Requirement: A capacity mention is not an unstructured value

A dimension's free-text scan MUST require the text to name the DIMENSION, not merely a number
with a unit: a card's VRAM, a Mac's unified memory or a context size MUST NOT be reported as
`unstructured:weight_gb`.

#### Scenario: the three shapes the store holds

- **Given** a model whose hardware is `"RX 9070 XT 16GB"`, one whose hardware is
  `"M3 Ultra 256GB"`, and one whose quant is `"Q4_K_M, 19GB weights"`
- **When** the store is analysed
- **Then** only the third is `unstructured:weight_gb`, while all three are missing the structured value
- **Test:** tests/test_data_gap_analysis.py::test_a_capacity_mention_is_not_an_unstructured_weights_figure

### Requirement: A capacity dimension does not scan the hardware field

`weight_gb` MUST NOT scan `hardware` (`skip_fields`), because that field names the card.

#### Scenario: a card inside hardware

- **Given** a measurement whose hardware names a 16 GB card and whose quant names no footprint
- **When** the store is analysed
- **Then** the model is not reported as prose-only for `weight_gb`
- **Test:** tests/test_data_gap_analysis.py::test_a_capacity_mention_is_not_an_unstructured_weights_figure

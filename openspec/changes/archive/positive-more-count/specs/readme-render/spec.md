# Spec delta: readme-render (positive-more-count)

## ADDED Requirements

### Requirement: The "more measured" label is never negative
The per-VRAM render SHALL compute the number of OTHER ran-on measurements beside the shown
row by measurement identity (engine, tps, date, source_post), using ONE implementation for
both the card tables and the above-48-GB tables. A shown row that is not among the tier's
ran-on candidates SHALL NOT cause a subtraction; the count SHALL be zero or positive.

#### Scenario: a shown row is not classified ran-on by the tier seam
- **Given** a candidate list with no ran-on rows and a row shown with `ran on ≤32 GB`
- **When** the label is computed
- **Then** it reads `+0` (no label), never `+-1 more measured at this size`
- **Test:** tests/test_tier_more_count.py

#### Scenario: other ran-on rows are counted by identity
- **Given** a shown row and two ran-on candidates in freshly rebuilt dicts with the same measurement identity
- **When** the label is computed
- **Then** exactly two other measurements are reported
- **Test:** tests/test_tier_more_count.py
